import os
import tempfile
import subprocess
from dataclasses import dataclass

from app.services.transcription import Utterance


@dataclass
class AudioExtractionResult:
    student_audio_bytes: bytes
    student_speaking_duration: float


def extract_student_audio(
    audio_bytes: bytes,
    audio_ext: str,
    utterances: list[Utterance],
    student_speaker: int,
) -> AudioExtractionResult:
    """Extract student-only audio segments using FFmpeg and concatenate them."""
    student_segments = [u for u in utterances if u.speaker == student_speaker]

    if not student_segments:
        raise ValueError("No student speech segments found in transcript")

    student_duration = sum(u.end - u.start for u in student_segments)

    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input{audio_ext}")
        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        # Build FFmpeg filter_complex to trim and concatenate segments
        segment_files: list[str] = []
        for i, seg in enumerate(student_segments):
            seg_path = os.path.join(tmpdir, f"seg_{i:04d}.wav")
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-ss", str(seg.start),
                "-to", str(seg.end),
                "-ac", "1",
                "-ar", "16000",
                "-acodec", "pcm_s16le",
                seg_path,
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            segment_files.append(seg_path)

        # Write concat list
        concat_list_path = os.path.join(tmpdir, "concat.txt")
        with open(concat_list_path, "w") as f:
            for seg_path in segment_files:
                f.write(f"file '{seg_path}'\n")

        output_path = os.path.join(tmpdir, "student_only.wav")
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-ac", "1",
            "-ar", "16000",
            "-acodec", "pcm_s16le",
            output_path,
        ]
        subprocess.run(concat_cmd, check=True, capture_output=True)

        with open(output_path, "rb") as f:
            student_audio_bytes = f.read()

    return AudioExtractionResult(
        student_audio_bytes=student_audio_bytes,
        student_speaking_duration=student_duration,
    )


def get_audio_duration(audio_bytes: bytes, audio_ext: str) -> float:
    """Use ffprobe to get audio duration in seconds."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, f"input{audio_ext}")
        with open(input_path, "wb") as f:
            f.write(audio_bytes)

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            input_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        import json
        data = json.loads(result.stdout)
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "audio":
                return float(stream.get("duration", 0))
    return 0.0
