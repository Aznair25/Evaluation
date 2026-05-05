import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json

from app.services.azure_speech import (
    _score_to_cefr_band,
    FLUENCY_THRESHOLDS,
    PRONUNCIATION_THRESHOLDS,
    build_fluency_result,
    build_pronunciation_result,
    AzureSpeechResult,
)
from app.services.llm_evaluator import CRITERIA_PROMPTS, CEFR_LEVEL_DESCRIPTORS


def test_score_to_cefr_band_high():
    band = _score_to_cefr_band(92.0, FLUENCY_THRESHOLDS)
    assert band == "C2"


def test_score_to_cefr_band_mid():
    band = _score_to_cefr_band(60.0, FLUENCY_THRESHOLDS)
    assert band == "B1"


def test_score_to_cefr_band_low():
    band = _score_to_cefr_band(20.0, FLUENCY_THRESHOLDS)
    assert band == "A1"


def test_build_fluency_result_achieved():
    azure = AzureSpeechResult(
        pronunciation_score=80.0,
        accuracy_score=82.0,
        completeness_score=85.0,
        fluency_score=60.0,
        prosody_score=58.0,
        fluency_cefr_band="B1",
        pronunciation_cefr_band="B2",
    )
    result = build_fluency_result(azure, "A2")
    assert result["achieved"] is True
    assert "fluency_score" in result["azure_scores"]


def test_build_fluency_result_not_achieved():
    azure = AzureSpeechResult(
        pronunciation_score=30.0,
        accuracy_score=32.0,
        completeness_score=35.0,
        fluency_score=30.0,
        prosody_score=28.0,
        fluency_cefr_band="A1",
        pronunciation_cefr_band="A1",
    )
    result = build_fluency_result(azure, "B1")
    assert result["achieved"] is False


def test_build_pronunciation_result_achieved():
    azure = AzureSpeechResult(
        pronunciation_score=80.0,
        accuracy_score=82.0,
        completeness_score=85.0,
        fluency_score=60.0,
        prosody_score=58.0,
        fluency_cefr_band="B1",
        pronunciation_cefr_band="B2",
    )
    result = build_pronunciation_result(azure, "B1")
    assert result["achieved"] is True
    assert "pronunciation_score" in result["azure_scores"]


def test_all_criteria_keys_in_prompts():
    expected = {"interaction", "clarity", "strategies", "vocabulary"}
    assert set(CRITERIA_PROMPTS.keys()) == expected


def test_all_cefr_bands_in_descriptors():
    expected = {"A1", "A2", "B1", "B2", "C1", "C2"}
    assert set(CEFR_LEVEL_DESCRIPTORS.keys()) == expected
