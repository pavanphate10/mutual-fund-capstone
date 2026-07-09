"""Simple weekday scheduler for automatic NAV fetch and ETL runs."""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def should_run() -> bool:
    now = datetime.now()
    return now.weekday() < 5 and now.hour == 20 and now.minute == 0


def main() -> int:
    while True:
        if should_run():
            subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "live_nav_fetch.py")], check=False)
            subprocess.run([sys.executable, str(PROJECT_ROOT / "scripts" / "etl_pipeline.py")], check=False)
            time.sleep(60)
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
