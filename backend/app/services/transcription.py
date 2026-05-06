import json
import logging
from dataclasses import dataclass
from typing import Any

from deepgram import DeepgramClient, PrerecordedOptions
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class Utterance:
    speaker: int
    start: float
    end: float
    text: str
    confidence: float


@dataclass
class TranscriptResult:
    utterances: list[Utterance]
    full_text: str
    student_speaker: int
    audio_duration: float


def _identify_student_speaker(utterances: list[Utterance]) -> int:
    """Heuristic: the student speaks more total seconds than the interviewer."""
    speaker_durations: dict[int, float] = {}
    for u in utterances:
        duration = u.end - u.start
        speaker_durations[u.speaker] = speaker_durations.get(u.speaker, 0) + duration

    if not speaker_durations:
        return 0

    return max(speaker_durations, key=lambda s: speaker_durations[s])


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def transcribe_audio(audio_bytes: bytes, language: str = "fr") -> TranscriptResult:
    logger.info(f"Deepgram transcription: audio_size={len(audio_bytes)} bytes | language={language} | model=nova-3")
    client = DeepgramClient(settings.deepgram_api_key)

    options = PrerecordedOptions(
        model="nova-3",
        language=language,
        diarize=True,
        utterances=True,
        punctuate=True,
        smart_format=True,
    )

    response = await client.listen.asyncprerecorded.v("1").transcribe_file(
        {"buffer": audio_bytes, "mimetype": "audio/wav"},
        options,
    )
    logger.info("Deepgram response received")

    result_dict: dict[str, Any] = response.to_dict()
    channels = result_dict.get("results", {}).get("channels", [])
    utterances_raw = result_dict.get("results", {}).get("utterances", [])
    metadata = result_dict.get("metadata", {})

    audio_duration = metadata.get("duration", 0.0)
    logger.info(f"Deepgram metadata: duration={audio_duration:.2f}s | raw_utterances={len(utterances_raw)}")

    utterances: list[Utterance] = []
    for u in utterances_raw:
        utterances.append(
            Utterance(
                speaker=u.get("speaker", 0),
                start=u.get("start", 0.0),
                end=u.get("end", 0.0),
                text=u.get("transcript", ""),
                confidence=u.get("confidence", 0.0),
            )
        )

    # Fallback: reconstruct from channel alternatives if no utterances
    if not utterances and channels:
        logger.warning("No utterances returned by Deepgram; falling back to word-level channel reconstruction")
        words = channels[0].get("alternatives", [{}])[0].get("words", [])
        current_speaker = None
        current_start = 0.0
        current_end = 0.0
        current_words: list[str] = []

        for word in words:
            spk = word.get("speaker", 0)
            if spk != current_speaker:
                if current_words and current_speaker is not None:
                    utterances.append(
                        Utterance(
                            speaker=current_speaker,
                            start=current_start,
                            end=current_end,
                            text=" ".join(current_words),
                            confidence=1.0,
                        )
                    )
                current_speaker = spk
                current_start = word.get("start", 0.0)
                current_words = []

            current_end = word.get("end", current_end)
            current_words.append(word.get("word", ""))

        if current_words and current_speaker is not None:
            utterances.append(
                Utterance(
                    speaker=current_speaker,
                    start=current_start,
                    end=current_end,
                    text=" ".join(current_words),
                    confidence=1.0,
                )
            )

    student_speaker = _identify_student_speaker(utterances)
    student_turns = [u for u in utterances if u.speaker == student_speaker]
    full_text = " ".join(u.text for u in student_turns)

    logger.info(
        f"Transcription parsed: total_utterances={len(utterances)} | student_speaker={student_speaker} | "
        f"student_turns={len(student_turns)} | full_text_chars={len(full_text)}"
    )
    # Log unique speakers found
    speakers = sorted({u.speaker for u in utterances})
    logger.debug(f"Speakers detected: {speakers}")

    return TranscriptResult(
        utterances=utterances,
        full_text=full_text,
        student_speaker=student_speaker,
        audio_duration=audio_duration,
    )


def transcript_to_dict(result: TranscriptResult) -> dict[str, Any]:
    return {
        "full_text": result.full_text,
        "student_speaker": result.student_speaker,
        "audio_duration": result.audio_duration,
        "utterances": [
            {
                "speaker": u.speaker,
                "start": u.start,
                "end": u.end,
                "text": u.text,
                "confidence": u.confidence,
            }
            for u in result.utterances
        ],
    }
