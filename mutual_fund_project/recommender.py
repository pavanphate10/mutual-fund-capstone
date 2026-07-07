"""Mutual fund recommender ranked by Sharpe ratio within a risk appetite bucket."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
SCHEME_PERFORMANCE_PATH = PROJECT_ROOT / "data" / "processed" / "scheme_performance.csv"

RISK_APPETITE_MAP = {
    "Low": ["Low"],
    "Moderate": ["Moderate", "Moderately High"],
    "High": ["High", "Very High"],
}


def recommend_funds(risk_appetite: str) -> pd.DataFrame:
    """Return the top 3 funds for a given risk appetite."""
    normalized = risk_appetite.strip().title()
    if normalized not in RISK_APPETITE_MAP:
        valid = ", ".join(RISK_APPETITE_MAP)
        raise ValueError(f"Unsupported risk appetite '{risk_appetite}'. Choose one of: {valid}.")

    scheme_performance = pd.read_csv(SCHEME_PERFORMANCE_PATH)
    recommendations = (
        scheme_performance.loc[
            scheme_performance["risk_grade"].isin(RISK_APPETITE_MAP[normalized])
        ]
        .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
        .head(3)
        .copy()
    )
    return recommendations[
        ["scheme_name", "risk_grade", "sharpe_ratio", "return_3yr_pct", "aum_crore"]
    ].reset_index(drop=True)
