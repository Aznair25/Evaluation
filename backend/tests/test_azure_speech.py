"""
Unit tests for app.services.azure_speech.

The Azure SDK and FFmpeg segment-extraction helper are mocked entirely so
tests run without any real Azure credentials or audio files.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.azure_speech import (
    _score_to_cefr_band,
    FLUENCY_THRESHOLDS,
    PRONUNCIATION_THRESHOLDS,
    build_fluency_result,
    build_pronunciation_result,
    AzureSpeechResult,
)


# ── Fake utterance ─────────────────────────────────────────────────────────────

class _FakeUtterance:
    def __init__(self, text: str, start: float, end: float):
        self.text  = text
        self.start = start
        self.end   = end


def _make_utterances(*text_start_end: tuple) -> list:
    """Convenience: _make_utterances(("Bonjour.", 0.0, 2.0), ...)"""
    return [_FakeUtterance(t, s, e) for t, s, e in text_start_end]


# ── Mock SDK factory ───────────────────────────────────────────────────────────

# Minimal fake PCM used wherever _extract_pcm_segment is patched out
_FAKE_PCM = b"\x00\x01" * 1600


def _build_mock_sdk(
    utterance_scores: list | None = None,
    cancel_as_error: bool = False,
) -> MagicMock:
    """
    Return a fake ``azure.cognitiveservices.speech`` module for the
    per-utterance ``recognize_once_async`` approach.

    utterance_scores:
        List of dicts with keys pron/acc/comp/flu/pros.
        Each entry returns RecognizedSpeech for the i-th utterance call.
        Utterances beyond the list length return NoMatch.
    cancel_as_error:
        If True the first utterance returns Canceled with Error reason.
    """
    sdk = MagicMock(name="speechsdk")

    # enums (plain sentinels so equality comparisons work)
    sdk.ResultReason.RecognizedSpeech  = object()
    sdk.ResultReason.NoMatch           = object()
    sdk.ResultReason.Canceled          = object()
    sdk.CancellationReason.Error       = object()
    sdk.CancellationReason.EndOfStream = object()
    sdk.PronunciationAssessmentGradingSystem.HundredMark = object()
    sdk.PronunciationAssessmentGranularity.Phoneme       = object()

    sdk.SpeechConfig.return_value                  = MagicMock()
    sdk.PronunciationAssessmentConfig.return_value = MagicMock()
    sdk.audio.AudioStreamFormat.return_value       = MagicMock()
    sdk.audio.PushAudioInputStream.return_value    = MagicMock(name="push_stream")
    sdk.audio.AudioConfig.return_value             = MagicMock()

    scores_list = utterance_scores or []
    call_idx    = [0]

    def _make_future(idx: int) -> MagicMock:
        future = MagicMock()
        if cancel_as_error and idx == 0:
            result        = MagicMock()
            result.reason = sdk.ResultReason.Canceled
            details       = MagicMock()
            details.reason        = sdk.CancellationReason.Error
            details.error_code    = "ServiceError"
            details.error_details = "Simulated service error"
            result.cancellation_details = details
            future.get.return_value = result
        elif idx < len(scores_list):
            result        = MagicMock()
            result.reason = sdk.ResultReason.RecognizedSpeech
            result.json   = None
            future.get.return_value = result
        else:
            result        = MagicMock()
            result.reason = sdk.ResultReason.NoMatch
            future.get.return_value = result
        return future

    def _recognize_once_async() -> MagicMock:
        idx          = call_idx[0]
        call_idx[0] += 1
        return _make_future(idx)

    recognizer_mock = MagicMock()
    recognizer_mock.recognize_once_async.side_effect = _recognize_once_async
    sdk.SpeechRecognizer.return_value = recognizer_mock

    # PronunciationAssessmentResult returns scores in the order they are called
    pron_idx = [0]

    def _pron_result(_result) -> MagicMock:
        idx         = pron_idx[0]
        pron_idx[0] += 1
        pr = MagicMock()
        if idx < len(scores_list):
            s = scores_list[idx]
            pr.pronunciation_score = s["pron"]
            pr.accuracy_score      = s["acc"]
            pr.completeness_score  = s["comp"]
            pr.fluency_score       = s["flu"]
            pr.prosody_score       = s.get("pros", 0.0)
        return pr

    sdk.PronunciationAssessmentResult.side_effect = _pron_result
    return sdk


# ── helpers to run the function under test ─────────────────────────────────────

def _run_assessment(
    sdk_mock: MagicMock,
    utterances: list | None = None,
) -> AzureSpeechResult:
    """
    Call ``_run_azure_assessment`` with mocked speechsdk and
    ``_extract_pcm_segment`` (returns fake PCM without invoking FFmpeg).
    """
    from app.services import azure_speech as _mod

    if utterances is None:
        utterances = _make_utterances(("Bonjour je m'appelle Thomas.", 0.0, 3.0))

    with patch.object(_mod, "speechsdk", sdk_mock), \
         patch.object(_mod, "_extract_pcm_segment", return_value=_FAKE_PCM):
        return _mod._run_azure_assessment(b"fake_audio", ".wav", utterances)


# ── Tests: score-to-CEFR band mapping ─────────────────────────────────────────

class TestScoreToCefrBand:
    @pytest.mark.parametrize("score,expected", [
        (91.0, "C2"),
        (80.0, "C1"),
        (70.0, "B2"),
        (55.0, "B1"),
        (40.0, "A2"),
        (0.0,  "A1"),
        (39.9, "A1"),
    ])
    def test_fluency_bands(self, score, expected):
        assert _score_to_cefr_band(score, FLUENCY_THRESHOLDS) == expected

    @pytest.mark.parametrize("score,expected", [
        (88.0, "C2"),
        (68.0, "B2"),
        (55.0, "B1"),
        (0.0,  "A1"),
    ])
    def test_pronunciation_bands(self, score, expected):
        assert _score_to_cefr_band(score, PRONUNCIATION_THRESHOLDS) == expected


# ── Tests: _run_azure_assessment ──────────────────────────────────────────────

class TestRunAzureAssessment:

    # ------------------------------------------------------------------
    # Critical regression: enable_miscue must be False
    # ------------------------------------------------------------------
    def test_enable_miscue_is_false(self):
        """PronunciationAssessmentConfig must be created with enable_miscue=False."""
        sdk = _build_mock_sdk(
            utterance_scores=[{"pron": 80, "acc": 75, "comp": 90, "flu": 70, "pros": 65}]
        )
        _run_assessment(sdk)

        call_kwargs = sdk.PronunciationAssessmentConfig.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        args   = call_kwargs.args   if call_kwargs.args   else ()

        miscue_val = kwargs.get("enable_miscue", args[3] if len(args) > 3 else None)
        assert miscue_val is False, (
            f"enable_miscue={miscue_val!r} — must be False; "
            "True without matching reference text causes Azure to return zero scores"
        )

    def test_reference_text_is_forwarded_to_config(self):
        """Each utterance's text is passed as reference_text to PronunciationAssessmentConfig."""
        sdk = _build_mock_sdk(utterance_scores=[])
        expected_text = "Bonjour, je m'appelle Thomas, je vais très bien."
        utterances = _make_utterances((expected_text, 0.0, 3.0))
        _run_assessment(sdk, utterances=utterances)

        call_kwargs = sdk.PronunciationAssessmentConfig.call_args
        kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        args   = call_kwargs.args   if call_kwargs.args   else ()

        ref_val = kwargs.get("reference_text", args[0] if args else None)
        assert ref_val == expected_text, (
            f"reference_text={ref_val!r} — expected the utterance text to be forwarded"
        )

    def test_uses_push_audio_stream_not_file(self):
        """AudioConfig must be called with stream=, and write/close must be called."""
        sdk = _build_mock_sdk(utterance_scores=[])
        _run_assessment(sdk)

        sdk.audio.PushAudioInputStream.assert_called()
        push_stream = sdk.audio.PushAudioInputStream.return_value
        push_stream.write.assert_called()
        push_stream.close.assert_called()
        audio_config_call = sdk.audio.AudioConfig.call_args
        assert "stream" in (audio_config_call.kwargs or {}), (
            "AudioConfig must be called with stream=push_stream, not filename="
        )

    # ------------------------------------------------------------------
    # Score aggregation
    # ------------------------------------------------------------------
    def test_single_segment_scores_used_directly(self):
        seg = {"pron": 78.0, "acc": 82.0, "comp": 91.0, "flu": 65.0, "pros": 72.0}
        sdk = _build_mock_sdk(utterance_scores=[seg])
        result = _run_assessment(sdk)

        assert abs(result.pronunciation_score - 78.0) < 0.01
        assert abs(result.accuracy_score      - 82.0) < 0.01
        assert abs(result.completeness_score  - 91.0) < 0.01
        assert abs(result.fluency_score       - 65.0) < 0.01
        assert abs(result.prosody_score       - 72.0) < 0.01

    def test_multiple_segments_averaged(self):
        scores = [
            {"pron": 80.0, "acc": 70.0, "comp": 90.0, "flu": 60.0, "pros": 65.0},
            {"pron": 60.0, "acc": 90.0, "comp": 70.0, "flu": 80.0, "pros": 75.0},
        ]
        utterances = _make_utterances(
            ("Premier segment.", 0.0, 3.0),
            ("Deuxième segment.", 5.0, 8.0),
        )
        sdk = _build_mock_sdk(utterance_scores=scores)
        result = _run_assessment(sdk, utterances=utterances)

        assert abs(result.pronunciation_score - 70.0) < 0.01
        assert abs(result.accuracy_score      - 80.0) < 0.01
        assert abs(result.completeness_score  - 80.0) < 0.01
        assert abs(result.fluency_score       - 70.0) < 0.01
        assert abs(result.prosody_score       - 70.0) < 0.01

    # ------------------------------------------------------------------
    # Zero-segment path
    # ------------------------------------------------------------------
    def test_no_segments_returns_zero_scores(self):
        sdk = _build_mock_sdk(utterance_scores=[])   # all utterances → NoMatch
        result = _run_assessment(sdk)

        assert result.pronunciation_score == 0.0
        assert result.accuracy_score      == 0.0
        assert result.completeness_score  == 0.0
        assert result.fluency_score       == 0.0
        assert result.prosody_score       == 0.0

    def test_no_segments_cefr_band_is_a1(self):
        sdk = _build_mock_sdk(utterance_scores=[])
        result = _run_assessment(sdk)
        assert result.fluency_cefr_band       == "A1"
        assert result.pronunciation_cefr_band == "A1"

    # ------------------------------------------------------------------
    # Short / empty utterances are skipped
    # ------------------------------------------------------------------
    def test_short_utterance_skipped(self):
        """Utterances shorter than 0.5 s must be skipped (no API call made)."""
        sdk = _build_mock_sdk(utterance_scores=[])
        short_utt = _make_utterances(("Hi.", 0.0, 0.2))   # 200 ms — below MIN_DURATION
        _run_assessment(sdk, utterances=short_utt)

        sdk.SpeechRecognizer.assert_not_called()

    def test_empty_text_utterance_skipped(self):
        """Utterances with blank text must be skipped."""
        sdk = _build_mock_sdk(utterance_scores=[])
        blank_utt = _make_utterances(("   ", 0.0, 5.0))
        _run_assessment(sdk, utterances=blank_utt)

        sdk.SpeechRecognizer.assert_not_called()

    # ------------------------------------------------------------------
    # Error / cancellation path
    # ------------------------------------------------------------------
    def test_error_cancellation_raises_runtime_error(self):
        sdk = _build_mock_sdk(utterance_scores=[], cancel_as_error=True)
        with pytest.raises(RuntimeError, match="Azure Speech canceled with error"):
            _run_assessment(sdk)

    # ------------------------------------------------------------------
    # CEFR band derivation from scores
    # ------------------------------------------------------------------
    def test_b2_fluency_band(self):
        scores = [{"pron": 72.0, "acc": 80.0, "comp": 90.0, "flu": 75.0, "pros": 70.0}]
        sdk = _build_mock_sdk(utterance_scores=scores)
        result = _run_assessment(sdk)
        assert result.fluency_cefr_band       == "B2"
        assert result.pronunciation_cefr_band == "B2"


# ── Tests: build_fluency_result / build_pronunciation_result ──────────────────

class TestBuildResults:
    def _make_result(self, flu=75.0, pron=75.0) -> AzureSpeechResult:
        return AzureSpeechResult(
            pronunciation_score=pron,
            accuracy_score=80.0,
            completeness_score=85.0,
            fluency_score=flu,
            prosody_score=70.0,
            fluency_cefr_band=_score_to_cefr_band(flu, FLUENCY_THRESHOLDS),
            pronunciation_cefr_band=_score_to_cefr_band(pron, PRONUNCIATION_THRESHOLDS),
        )

    def test_fluency_achieved_at_target_band(self):
        result = self._make_result(flu=75.0)   # B2 (≥70)
        outcome = build_fluency_result(result, target_level="B2")
        assert outcome["achieved"] is True

    def test_fluency_not_achieved_below_target(self):
        result = self._make_result(flu=60.0)   # B1
        outcome = build_fluency_result(result, target_level="B2")
        assert outcome["achieved"] is False

    def test_pronunciation_achieved_at_target_band(self):
        result = self._make_result(pron=70.0)  # B2 (≥68)
        outcome = build_pronunciation_result(result, target_level="B2")
        assert outcome["achieved"] is True

    def test_pronunciation_not_achieved_below_target(self):
        result = self._make_result(pron=50.0)  # B1
        outcome = build_pronunciation_result(result, target_level="B2")
        assert outcome["achieved"] is False
