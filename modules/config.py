"""Configuration and project path definitions."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class AssemblyConfig:
    elevenlabs_api_key: str
    elevenlabs_voice_id: str
    video_width: int = 1920
    video_height: int = 1080
    fps: int = 60
    voiceover_volume: float = 1.0
    bg_music_volume: float = 0.18
    zoom_intensity: float = 0.15
    fade_duration: float = 0.3
    blur_background: bool = True
    blur_radius: int = 51
    blur_dim: float = 0.7
    foreground_scale: float = 0.95
    caption_font: str = "Arial-Bold"
    caption_font_size: int = 48
    caption_color: str = "white"
    caption_stroke_color: str = "black"
    caption_stroke_width: int = 3
    extra_panel_flash_duration: float = 0.25
    inter_sentence_pause_ms: int = 0
    voice_chunk_cache_dir: str = "output/voice_chunks"
    extra_fields: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_json(cls, path: Path) -> "AssemblyConfig":
        if not path.exists():
            print(f"ERROR: Config file not found at {path}")
            print("Copy config.example.json to config.json and fill in your API keys.")
            sys.exit(1)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        known_keys = {f.name for f in cls.__dataclass_fields__.values() if f.name != "extra_fields"}
        kwargs = {k: v for k, v in data.items() if k in known_keys and not k.startswith("_")}
        extra = {k: v for k, v in data.items() if k not in known_keys and not k.startswith("_")}
        return cls(**kwargs, extra_fields=extra)

    def as_dict(self) -> Dict[str, Any]:
        """Flat dict for components that still expect a config mapping."""
        result = asdict(self)
        result.pop("extra_fields", None)
        result.update(self.extra_fields)
        return result


@dataclass
class ProjectPaths:
    input_dir: Path
    output_dir: Path
    images_dir: Path
    script_file: Path
    timeline_file: Path
    music_file: Path
    voiceover_file: Path
    final_video: Path
    sync_plan_file: Path
    sync_sheet_file: Path
    chunk_dir: Path
    log_file: Path

    @classmethod
    def from_config(
        cls,
        config: AssemblyConfig,
        root: Optional[Path] = None,
    ) -> "ProjectPaths":
        root = root or Path(".")
        input_dir = root / "input"
        output_dir = root / "output"
        return cls(
            input_dir=input_dir,
            output_dir=output_dir,
            images_dir=input_dir / "images",
            script_file=input_dir / "script.txt",
            timeline_file=input_dir / "timeline.json",
            music_file=input_dir / "music.mp3",
            voiceover_file=output_dir / "voiceover.mp3",
            final_video=output_dir / "final_video.mp4",
            sync_plan_file=output_dir / "sync_plan.json",
            sync_sheet_file=output_dir / "sync_sheet_audio.csv",
            chunk_dir=Path(config.voice_chunk_cache_dir),
            log_file=root / "assembly.log",
        )

    def ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
