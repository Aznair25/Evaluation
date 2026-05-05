import os
import tempfile
import json
import asyncio
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()

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


def _run_azure_assessment(audio_bytes: bytes) -> AzureSpeechResult:
    """Run Azure Speech Pronunciation Assessment synchronously."""
    import azure.cognitiveservices.speech as speechsdk

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        speech_config = speechsdk.SpeechConfig(
            subscription=settings.azure_speech_key,
            region=settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = "fr-FR"

        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        pronunciation_config.enable_prosody_assessment()

        audio_config = speechsdk.AudioConfig(filename=tmp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        pronunciation_config.apply_to(recognizer)

        result = recognizer.recognize_once_async().get()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            assessment_result = speechsdk.PronunciationAssessmentResult(result)
            pron_score = assessment_result.pronunciation_score or 0.0
            accuracy_score = assessment_result.accuracy_score or 0.0
            completeness_score = assessment_result.completeness_score or 0.0
            fluency_score = assessment_result.fluency_score or 0.0
            prosody_score = getattr(assessment_result, "prosody_score", 0.0) or 0.0
        else:
            pron_score = accuracy_score = completeness_score = fluency_score = prosody_score = 0.0

    finally:
        os.unlink(tmp_path)

    return AzureSpeechResult(
        pronunciation_score=pron_score,
        accuracy_score=accuracy_score,
        completeness_score=completeness_score,
        fluency_score=fluency_score,
        prosody_score=prosody_score,
        fluency_cefr_band=_score_to_cefr_band(fluency_score, FLUENCY_THRESHOLDS),
        pronunciation_cefr_band=_score_to_cefr_band(pron_score, PRONUNCIATION_THRESHOLDS),
    )


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def assess_pronunciation_and_fluency(student_audio_bytes: bytes) -> AzureSpeechResult:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_azure_assessment, student_audio_bytes)


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
