import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.evaluation import Evaluation, EvaluationStatus
from app.services.transcription import transcribe_audio, transcript_to_dict, TranscriptResult
from app.services.audio_extraction import extract_student_audio, get_audio_duration
from app.services.llm_evaluator import evaluate_criterion, detect_cefr_band
from app.services.azure_speech import assess_pronunciation_and_fluency, build_fluency_result, build_pronunciation_result
from app.services.level_decider import decide_level
from app.services.pdf_generator import generate_pdf
from app.services.storage import StorageService
from app.services.eval_logger import get_eval_logger, cleanup_eval_logger
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def _update_evaluation(
    db: AsyncSession,
    evaluation_id: str,
    **kwargs,
):
    result = await db.execute(
        select(Evaluation).where(Evaluation.id == evaluation_id)
    )
    evaluation = result.scalar_one_or_none()
    if evaluation:
        for key, value in kwargs.items():
            setattr(evaluation, key, value)
        evaluation.updated_at = datetime.now(timezone.utc)
        await db.commit()


async def run_evaluation_pipeline(
    evaluation_id: str,
    audio_bytes: bytes,
    audio_ext: str,
    language: str = "fr",
):
    log = get_eval_logger(evaluation_id)
    log.info("=" * 70)
    log.info(f"Pipeline started | evaluation_id={evaluation_id} | language={language} | audio_ext={audio_ext} | audio_size={len(audio_bytes)} bytes")
    log.info("=" * 70)

    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline(db, evaluation_id, audio_bytes, audio_ext, language, log)
        except Exception as exc:
            log.error(f"Pipeline FAILED: {type(exc).__name__}: {exc}", exc_info=True)
            logger.error(f"Pipeline failed for {evaluation_id}: {exc}", exc_info=True)
            try:
                await _update_evaluation(
                    db,
                    evaluation_id,
                    status=EvaluationStatus.FAILED,
                    error_message=str(exc),
                    progress_percentage=0,
                    current_step="Processing failed",
                )
            except Exception:
                pass
        finally:
            log.info("=" * 70)
            log.info("Pipeline finished")
            log.info("=" * 70)
            cleanup_eval_logger(evaluation_id)


async def _run_pipeline(
    db: AsyncSession,
    evaluation_id: str,
    audio_bytes: bytes,
    audio_ext: str,
    language: str,
    log: logging.Logger,
):
    storage = StorageService()

    # --- Stage 1: Transcription ---
    log.info("--- STAGE 1: Transcription ---")
    log.info(f"Calling Deepgram transcription | language={language} | audio_size={len(audio_bytes)} bytes")
    await _update_evaluation(
        db, evaluation_id,
        status=EvaluationStatus.TRANSCRIBING,
        progress_percentage=10,
        current_step="Transcribing audio with speaker diarization...",
    )

    transcript_result: TranscriptResult = await transcribe_audio(audio_bytes, language)
    log.info(f"Transcription complete | utterances={len(transcript_result.utterances)} | student_speaker={transcript_result.student_speaker} | audio_duration={transcript_result.audio_duration:.2f}s")
    log.debug(f"Full transcript text (first 500 chars): {transcript_result.full_text[:500]!r}")

    # Get total audio duration
    log.info("Getting audio duration via ffprobe")
    audio_duration = await asyncio.get_event_loop().run_in_executor(
        None, get_audio_duration, audio_bytes, audio_ext
    )
    if not audio_duration:
        log.warning("ffprobe returned no duration; falling back to Deepgram duration")
        audio_duration = transcript_result.audio_duration
    log.info(f"Audio duration: {audio_duration:.2f}s")

    # Save transcript to S3
    transcript_dict = transcript_to_dict(transcript_result)
    transcript_bytes = json.dumps(transcript_dict).encode("utf-8")
    transcript_s3_key = f"transcripts/{evaluation_id}/transcript.json"
    log.info(f"Uploading transcript to S3: {transcript_s3_key}")
    await asyncio.get_event_loop().run_in_executor(
        None, storage.upload_bytes, transcript_bytes, transcript_s3_key, "application/json"
    )
    log.info("Transcript uploaded successfully")

    await _update_evaluation(
        db, evaluation_id,
        transcript_s3_key=transcript_s3_key,
        audio_duration_seconds=audio_duration,
        progress_percentage=20,
        current_step="Transcription complete. Extracting student audio...",
    )

    # --- Stage 2: Student Audio Extraction ---
    log.info("--- STAGE 2: Student Audio Extraction ---")
    student_segments = [u for u in transcript_result.utterances if u.speaker == transcript_result.student_speaker]
    log.info(f"Identified {len(student_segments)} student speech segments for speaker {transcript_result.student_speaker}")
    for i, seg in enumerate(student_segments):
        log.debug(f"  Segment {i+1}: [{seg.start:.2f}s - {seg.end:.2f}s] confidence={seg.confidence:.2f} text={seg.text[:80]!r}")

    extraction_result = await asyncio.get_event_loop().run_in_executor(
        None,
        extract_student_audio,
        audio_bytes,
        audio_ext,
        transcript_result.utterances,
        transcript_result.student_speaker,
    )
    log.info(f"Student audio extracted | speaking_duration={extraction_result.student_speaking_duration:.2f}s | audio_size={len(extraction_result.student_audio_bytes)} bytes")

    student_audio_s3_key = f"audio/{evaluation_id}/student_only.wav"
    log.info(f"Uploading student audio to S3: {student_audio_s3_key}")
    await asyncio.get_event_loop().run_in_executor(
        None,
        storage.upload_bytes,
        extraction_result.student_audio_bytes,
        student_audio_s3_key,
        "audio/wav",
    )
    log.info("Student audio uploaded successfully")

    await _update_evaluation(
        db, evaluation_id,
        student_speaking_duration_seconds=extraction_result.student_speaking_duration,
        progress_percentage=30,
        current_step="Student audio extracted. Starting criterion evaluation...",
        status=EvaluationStatus.ANALYZING,
    )

    # --- Stage 3: Level Detection + Parallel Criterion Evaluation ---
    log.info("--- STAGE 3: CEFR Band Detection + Parallel Criterion Evaluation ---")
    student_transcript_text = transcript_result.full_text
    log.info(f"Student transcript length: {len(student_transcript_text)} chars")

    log.info("Calling GPT-4o for initial CEFR band detection")
    cefr_band = await detect_cefr_band(student_transcript_text)
    log.info(f"Detected CEFR band: {cefr_band}")

    await _update_evaluation(
        db, evaluation_id,
        progress_percentage=40,
        current_step=f"Detected CEFR band: {cefr_band}. Evaluating 6 criteria in parallel...",
    )

    log.info("Launching 4 LLM criterion tasks + Azure Speech assessment in parallel")
    llm_tasks = {
        "interaction": evaluate_criterion("interaction", student_transcript_text, cefr_band),
        "clarity": evaluate_criterion("clarity", student_transcript_text, cefr_band),
        "strategies": evaluate_criterion("strategies", student_transcript_text, cefr_band),
        "vocabulary": evaluate_criterion("vocabulary", student_transcript_text, cefr_band),
    }
    log.info(f"LLM criteria to evaluate: {list(llm_tasks.keys())}")

    # Per-utterance pronunciation assessment: each student segment is extracted
    # individually from the original audio and assessed against its own short
    # reference text. This avoids Azure's limitations with long audio / large
    # reference texts in a single continuous-recognition session.
    log.info(
        f"Azure Speech: submitting {len(student_segments)} student utterance(s) for "
        f"per-utterance assessment | region={settings.azure_speech_region}"
    )

    azure_task = assess_pronunciation_and_fluency(
        audio_bytes,
        audio_ext,
        student_segments,
    )

    llm_keys = list(llm_tasks.keys())
    llm_coroutines = list(llm_tasks.values())

    results = await asyncio.gather(*llm_coroutines, azure_task, return_exceptions=True)

    llm_results_raw = results[:4]
    azure_result_raw = results[4]

    criteria_results: dict = {}

    # Process LLM results
    for i, key in enumerate(llm_keys):
        if isinstance(llm_results_raw[i], Exception):
            log.error(f"Criterion '{key}' FAILED: {type(llm_results_raw[i]).__name__}: {llm_results_raw[i]}", exc_info=llm_results_raw[i])
            logger.error(f"Criterion {key} failed: {llm_results_raw[i]}")
            criteria_results[key] = {
                "achieved": None,
                "evidence": [],
                "comment_fr": "Erreur lors de l'évaluation de ce critère.",
                "comment_en": "Error evaluating this criterion.",
                "error": str(llm_results_raw[i]),
            }
        else:
            result_val = llm_results_raw[i]
            log.info(f"Criterion '{key}': achieved={result_val.get('achieved')} | highest_level={result_val.get('highest_level_demonstrated', 'N/A')}")
            log.debug(f"  Evidence: {result_val.get('evidence', [])}")
            log.debug(f"  Comment (EN): {result_val.get('comment_en', '')[:200]}")
            criteria_results[key] = result_val

    # Process Azure Speech result
    if isinstance(azure_result_raw, Exception):
        log.error(f"Azure Speech assessment FAILED: {type(azure_result_raw).__name__}: {azure_result_raw}", exc_info=azure_result_raw)
        log.error("Fluency and pronunciation will be marked as errors in the report")
        logger.error(f"Azure Speech failed: {azure_result_raw}")
        criteria_results["fluency"] = {
            "achieved": None,
            "evidence": [],
            "comment_fr": "Erreur lors de l'analyse de la fluidité.",
            "comment_en": "Error analyzing fluency.",
            "error": str(azure_result_raw),
        }
        criteria_results["pronunciation"] = {
            "achieved": None,
            "evidence": [],
            "comment_fr": "Erreur lors de l'analyse de la prononciation.",
            "comment_en": "Error analyzing pronunciation.",
            "error": str(azure_result_raw),
        }
    else:
        log.info(
            f"Azure Speech result: pronunciation={azure_result_raw.pronunciation_score:.1f} | "
            f"accuracy={azure_result_raw.accuracy_score:.1f} | "
            f"completeness={azure_result_raw.completeness_score:.1f} | "
            f"fluency={azure_result_raw.fluency_score:.1f} | "
            f"prosody={azure_result_raw.prosody_score:.1f}"
        )
        log.info(f"  -> fluency_cefr_band={azure_result_raw.fluency_cefr_band} | pronunciation_cefr_band={azure_result_raw.pronunciation_cefr_band}")
        fluency_result = build_fluency_result(azure_result_raw, cefr_band)
        pronunciation_result = build_pronunciation_result(azure_result_raw, cefr_band)
        log.info(f"  Fluency criterion: achieved={fluency_result.get('achieved')}")
        log.info(f"  Pronunciation criterion: achieved={pronunciation_result.get('achieved')}")
        log.debug(f"  Fluency evidence: {fluency_result.get('evidence', [])}")
        log.debug(f"  Pronunciation evidence: {pronunciation_result.get('evidence', [])}")
        criteria_results["fluency"] = fluency_result
        criteria_results["pronunciation"] = pronunciation_result

    criteria_summary = {k: v.get("achieved") for k, v in criteria_results.items()}
    log.info(f"All criteria summary: {criteria_summary}")

    await _update_evaluation(
        db, evaluation_id,
        criteria_results=criteria_results,
        progress_percentage=75,
        current_step="Criteria evaluated. Determining final CEFR level...",
    )

    # --- Stage 4: Level Decision ---
    log.info("--- STAGE 4: Level Decision ---")
    decision = decide_level(cefr_band, criteria_results)
    log.info(f"Level decision: cefr_level={decision.cefr_level} | sub_level={decision.sub_level}")
    log.info(f"  communicative_profile_fr={decision.communicative_profile_fr!r}")
    log.info(f"  communicative_profile_en={decision.communicative_profile_en!r}")

    log.info("Generating bilingual global comment via GPT-4o")
    global_comments = await _generate_global_comments(
        student_transcript_text, decision.cefr_level, criteria_results, log
    )
    log.info(f"Global comment (FR, first 150 chars): {global_comments.get('fr', '')[:150]!r}")
    log.info(f"Global comment (EN, first 150 chars): {global_comments.get('en', '')[:150]!r}")

    await _update_evaluation(
        db, evaluation_id,
        cefr_level=decision.cefr_level,
        sub_level_rule=decision.sub_level,
        communicative_profile_fr=decision.communicative_profile_fr,
        communicative_profile_en=decision.communicative_profile_en,
        global_comment_fr=global_comments.get("fr"),
        global_comment_en=global_comments.get("en"),
        criteria_results=criteria_results,
        progress_percentage=85,
        current_step="Generating bilingual PDF report...",
        status=EvaluationStatus.GENERATING_REPORT,
    )

    # --- Stage 5: PDF Generation ---
    log.info("--- STAGE 5: PDF Generation ---")
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()

    log.info(f"Generating PDF | student={getattr(evaluation, 'student_name', None)!r} | evaluator={getattr(evaluation, 'evaluator_name', None)!r}")
    pdf_bytes = await asyncio.get_event_loop().run_in_executor(
        None,
        generate_pdf,
        evaluation_id,
        decision,
        criteria_results,
        global_comments.get("fr", ""),
        global_comments.get("en", ""),
        evaluation.student_name if evaluation else None,
        evaluation.evaluator_name if evaluation else None,
        evaluation.institution if evaluation else None,
        evaluation.evaluation_date if evaluation else None,
    )
    log.info(f"PDF generated: {len(pdf_bytes)} bytes")

    report_s3_key = f"reports/{evaluation_id}/evaluation_report.pdf"
    log.info(f"Uploading PDF to S3: {report_s3_key}")
    await asyncio.get_event_loop().run_in_executor(
        None, storage.upload_bytes, pdf_bytes, report_s3_key, "application/pdf"
    )
    log.info("PDF uploaded successfully")

    # Delete source audio if retention is 0
    if settings.audio_retention_days == 0 and evaluation and evaluation.audio_s3_key:
        log.info(f"audio_retention_days=0 — deleting source audio: {evaluation.audio_s3_key}")
        await asyncio.get_event_loop().run_in_executor(
            None, storage.delete_object, evaluation.audio_s3_key
        )

    await _update_evaluation(
        db, evaluation_id,
        report_s3_key=report_s3_key,
        status=EvaluationStatus.COMPLETED,
        progress_percentage=100,
        current_step="Evaluation complete.",
    )
    log.info(f"Pipeline completed successfully | cefr_level={decision.cefr_level}")


async def _generate_global_comments(
    student_transcript: str,
    cefr_level: str,
    criteria_results: dict,
    log: logging.Logger,
) -> dict:
    """Generate global bilingual comment using GPT-4o."""
    from openai import AsyncOpenAI
    from app.config import get_settings

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    strengths = [
        k for k, v in criteria_results.items()
        if isinstance(v, dict) and v.get("achieved") is True
    ]
    weaknesses = [
        k for k, v in criteria_results.items()
        if isinstance(v, dict) and v.get("achieved") is False
    ]
    log.info(f"Global comment: strengths={strengths} | weaknesses={weaknesses}")

    prompt = f"""You are a CEFR French language evaluator writing a global comment for a student's oral evaluation.

Student CEFR level determined: {cefr_level}
Criteria achieved: {', '.join(strengths) if strengths else 'none'}
Criteria not yet achieved: {', '.join(weaknesses) if weaknesses else 'none'}

Write a constructive global comment covering:
1. Strengths (forces)
2. Areas for improvement (pistes d'amélioration)
3. Next steps (prochaines étapes)

Respond ONLY in valid JSON:
{{
  "fr": "Commentaire global en français (3-5 phrases)...",
  "en": "Global comment in English (3-5 sentences)..."
}}"""

    try:
        log.info("Calling GPT-4o for global comment generation")
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        log.info("Global comment generated successfully")
        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        log.error(f"Global comment generation FAILED: {type(exc).__name__}: {exc}", exc_info=exc)
        logger.error(f"Global comment generation failed ({type(exc).__name__}): {exc}", exc_info=True)
        return {
            "fr": f"L'étudiant a atteint le niveau {cefr_level}.",
            "en": f"The student has reached level {cefr_level}.",
        }
