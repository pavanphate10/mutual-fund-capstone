"""Validate AMFI/scheme codes between fund master and NAV history datasets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Optional, Set

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_FILE = REPORTS_DIR / "day1_amfi_validation.log"
SUMMARY_FILE = REPORTS_DIR / "day1_data_quality.md"
FUND_MASTER_FILE = RAW_DATA_DIR / "fund_master.csv"
NAV_HISTORY_CANDIDATES = [
    RAW_DATA_DIR / "02_nav_history.csv",
    RAW_DATA_DIR / "nav_history.csv",
]


def configure_logging() -> logging.Logger:
    """Configure logging for AMFI code validation."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("validate_amfi_codes")
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
    """Find the most likely column for a logical field."""
    normalized = {column.lower().strip(): column for column in columns}
    for keyword in keywords:
        if keyword.lower().strip() in normalized:
            return normalized[keyword.lower().strip()]

    for column in columns:
        compact = column.lower().replace(" ", "").replace("_", "")
        for keyword in keywords:
            if keyword.lower().replace(" ", "").replace("_", "") in compact:
                return column
    return None


def load_dataset(file_path: Path) -> pd.DataFrame:
    """Load a CSV dataset or raise a clear error."""
    if not file_path.exists():
        raise FileNotFoundError(f"Required file not found: {file_path}")
    return pd.read_csv(file_path)


def resolve_nav_history_file() -> Path:
    """Pick the best available NAV history source for AMFI validation."""
    for candidate in NAV_HISTORY_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in NAV_HISTORY_CANDIDATES)
    raise FileNotFoundError(f"Required NAV history file not found. Checked: {searched}")


def extract_code_set(dataframe: pd.DataFrame, logical_name: str) -> Set[str]:
    """Extract a normalized set of scheme codes from the dataset."""
    code_column = find_column(
        dataframe.columns,
        ["amfi_code", "amfi code", "scheme_code", "scheme code", "code"],
    )

    if not code_column:
        raise KeyError(f"Could not find a scheme code column in {logical_name}.")

    return set(
        dataframe[code_column]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace(".0", "", regex=False)
        .unique()
    )


def write_summary(markdown: str) -> None:
    """Persist a short Day 1 data quality summary."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_FILE.write_text(markdown, encoding="utf-8")


def main() -> None:
    """Validate that fund master AMFI codes exist in NAV history."""
    try:
        fund_master = load_dataset(FUND_MASTER_FILE)
        nav_history_file = resolve_nav_history_file()
        nav_history = load_dataset(nav_history_file)

        fund_master_codes = extract_code_set(fund_master, "fund_master.csv")
        nav_history_codes = extract_code_set(nav_history, nav_history_file.name)

        missing_codes = sorted(fund_master_codes - nav_history_codes)
        matched_codes = sorted(fund_master_codes & nav_history_codes)

        print("AMFI Validation Summary")
        print("=" * 80)
        print(f"Fund master scheme codes: {len(fund_master_codes)}")
        print(f"NAV history scheme codes: {len(nav_history_codes)}")
        print(f"Matched scheme codes: {len(matched_codes)}")
        print(f"Missing scheme codes: {len(missing_codes)}")

        summary_lines = [
            "# Day 1 Data Quality Report",
            "",
            "## AMFI Validation Summary",
            "",
            f"- NAV history file used: `{nav_history_file.name}`",
            f"- Fund master scheme codes: {len(fund_master_codes)}",
            f"- NAV history scheme codes: {len(nav_history_codes)}",
            f"- Matched scheme codes: {len(matched_codes)}",
            f"- Missing scheme codes: {len(missing_codes)}",
        ]

        if missing_codes:
            print("\nMissing codes:")
            for code in missing_codes:
                print(f"- {code}")
            LOGGER.warning("Missing AMFI/scheme codes detected: %s", missing_codes)
            summary_lines.extend(
                [
                    "",
                    "## Missing Codes",
                    "",
                    *[f"- {code}" for code in missing_codes],
                ]
            )
        else:
            print(f"\nAll fund master scheme codes are present in {nav_history_file.name}")
            LOGGER.info("All fund master scheme codes were validated successfully.")
            summary_lines.extend(
                [
                    "",
                    "## Missing Codes",
                    "",
                    f"- None. Every fund master scheme code exists in {nav_history_file.name}.",
                ]
            )

        write_summary("\n".join(summary_lines) + "\n")

    except FileNotFoundError as exc:
        LOGGER.error(str(exc))
        print(str(exc))
        write_summary(
            "\n".join(
                [
                    "# Day 1 Data Quality Report",
                    "",
                    "## AMFI Validation Summary",
                    "",
                    f"- Validation blocked: {exc}",
                    "- Current implication: fund_master-driven code coverage cannot be confirmed yet.",
                ]
            )
            + "\n"
        )
    except KeyError as exc:
        LOGGER.error(str(exc))
        print(str(exc))
    except pd.errors.EmptyDataError as exc:
        LOGGER.error("One of the input CSV files is empty: %s", exc)
        print(f"One of the input CSV files is empty: {exc}")
    except Exception as exc:  # pragma: no cover - defensive logging
        LOGGER.exception("Unexpected validation error: %s", exc)
        print(f"Unexpected validation error: {exc}")


if __name__ == "__main__":
    main()
