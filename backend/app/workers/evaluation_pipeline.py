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
    async with AsyncSessionLocal() as db:
        try:
            await _run_pipeline(db, evaluation_id, audio_bytes, audio_ext, language)
        except Exception as exc:
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


async def _run_pipeline(
    db: AsyncSession,
    evaluation_id: str,
    audio_bytes: bytes,
    audio_ext: str,
    language: str,
):
    storage = StorageService()

    # --- Stage 1: Transcription ---
    await _update_evaluation(
        db, evaluation_id,
        status=EvaluationStatus.TRANSCRIBING,
        progress_percentage=10,
        current_step="Transcribing audio with speaker diarization...",
    )

    transcript_result: TranscriptResult = await transcribe_audio(audio_bytes, language)

    # Get total audio duration
    audio_duration = await asyncio.get_event_loop().run_in_executor(
        None, get_audio_duration, audio_bytes, audio_ext
    )
    if not audio_duration:
        audio_duration = transcript_result.audio_duration

    # Save transcript to S3
    transcript_dict = transcript_to_dict(transcript_result)
    transcript_bytes = json.dumps(transcript_dict).encode("utf-8")
    transcript_s3_key = f"transcripts/{evaluation_id}/transcript.json"
    await asyncio.get_event_loop().run_in_executor(
        None, storage.upload_bytes, transcript_bytes, transcript_s3_key, "application/json"
    )

    await _update_evaluation(
        db, evaluation_id,
        transcript_s3_key=transcript_s3_key,
        audio_duration_seconds=audio_duration,
        progress_percentage=20,
        current_step="Transcription complete. Extracting student audio...",
    )

    # --- Stage 2: Student Audio Extraction ---
    extraction_result = await asyncio.get_event_loop().run_in_executor(
        None,
        extract_student_audio,
        audio_bytes,
        audio_ext,
        transcript_result.utterances,
        transcript_result.student_speaker,
    )

    student_audio_s3_key = f"audio/{evaluation_id}/student_only.wav"
    await asyncio.get_event_loop().run_in_executor(
        None,
        storage.upload_bytes,
        extraction_result.student_audio_bytes,
        student_audio_s3_key,
        "audio/wav",
    )

    await _update_evaluation(
        db, evaluation_id,
        student_speaking_duration_seconds=extraction_result.student_speaking_duration,
        progress_percentage=30,
        current_step="Student audio extracted. Starting criterion evaluation...",
        status=EvaluationStatus.ANALYZING,
    )

    # --- Stage 3: Level Detection + Parallel Criterion Evaluation ---
    student_transcript_text = transcript_result.full_text

    # First detect the CEFR band
    cefr_band = await detect_cefr_band(student_transcript_text)

    await _update_evaluation(
        db, evaluation_id,
        progress_percentage=40,
        current_step=f"Detected CEFR band: {cefr_band}. Evaluating 6 criteria in parallel...",
    )

    # Run all 6 criteria in parallel
    llm_tasks = {
        "interaction": evaluate_criterion("interaction", student_transcript_text, cefr_band),
        "clarity": evaluate_criterion("clarity", student_transcript_text, cefr_band),
        "strategies": evaluate_criterion("strategies", student_transcript_text, cefr_band),
        "vocabulary": evaluate_criterion("vocabulary", student_transcript_text, cefr_band),
    }
    azure_task = assess_pronunciation_and_fluency(extraction_result.student_audio_bytes)

    # Gather LLM results with graceful error handling
    llm_keys = list(llm_tasks.keys())
    llm_coroutines = list(llm_tasks.values())

    results = await asyncio.gather(*llm_coroutines, azure_task, return_exceptions=True)

    llm_results_raw = results[:4]
    azure_result_raw = results[4]

    criteria_results: dict = {}
    for i, key in enumerate(llm_keys):
        if isinstance(llm_results_raw[i], Exception):
            logger.error(f"Criterion {key} failed: {llm_results_raw[i]}")
            criteria_results[key] = {
                "achieved": None,
                "evidence": [],
                "comment_fr": "Erreur lors de l'évaluation de ce critère.",
                "comment_en": "Error evaluating this criterion.",
                "error": str(llm_results_raw[i]),
            }
        else:
            criteria_results[key] = llm_results_raw[i]

    if isinstance(azure_result_raw, Exception):
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
        criteria_results["fluency"] = build_fluency_result(azure_result_raw, cefr_band)
        criteria_results["pronunciation"] = build_pronunciation_result(azure_result_raw, cefr_band)

    await _update_evaluation(
        db, evaluation_id,
        criteria_results=criteria_results,
        progress_percentage=75,
        current_step="Criteria evaluated. Determining final CEFR level...",
    )

    # --- Stage 4: Level Decision ---
    decision = decide_level(cefr_band, criteria_results)

    # Generate global comment via LLM
    global_comments = await _generate_global_comments(
        student_transcript_text, decision.cefr_level, criteria_results
    )

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
    # Reload evaluation for metadata
    result = await db.execute(select(Evaluation).where(Evaluation.id == evaluation_id))
    evaluation = result.scalar_one_or_none()

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

    report_s3_key = f"reports/{evaluation_id}/evaluation_report.pdf"
    await asyncio.get_event_loop().run_in_executor(
        None, storage.upload_bytes, pdf_bytes, report_s3_key, "application/pdf"
    )

    # Delete source audio if retention is 0
    if settings.audio_retention_days == 0 and evaluation and evaluation.audio_s3_key:
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


async def _generate_global_comments(
    student_transcript: str,
    cefr_level: str,
    criteria_results: dict,
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
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3,
        )
        return json.loads(response.choices[0].message.content)
    except Exception as exc:
        logger.error(f"Global comment generation failed: {exc}")
        return {
            "fr": f"L'étudiant a atteint le niveau {cefr_level}.",
            "en": f"The student has reached level {cefr_level}.",
        }
