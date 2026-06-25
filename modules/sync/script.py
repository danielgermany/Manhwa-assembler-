"""
Script Processing Module
========================
Reads script.txt and parses into segments.

Supports two formats:
  1. Delimiter-based: scenes separated by `---`
  2. Auto-split: splits on sentence boundaries
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass
class Sentence:
    """A single narrated sentence with scene context."""

    global_idx: int
    scene_id: int
    scene_sentence_idx: int
    text: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


def _split_into_sentences(text: str) -> List[str]:
    """Split text on sentence boundaries (. ! ?)."""
    raw = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = []
    buffer = ""
    for part in raw:
        if not part.strip():
            continue
        word_count = len(part.split())
        if word_count < 4 and buffer:
            buffer += " " + part.strip()
        else:
            if buffer:
                sentences.append(buffer.strip())
            buffer = part.strip()
    if buffer:
        sentences.append(buffer.strip())
    return sentences


def parse_script(script_path: Path, delimiter: str = "---") -> List[str]:
    """
    Parse script.txt into a list of segments.

    If the script contains `---` delimiters, segments are split on those.
    Otherwise, splits on sentence boundaries (. ! ?).

    Returns: list of text segments, each one a caption-able chunk.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError(f"Script file is empty: {script_path}")

    if delimiter in text:
        segments = [s.strip() for s in text.split(delimiter) if s.strip()]
        return segments

    return _split_into_sentences(text)


def parse_scenes_with_sentences(
    script_path: Path,
    delimiter: str = "---",
) -> List[List[Sentence]]:
    """
    Parse script into scenes, each containing an ordered list of sentences.

    Scenes are split on `---` when present; otherwise the whole script is
  one scene. Sentences within each scene are split on . ! ? boundaries.
    """
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise ValueError(f"Script file is empty: {script_path}")

    if delimiter in text:
        scene_texts = [s.strip() for s in text.split(delimiter) if s.strip()]
    else:
        scene_texts = [text]

    scenes: List[List[Sentence]] = []
    global_idx = 0
    for scene_id, scene_text in enumerate(scene_texts, start=1):
        scene_sentences = []
        for scene_sentence_idx, sentence_text in enumerate(
            _split_into_sentences(scene_text)
        ):
            scene_sentences.append(
                Sentence(
                    global_idx=global_idx,
                    scene_id=scene_id,
                    scene_sentence_idx=scene_sentence_idx,
                    text=sentence_text,
                )
            )
            global_idx += 1
        scenes.append(scene_sentences)

    return scenes


def flatten_sentences(scenes: List[List[Sentence]]) -> List[Sentence]:
    """Return all sentences in global narration order."""
    return [sentence for scene in scenes for sentence in scene]


def estimate_word_count(segments: List[str]) -> int:
    """Total word count across all segments. Used for duration estimation."""
    return sum(len(s.split()) for s in segments)


def estimate_duration_seconds(word_count: int, wpm: int = 155) -> float:
    """
    Estimate audio duration in seconds based on words per minute.
    Default 155 wpm matches typical narration speed.
    """
    return (word_count / wpm) * 60.0


def estimate_sentence_durations(
    sentences: List[Sentence],
    wpm: int = 155,
) -> List[float]:
    """Estimate per-sentence durations from word count (dry-run / planning)."""
    return [estimate_duration_seconds(s.word_count, wpm=wpm) for s in sentences]
