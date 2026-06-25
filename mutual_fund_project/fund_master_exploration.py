"""Explore the fund master dataset for Day 1 analytics insights."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_FILE = REPORTS_DIR / "day1_fund_master_exploration.log"
FUND_MASTER_FILE = RAW_DATA_DIR / "fund_master.csv"


def configure_logging() -> logging.Logger:
    """Configure logging for fund master exploration."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("fund_master_exploration")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


LOGGER = configure_logging()


def find_column(columns: Iterable[str], keywords: Iterable[str]) -> Optional[str]:
    """Find the first column whose normalized name matches any keyword."""
    normalized = {column.lower().strip(): column for column in columns}
    for keyword in keywords:
        keyword = keyword.lower().strip()
        if keyword in normalized:
            return normalized[keyword]

    for column in columns:
        compact = column.lower().replace(" ", "").replace("_", "")
        for keyword in keywords:
            if keyword.lower().replace(" ", "").replace("_", "") in compact:
                return column
    return None


def print_unique_values(dataframe: pd.DataFrame, label: str, keywords: Iterable[str]) -> None:
    """Print sorted unique values for a logical dataset field."""
    column = find_column(dataframe.columns, keywords)
    if not column:
        print(f"{label}: column not found")
        LOGGER.warning("%s column not found in fund_master.csv", label)
        return

    values = sorted(dataframe[column].dropna().astype(str).unique())
    print(f"\n{label} ({len(values)} unique):")
    for value in values:
        print(f"- {value}")

    LOGGER.info("Identified %s unique values for %s", len(values), label)


def print_scheme_code_structure(dataframe: pd.DataFrame) -> None:
    """Describe the AMFI/scheme code field structure."""
    code_column = find_column(
        dataframe.columns,
        ["amfi_code", "amfi code", "scheme_code", "scheme code", "code"],
    )
    if not code_column:
        print("\nAMFI Code Structure: scheme code column not found")
        LOGGER.warning("Scheme code column not found in fund_master.csv")
        return

    codes = (
        dataframe[code_column]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
    )
    code_lengths = codes.str.len().value_counts().sort_index()

    print("\nAMFI Code Structure:")
    print(f"- Column used: {code_column}")
    print(f"- Unique scheme codes: {codes.nunique()}")
    print("- Length distribution:")
    print(code_lengths.to_string())

    if not codes.empty and codes.str.fullmatch(r"\d+").all():
        print("- Observation: scheme codes are numeric identifiers, commonly 6 digits.")
    else:
        print("- Observation: some scheme codes are non-numeric or irregularly formatted.")


def generate_summary_statistics(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Generate summary statistics for numeric and categorical columns."""
    return dataframe.describe(include="all", datetime_is_numeric=True).transpose()


def print_insights(dataframe: pd.DataFrame) -> None:
    """Print lightweight exploratory insights from the fund master dataset."""
    row_count, column_count = dataframe.shape
    print("\nInsights:")
    print(f"- Dataset contains {row_count} rows and {column_count} columns.")
    print(f"- Total missing values: {int(dataframe.isna().sum().sum())}")
    print(f"- Duplicate rows: {int(dataframe.duplicated().sum())}")

    fund_house_column = find_column(dataframe.columns, ["fund_house", "fund house", "amc"])
    if fund_house_column:
        top_fund_houses = dataframe[fund_house_column].value_counts(dropna=True).head(5)
        print("- Top fund houses by record count:")
        print(top_fund_houses.to_string())


def main() -> None:
    """Run exploratory analysis on the fund master dataset."""
    if not FUND_MASTER_FILE.exists():
        message = (
            f"fund_master.csv not found at {FUND_MASTER_FILE}. "
            "Fund house/category exploration and AMFI validation are blocked until the file is added."
        )
        LOGGER.error(message)
        print(message)
        return

    try:
        dataframe = pd.read_csv(FUND_MASTER_FILE)
        LOGGER.info("Loaded fund_master.csv with shape %s", dataframe.shape)

        print_unique_values(dataframe, "Fund Houses", ["fund_house", "fund house", "amc"])
        print_unique_values(
            dataframe,
            "Categories",
            ["category", "scheme_category", "scheme category"],
        )
        print_unique_values(
            dataframe,
            "Sub-Categories",
            ["sub_category", "subcategory", "sub category"],
        )
        print_unique_values(
            dataframe,
            "Risk Grades",
            ["risk_grade", "risk grade", "riskometer", "risk"],
        )
        print_scheme_code_structure(dataframe)

        summary = generate_summary_statistics(dataframe)
        print("\nSummary Statistics:")
        print(summary)

        print_insights(dataframe)
    except pd.errors.EmptyDataError:
        LOGGER.error("fund_master.csv is empty.")
        print("fund_master.csv is empty.")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Error while exploring fund_master.csv: %s", exc)
        print(f"Error while exploring fund_master.csv: {exc}")


if __name__ == "__main__":
    main()
