"""
Voice Generation Module
========================
Calls ElevenLabs API to convert script text into MP3 voiceover.
Supports monolithic generation and per-sentence chunk mode for audio-synced pacing.
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Sequence

import imageio_ffmpeg
import requests
from mutagen.mp3 import MP3

from modules.sync.script import Sentence

logger = logging.getLogger("audio.voice")

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


def _ffmpeg_path() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def _run_ffmpeg(args: List[str]) -> None:
    command = [_ffmpeg_path(), *args]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({result.returncode}): {result.stderr.strip() or result.stdout}"
        )


def _validate_api_key(api_key: str) -> None:
    if not api_key or api_key == "your-key-here":
        raise ValueError(
            "ElevenLabs API key not configured. "
            "Set it in config.json. Get a key at https://elevenlabs.io/app/settings/api-keys"
        )


def _call_elevenlabs(
    text: str,
    output_path: Path,
    voice_id: str,
    api_key: str,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
    model_id: str = "eleven_multilingual_v2",
) -> Path:
    """Call ElevenLabs TTS API and write MP3 to output_path."""
    _validate_api_key(api_key)

    url = ELEVENLABS_API_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }

    response = requests.post(url, json=payload, headers=headers, timeout=300)
    if response.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs API error {response.status_code}: {response.text}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(response.content)

    return output_path


def _apply_speed(audio_path: Path, speed: float) -> None:
    """Apply playback speed adjustment in-place via ffmpeg atempo."""
    if speed == 1.0:
        return

    temp_path = audio_path.with_suffix(".tmp.mp3")
    _run_ffmpeg(
        [
            "-y",
            "-i",
            str(audio_path),
            "-filter:a",
            f"atempo={speed}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(temp_path),
        ]
    )
    temp_path.replace(audio_path)


def _write_silence_mp3(path: Path, duration_ms: int) -> None:
    if duration_ms <= 0:
        return
    duration_s = duration_ms / 1000.0
    _run_ffmpeg(
        [
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=mono",
            "-t",
            f"{duration_s:.3f}",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "192k",
            str(path),
        ]
    )


def generate_voiceover(
    text: str,
    output_path: Path,
    voice_id: str,
    api_key: str,
    speed: float = 1.0,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
    model_id: str = "eleven_multilingual_v2",
) -> Path:
    """Generate voiceover from a single text block using ElevenLabs API."""
    logger.info(f"  Sending {len(text)} chars to ElevenLabs (voice: {voice_id})")
    _call_elevenlabs(
        text=text,
        output_path=output_path,
        voice_id=voice_id,
        api_key=api_key,
        stability=stability,
        similarity_boost=similarity_boost,
        style=style,
        model_id=model_id,
    )
    _apply_speed(output_path, speed)
    return output_path


def generate_voiceover_chunks(
    sentences: Sequence[Sentence],
    chunk_dir: Path,
    voice_id: str,
    api_key: str,
    speed: float = 1.0,
    skip_existing: bool = False,
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.3,
    model_id: str = "eleven_multilingual_v2",
) -> List[float]:
    """
    Generate one MP3 per sentence. Returns real duration (seconds) per sentence.

    Chunks are cached as {chunk_dir}/{global_idx:03d}.mp3.
    """
    chunk_dir.mkdir(parents=True, exist_ok=True)
    durations: List[float] = []

    for i, sentence in enumerate(sentences):
        chunk_path = chunk_dir / f"{sentence.global_idx:03d}.mp3"
        if skip_existing and chunk_path.exists():
            duration = get_audio_duration(chunk_path)
            logger.info(
                f"  Chunk {i + 1}/{len(sentences)} cached "
                f"({duration:.2f}s): {sentence.text[:50]}..."
            )
        else:
            logger.info(
                f"  Chunk {i + 1}/{len(sentences)}: {sentence.text[:60]}..."
            )
            _call_elevenlabs(
                text=sentence.text,
                output_path=chunk_path,
                voice_id=voice_id,
                api_key=api_key,
                stability=stability,
                similarity_boost=similarity_boost,
                style=style,
                model_id=model_id,
            )
            _apply_speed(chunk_path, speed)
            duration = get_audio_duration(chunk_path)

        durations.append(duration)

    return durations


def concatenate_voiceover_chunks(
    sentences: Sequence[Sentence],
    chunk_dir: Path,
    output_path: Path,
    silence_after_ms: Sequence[int],
    inter_sentence_pause_ms: int = 0,
) -> Path:
    """
    Concatenate per-sentence chunks into a single voiceover MP3.

    silence_after_ms[i] is appended after sentence i (for flash-panel padding).
    """
    if len(silence_after_ms) != len(sentences):
        raise ValueError("silence_after_ms must match sentence count")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="voice_concat_") as tmp:
        tmp_dir = Path(tmp)
        concat_list = tmp_dir / "concat.txt"
        entries: List[str] = []

        for idx, (sentence, silence_ms) in enumerate(zip(sentences, silence_after_ms)):
            chunk_path = chunk_dir / f"{sentence.global_idx:03d}.mp3"
            if not chunk_path.exists():
                raise FileNotFoundError(f"Missing voice chunk: {chunk_path}")

            entries.append(f"file '{chunk_path.resolve()}'")

            if silence_ms > 0:
                silence_path = tmp_dir / f"silence_{sentence.global_idx:03d}.mp3"
                _write_silence_mp3(silence_path, silence_ms)
                entries.append(f"file '{silence_path.resolve()}'")

            if inter_sentence_pause_ms > 0 and idx < len(sentences) - 1:
                pause_path = tmp_dir / f"pause_{sentence.global_idx:03d}.mp3"
                _write_silence_mp3(pause_path, inter_sentence_pause_ms)
                entries.append(f"file '{pause_path.resolve()}'")

        if not entries:
            raise ValueError("No sentences to concatenate")

        concat_list.write_text("\n".join(entries) + "\n", encoding="utf-8")
        _run_ffmpeg(
            [
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                str(output_path),
            ]
        )

    duration = get_audio_duration(output_path)
    logger.info(f"  Concatenated voiceover: {output_path} ({duration:.1f}s)")
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Return duration of an MP3 file in seconds."""
    return float(MP3(audio_path).info.length)
