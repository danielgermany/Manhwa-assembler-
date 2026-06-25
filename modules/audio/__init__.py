"""ElevenLabs voice generation."""

from modules.audio.voice import (
    concatenate_voiceover_chunks,
    generate_voiceover,
    generate_voiceover_chunks,
    get_audio_duration,
)

__all__ = [
    "generate_voiceover",
    "generate_voiceover_chunks",
    "concatenate_voiceover_chunks",
    "get_audio_duration",
]
