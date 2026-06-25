"""Timeline loading and legacy panel ordering."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

logger = logging.getLogger("sync.timeline")


@dataclass
class TimelinePanel:
    file: str
    segment: int


def load_timeline_panels(timeline_path: Path) -> List[TimelinePanel]:
    """Load panel order and scene segment from timeline.json."""
    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    return [
        TimelinePanel(file=entry["file"], segment=int(entry["segment"]))
        for entry in timeline["panels"]
    ]


def load_timeline_legacy(
    timeline_path: Path,
    image_paths: Sequence[Path],
) -> Tuple[List[Path], Optional[List[float]]]:
    """
    Load legacy script-synced timeline (word-count estimated durations).

    Returns (ordered_image_paths, durations) or (image_paths, None) if missing.
    """
    if not timeline_path.exists():
        logger.info("      No timeline.json found - using even image spread")
        return list(image_paths), None

    with open(timeline_path, "r", encoding="utf-8") as f:
        timeline = json.load(f)

    by_name = {p.name: p for p in image_paths}
    ordered: List[Path] = []
    durations: List[float] = []
    missing: List[str] = []

    for entry in timeline["panels"]:
        name = entry["file"]
        if name in by_name:
            ordered.append(by_name[name])
            durations.append(float(entry["dur"]))
        else:
            missing.append(name)

    leftover = [
        p for p in image_paths
        if p.name not in {e["file"] for e in timeline["panels"]}
    ]
    if leftover:
        avg = sum(durations) / len(durations) if durations else 2.0
        for p in leftover:
            ordered.append(p)
            durations.append(avg)

    if missing:
        logger.warning(f"      {len(missing)} timeline panels missing from disk (skipped)")
    logger.info(
        f"      Timeline loaded: {len(ordered)} panels, legacy pacing "
        f"({min(durations):.2f}s-{max(durations):.2f}s per panel)"
    )
    return ordered, durations
