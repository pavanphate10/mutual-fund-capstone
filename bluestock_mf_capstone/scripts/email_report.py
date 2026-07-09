"""Generate a simple HTML email-style weekly report for the project."""

from __future__ import annotations

from pathlib import Path
from html import escape

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_PATH = REPORTS_DIR / "weekly_report.html"


def build_html() -> str:
    items = [
        ("ETL pipeline", "scripts/etl_pipeline.py"),
        ("Performance analytics", "scripts/compute_metrics.py"),
        ("Advanced analytics", "scripts/advanced_analytics.py"),
    ]
    rows = "\n".join(
        f"<tr><td>{escape(name)}</td><td>{escape(path)}</td></tr>" for name, path in items
    )
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head><meta charset=\"utf-8\"><title>Weekly Mutual Fund Report</title></head>
<body>
<h1>Weekly Mutual Fund Report</h1>
<p>This weekly digest summarizes the project workflow and key deliverables.</p>
<table>
  <tr><th>Component</th><th>Entry point</th></tr>
  {rows}
</table>
</body>
</html>
"""


def main() -> None:
    OUTPUT_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
