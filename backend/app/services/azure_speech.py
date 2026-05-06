import asyncio
import logging
import os
import subprocess
import tempfile
import wave
from dataclasses import dataclass

import azure.cognitiveservices.speech as speechsdk
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.config import get_settings
from app.services.transcription import Utterance

settings = get_settings()
logger = logging.getLogger(__name__)

# CEFR thresholds for Azure Speech scores
# Based on MÉTRO-LANG calibration
FLUENCY_THRESHOLDS = {
    "C2": 90,
    "C1": 80,
    "B2": 70,
    "B1": 55,
    "A2": 40,
    "A1": 0,
}

PRONUNCIATION_THRESHOLDS = {
    "C2": 88,
    "C1": 78,
    "B2": 68,
    "B1": 55,
    "A2": 40,
    "A1": 0,
}


def _score_to_cefr_band(score: float, thresholds: dict) -> str:
    for band, threshold in thresholds.items():
        if score >= threshold:
            return band
    return "A1"


@dataclass
class AzureSpeechResult:
    pronunciation_score: float
    accuracy_score: float
    completeness_score: float
    fluency_score: float
    prosody_score: float
    fluency_cefr_band: str
    pronunciation_cefr_band: str


def _extract_pcm_segment(
    audio_bytes: bytes,
    audio_ext: str,
    start: float,
    end: float,
) -> bytes:
    """Use FFmpeg to cut [start, end] seconds from audio and return raw 16 kHz/16-bit/mono PCM."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path  = os.path.join(tmpdir, f"input{audio_ext}")
        output_path = os.path.join(tmpdir, "seg.wav")
        with open(input_path, "wb") as f:
            f.write(audio_bytes)
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ss", str(start),
                "-to", str(end),
                "-ac", "1",
                "-ar", "16000",
                "-acodec", "pcm_s16le",
                output_path,
            ],
            check=True,
            capture_output=True,
        )
        with wave.open(output_path, "rb") as wf:
            return wf.readframes(wf.getnframes())


def _assess_utterance(
    speech_config: speechsdk.SpeechConfig,
    stream_format: speechsdk.audio.AudioStreamFormat,
    pcm_bytes: bytes,
    reference_text: str,
    idx: int,
) -> tuple[float, float, float, float, float] | None:
    """
    Run recognize_once_async for a single utterance.
    Returns (pron, acc, comp, flu, prosody) or None if not recognised.
    Raises RuntimeError on CancellationReason.Error.
    """
    push_stream  = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
    audio_config = speechsdk.audio.AudioConfig(stream=push_stream)

    pron_config = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=False,
    )
    pron_config.enable_prosody_assessment()

    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_config,
    )
    pron_config.apply_to(recognizer)

    push_stream.write(pcm_bytes)
    push_stream.close()

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        raw_json = getattr(result, "json", None)
        if raw_json:
            logger.debug(f"  Utterance {idx} raw JSON: {raw_json[:300]}")
        ar   = speechsdk.PronunciationAssessmentResult(result)
        pron = ar.pronunciation_score or 0.0
        acc  = ar.accuracy_score or 0.0
        comp = ar.completeness_score or 0.0
        flu  = ar.fluency_score or 0.0
        pros = getattr(ar, "prosody_score", 0.0) or 0.0
        logger.debug(
            f"  Utterance {idx}: pron={pron:.1f} acc={acc:.1f} "
            f"comp={comp:.1f} flu={flu:.1f} pros={pros:.1f}"
        )
        return (pron, acc, comp, flu, pros)
    elif result.reason == speechsdk.ResultReason.NoMatch:
        details = getattr(result, "no_match_details", "n/a")
        logger.warning(f"  Utterance {idx} NoMatch: {details}")
    elif result.reason == speechsdk.ResultReason.Canceled:
        details      = result.cancellation_details
        err_code     = getattr(details, "error_code",    "N/A")
        err_details  = getattr(details, "error_details", "N/A")
        if details.reason == speechsdk.CancellationReason.Error:
            logger.error(
                f"  Utterance {idx} Canceled (Error): reason={details.reason} "
                f"error_code={err_code} error_details={err_details!r}"
            )
            raise RuntimeError(
                f"Azure Speech canceled with error: "
                f"code={err_code} details={err_details!r}"
            )
        else:
            # EndOfStream or other non-error cancellation — treat as NoMatch
            logger.warning(
                f"  Utterance {idx} Canceled (non-error): reason={details.reason} "
                f"error_code={err_code} — treating as NoMatch"
            )
    else:
        logger.warning(f"  Utterance {idx}: unexpected result reason {result.reason}")
    return None


def _run_azure_assessment(
    audio_bytes: bytes,
    audio_ext: str,
    utterances: list[Utterance],
) -> AzureSpeechResult:
    """
    Per-utterance pronunciation assessment.

    For each student utterance the corresponding audio segment is extracted
    from the original recording with FFmpeg and assessed against that
    utterance's Deepgram transcript as reference text.  This sidesteps the
    issues that arise when submitting a single long audio file with a large
    reference text to Azure Pronunciation Assessment.
    """
    logger.debug(
        f"Azure Speech: configuring SDK | region={settings.azure_speech_region} | language=fr-FR"
    )
    speech_config = speechsdk.SpeechConfig(
        subscription=settings.azure_speech_key,
        region=settings.azure_speech_region,
    )
    speech_config.speech_recognition_language = "fr-FR"

    stream_format = speechsdk.audio.AudioStreamFormat(
        samples_per_second=16000,
        bits_per_sample=16,
        channels=1,
    )

    MIN_DURATION = 0.5  # skip utterances shorter than 500 ms
    valid = [u for u in utterances if u.text.strip() and (u.end - u.start) >= MIN_DURATION]
    logger.info(
        f"Azure Speech: {len(valid)}/{len(utterances)} utterances eligible "
        f"(skipped {len(utterances) - len(valid)} short/empty)"
    )

    segment_results: list[tuple[float, float, float, float, float]] = []

    for i, utt in enumerate(valid):
        ref_text = utt.text.strip()
        duration = utt.end - utt.start
        logger.info(
            f"  Utterance {i + 1}/{len(valid)}: [{utt.start:.2f}s-{utt.end:.2f}s] "
            f"duration={duration:.2f}s ref={ref_text[:80]!r}"
        )

        try:
            pcm_bytes = _extract_pcm_segment(audio_bytes, audio_ext, utt.start, utt.end)
        except Exception as exc:
            logger.warning(f"  Utterance {i + 1}: audio extraction failed: {exc}")
            continue

        if not pcm_bytes:
            logger.warning(f"  Utterance {i + 1}: extracted PCM is empty, skipping")
            continue

        scores = _assess_utterance(speech_config, stream_format, pcm_bytes, ref_text, i + 1)
        if scores is not None:
            segment_results.append(scores)

    if not segment_results:
        logger.warning("Azure Speech: no speech segments recognized — all scores will be 0")
        pron_score = accuracy_score = completeness_score = fluency_score = prosody_score = 0.0
    else:
        n = len(segment_results)
        logger.info(f"Azure Speech: aggregating scores over {n} recognized segment(s)")
        pron_score         = sum(r[0] for r in segment_results) / n
        accuracy_score     = sum(r[1] for r in segment_results) / n
        completeness_score = sum(r[2] for r in segment_results) / n
        fluency_score      = sum(r[3] for r in segment_results) / n
        prosody_score      = sum(r[4] for r in segment_results) / n
        logger.info(
            f"Azure Speech: aggregated: pron={pron_score:.1f} acc={accuracy_score:.1f} "
            f"comp={completeness_score:.1f} flu={fluency_score:.1f} prosody={prosody_score:.1f}"
        )

    azure_result = AzureSpeechResult(
        pronunciation_score=pron_score,
        accuracy_score=accuracy_score,
        completeness_score=completeness_score,
        fluency_score=fluency_score,
        prosody_score=prosody_score,
        fluency_cefr_band=_score_to_cefr_band(fluency_score, FLUENCY_THRESHOLDS),
        pronunciation_cefr_band=_score_to_cefr_band(pron_score, PRONUNCIATION_THRESHOLDS),
    )
    logger.info(
        f"Azure Speech: done | "
        f"fluency_cefr={azure_result.fluency_cefr_band} | "
        f"pronunciation_cefr={azure_result.pronunciation_cefr_band}"
    )
    return azure_result


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def assess_pronunciation_and_fluency(
    audio_bytes: bytes,
    audio_ext: str,
    utterances: list[Utterance],
) -> AzureSpeechResult:
    logger.info(
        f"assess_pronunciation_and_fluency: dispatching to thread executor | "
        f"audio_size={len(audio_bytes)} bytes | utterances={len(utterances)}"
    )
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, _run_azure_assessment, audio_bytes, audio_ext, utterances
    )


def build_fluency_result(azure_result: AzureSpeechResult, target_level: str) -> dict:
    target_band = target_level[:2]  # e.g. "B1" from "B1.2"
    band_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
    achieved = band_order.index(azure_result.fluency_cefr_band) >= band_order.index(target_band)

    return {
        "achieved": achieved,
        "evidence": [
            f"Fluency score: {azure_result.fluency_score:.1f}/100",
            f"Prosody score: {azure_result.prosody_score:.1f}/100",
        ],
        "comment_fr": f"Score de fluidité: {azure_result.fluency_score:.1f}/100. Score de prosodie: {azure_result.prosody_score:.1f}/100.",
        "comment_en": f"Fluency score: {azure_result.fluency_score:.1f}/100. Prosody score: {azure_result.prosody_score:.1f}/100.",
        "azure_scores": {
            "fluency_score": azure_result.fluency_score,
            "prosody_score": azure_result.prosody_score,
        },
    }


def build_pronunciation_result(azure_result: AzureSpeechResult, target_level: str) -> dict:
    target_band = target_level[:2]
    band_order = ["A1", "A2", "B1", "B2", "C1", "C2"]
    achieved = band_order.index(azure_result.pronunciation_cefr_band) >= band_order.index(target_band)

    return {
        "achieved": achieved,
        "evidence": [
            f"Pronunciation score: {azure_result.pronunciation_score:.1f}/100",
            f"Accuracy score: {azure_result.accuracy_score:.1f}/100",
            f"Completeness score: {azure_result.completeness_score:.1f}/100",
        ],
        "comment_fr": f"Score de prononciation: {azure_result.pronunciation_score:.1f}/100. Score de précision: {azure_result.accuracy_score:.1f}/100. Score de complétude: {azure_result.completeness_score:.1f}/100.",
        "comment_en": f"Pronunciation score: {azure_result.pronunciation_score:.1f}/100. Accuracy score: {azure_result.accuracy_score:.1f}/100. Completeness score: {azure_result.completeness_score:.1f}/100.",
        "azure_scores": {
            "pronunciation_score": azure_result.pronunciation_score,
            "accuracy_score": azure_result.accuracy_score,
            "completeness_score": azure_result.completeness_score,
        },
    }
