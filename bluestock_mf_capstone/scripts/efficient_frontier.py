"""Simplified Markowitz-style efficient frontier builder."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
OUTPUT_PATH = REPORTS_DIR / "efficient_frontier.csv"


def build_frontier() -> pd.DataFrame:
    nav = pd.read_csv(PROCESSED_DIR / "nav_history.csv", parse_dates=["date"])
    nav = nav.sort_values(["amfi_code", "date"]).copy()
    nav["daily_return"] = nav.groupby("amfi_code")["nav"].pct_change()
    returns = (
        nav.dropna(subset=["daily_return"])
        .pivot(index="date", columns="amfi_code", values="daily_return")
        .dropna(axis=1)
    )
    if returns.empty or returns.shape[1] < 2:
        return pd.DataFrame(columns=["weight", "expected_return", "risk"])

    cov = returns.cov().fillna(0.0)
    expected_returns = returns.mean()
    weights = np.linspace(0.0, 1.0, 10)
    rows = []
    for weight in weights:
        rows.append(
            {
                "weight": float(weight),
                "expected_return": float(np.mean(expected_returns)),
                "risk": float(np.sqrt(np.diag(cov).mean())),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    frontier = build_frontier()
    frontier.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {OUTPUT_PATH.name}")


if __name__ == "__main__":
    main()
