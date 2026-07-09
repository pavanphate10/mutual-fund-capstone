"""Monte Carlo projection for 5-year NAV scenarios."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_PATH = REPORTS_DIR / "monte_carlo_projection.csv"


def run_simulation() -> pd.DataFrame:
    nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
    latest_nav = nav.sort_values(["amfi_code", "date"]).groupby("amfi_code").tail(1)
    projected = []
    rng = np.random.default_rng(42)
    for _, row in latest_nav.head(5).iterrows():
        drift = np.log(row["nav"]) * 0.02
        vol = 0.02
        for _ in range(1000):
            path = np.exp(np.cumsum(rng.normal(drift, vol, size=60)))
            projected.append({"amfi_code": row["amfi_code"], "scenario": _, "projected_nav": path[-1]})
    return pd.DataFrame(projected)


def main() -> None:
    result = run_simulation()
    result.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
