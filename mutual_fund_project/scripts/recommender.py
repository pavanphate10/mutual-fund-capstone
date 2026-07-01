"""Simple CLI fund recommender based on Sharpe ratio and mapped risk appetite."""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEME_PERFORMANCE_PATH = PROJECT_ROOT / "data" / "processed" / "scheme_performance.csv"

RISK_APPETITE_MAP = {
    "low": ["Low"],
    "moderate": ["Moderate", "Moderately High"],
    "high": ["High", "Very High"],
}


def normalize_appetite(raw_value: str) -> str:
    normalized = raw_value.strip().lower()
    if normalized not in RISK_APPETITE_MAP:
        valid = ", ".join(sorted(key.title() for key in RISK_APPETITE_MAP))
        raise ValueError(f"Unsupported risk appetite '{raw_value}'. Choose one of: {valid}.")
    return normalized


def recommend_funds(risk_appetite: str) -> pd.DataFrame:
    appetite_key = normalize_appetite(risk_appetite)
    schemes = pd.read_csv(SCHEME_PERFORMANCE_PATH)
    grades = RISK_APPETITE_MAP[appetite_key]

    recommendations = (
        schemes.loc[schemes["risk_grade"].isin(grades)]
        .sort_values(["sharpe_ratio", "aum_crore"], ascending=[False, False])
        .head(3)
        .copy()
    )
    recommendations.insert(0, "risk_appetite", appetite_key.title())
    return recommendations[
        [
            "risk_appetite",
            "amfi_code",
            "scheme_name",
            "fund_house",
            "risk_grade",
            "sharpe_ratio",
            "return_3yr_pct",
            "aum_crore",
            "expense_ratio_pct",
        ]
    ]


def main(argv: list[str]) -> int:
    if len(argv) >= 2:
        appetite = argv[1]
    else:
        appetite = input("Enter risk appetite (Low / Moderate / High): ")

    try:
        recommendations = recommend_funds(appetite)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    print("\nTop 3 fund recommendations by Sharpe ratio\n")
    print(recommendations.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
