"""Convenience ETL entry point that runs the ingestion and cleaning workflow."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def main() -> int:
    commands = [
        [sys.executable, str(SCRIPTS_DIR / "data_ingestion.py")],
        [sys.executable, str(SCRIPTS_DIR / "day2_pipeline.py")],
    ]
    for command in commands:
        completed = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
