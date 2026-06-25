"""
Automated Manhwa Video Assembly Script
=======================================
Thin CLI entry point. See modules/pipeline.py for orchestration logic.

Usage:
  python assembly_script.py
  python assembly_script.py --dry-run
  python assembly_script.py --preview
  python assembly_script.py --legacy-sync
"""

import argparse
from pathlib import Path

from modules.common.utils import setup_logging
from modules.config import AssemblyConfig, ProjectPaths
from modules.pipeline import AssemblyArgs, AssemblyPipeline


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assemble manhwa recap video from images + script"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without rendering",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Render only first 60 seconds for QA",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Voiceover speed multiplier (0.8 = slower, 1.2 = faster)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config file",
    )
    parser.add_argument(
        "--skip-voiceover",
        action="store_true",
        help="Reuse cached voice chunks / voiceover.mp3 (saves API credits)",
    )
    parser.add_argument(
        "--legacy-sync",
        action="store_true",
        help="Use legacy timeline.json word-count pacing instead of audio-sync",
    )
    ns = parser.parse_args()

    config = AssemblyConfig.from_json(Path(ns.config))
    paths = ProjectPaths.from_config(config)
    setup_logging(str(paths.log_file))

    args = AssemblyArgs(
        dry_run=ns.dry_run,
        preview=ns.preview,
        speed=ns.speed,
        skip_voiceover=ns.skip_voiceover,
        legacy_sync=ns.legacy_sync,
    )
    AssemblyPipeline(config, paths).run(args)


if __name__ == "__main__":
    main()
