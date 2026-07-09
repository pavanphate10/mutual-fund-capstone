"""Day 1 data ingestion workflow for the Mutual Fund Analytics project."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_FILE = REPORTS_DIR / "day1_data_ingestion.log"
EXPECTED_DATASET_COUNT = 10


def configure_logging() -> logging.Logger:
    """Configure application logging for console and file output."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("data_ingestion")
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


def get_csv_files(directory: Path) -> List[Path]:
    """Return all CSV files from the provided directory."""
    return sorted(directory.glob("*.csv"))


def detect_anomalies(dataframe: pd.DataFrame, file_path: Path) -> List[str]:
    """Return a concise list of notable dataset anomalies."""
    anomalies: List[str] = []

    if dataframe.empty:
        anomalies.append("dataset is empty")

    duplicate_count = int(dataframe.duplicated().sum())
    if duplicate_count > 0:
        anomalies.append(f"{duplicate_count} duplicate row(s)")

    missing_columns = dataframe.columns[dataframe.isna().any()].tolist()
    if missing_columns:
        anomalies.append(
            "missing values in "
            + ", ".join(str(column) for column in missing_columns[:5])
            + ("..." if len(missing_columns) > 5 else "")
        )

    unnamed_columns = [column for column in dataframe.columns if str(column).startswith("Unnamed")]
    if unnamed_columns:
        anomalies.append(f"unexpected index-like columns: {', '.join(map(str, unnamed_columns))}")

    if "date" in dataframe.columns:
        parsed_dates = pd.to_datetime(dataframe["date"], errors="coerce", format="mixed")
        if parsed_dates.isna().any():
            anomalies.append("some date values could not be parsed")

    if "nav" in dataframe.columns:
        parsed_nav = pd.to_numeric(dataframe["nav"], errors="coerce")
        if parsed_nav.isna().any():
            anomalies.append("some NAV values are non-numeric")
        elif (parsed_nav <= 0).any():
            anomalies.append("some NAV values are non-positive")

    if not anomalies:
        anomalies.append("no obvious anomalies detected")

    LOGGER.info("Anomaly scan for %s: %s", file_path.name, anomalies)
    return anomalies


def summarize_dataframe(dataframe: pd.DataFrame, file_path: Path) -> Dict[str, object]:
    """Print and log high-level information about a dataframe."""
    print(f"\n{'=' * 80}")
    print(f"File: {file_path.name}")
    print(f"Shape: {dataframe.shape}")
    print("\nData types:")
    print(dataframe.dtypes)
    print("\nHead:")
    print(dataframe.head())

    missing_summary = dataframe.isna().sum()
    duplicate_count = int(dataframe.duplicated().sum())

    print("\nMissing values:")
    print(missing_summary[missing_summary > 0] if missing_summary.sum() else "None")
    print(f"\nDuplicate rows: {duplicate_count}")

    anomalies = detect_anomalies(dataframe, file_path)
    print("\nAnomalies:")
    for anomaly in anomalies:
        print(f"- {anomaly}")

    LOGGER.info("Processed %s with shape %s", file_path.name, dataframe.shape)

    if missing_summary.sum() > 0:
        LOGGER.warning(
            "Missing values found in %s: %s",
            file_path.name,
            missing_summary[missing_summary > 0].to_dict(),
        )

    if duplicate_count > 0:
        LOGGER.warning(
            "Duplicate rows found in %s: %s", file_path.name, duplicate_count
        )

    if dataframe.empty:
        LOGGER.warning("File %s is empty.", file_path.name)

    return {
        "file_name": file_path.name,
        "rows": int(dataframe.shape[0]),
        "columns": int(dataframe.shape[1]),
        "missing_values": missing_summary.to_dict(),
        "duplicate_rows": duplicate_count,
        "anomalies": anomalies,
    }


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file with defensive parsing."""
    try:
        return pd.read_csv(file_path)
    except UnicodeDecodeError:
        LOGGER.warning(
            "Unicode decoding issue in %s. Retrying with latin1 encoding.",
            file_path.name,
        )
        return pd.read_csv(file_path, encoding="latin1")


def ingest_all_csvs() -> List[Dict[str, object]]:
    """Load and profile every CSV file in the raw data directory."""
    LOGGER.info("Starting CSV ingestion from %s", RAW_DATA_DIR)
    csv_files = get_csv_files(RAW_DATA_DIR)

    if not csv_files:
        LOGGER.warning("No CSV files found in %s", RAW_DATA_DIR)
        print(f"No CSV files found in {RAW_DATA_DIR}")
        return []

    print(f"Discovered {len(csv_files)} CSV file(s) in {RAW_DATA_DIR}")
    if len(csv_files) < EXPECTED_DATASET_COUNT:
        missing_count = EXPECTED_DATASET_COUNT - len(csv_files)
        print(
            f"Expected {EXPECTED_DATASET_COUNT} dataset(s) for Day 1, "
            f"but only found {len(csv_files)}. Missing count: {missing_count}."
        )
        LOGGER.warning(
            "Expected %s datasets but found only %s in %s",
            EXPECTED_DATASET_COUNT,
            len(csv_files),
            RAW_DATA_DIR,
        )

    summaries: List[Dict[str, object]] = []

    for file_path in csv_files:
        try:
            dataframe = load_csv(file_path)
            summary = summarize_dataframe(dataframe, file_path)
            summaries.append(summary)
        except pd.errors.EmptyDataError:
            LOGGER.error("Skipped %s because it is empty.", file_path.name)
        except pd.errors.ParserError as exc:
            LOGGER.error("Parser error in %s: %s", file_path.name, exc)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Unexpected error while processing %s: %s", file_path, exc)

    LOGGER.info("Completed CSV ingestion for %s file(s).", len(summaries))
    return summaries


def main() -> None:
    """Run the Day 1 ingestion process."""
    ingest_all_csvs()


if __name__ == "__main__":
    main()
