"""Download historical NAV data from mfapi.in for selected mutual funds."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
LOG_FILE = REPORTS_DIR / "day1_nav_fetch.log"
API_URL = "https://api.mfapi.in/mf/{scheme_code}"
REQUEST_TIMEOUT = 30

FUNDS: Dict[str, str] = {
    "125497": "HDFC Top 100 Direct",
    "119551": "SBI Bluechip",
    "120503": "ICICI Bluechip",
    "118632": "Nippon Large Cap",
    "119092": "Axis Bluechip",
    "120841": "Kotak Bluechip",
}


def configure_logging() -> logging.Logger:
    """Configure logging for NAV download operations."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("live_nav_fetch")
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


def sanitize_filename(name: str) -> str:
    """Convert a fund name to a filesystem-friendly CSV file name."""
    cleaned = "".join(character if character.isalnum() else "_" for character in name)
    return "_".join(part for part in cleaned.split("_") if part).lower()


def fetch_nav_history(scheme_code: str, scheme_name: str) -> pd.DataFrame:
    """Fetch historical NAV data for a single scheme code."""
    url = API_URL.format(scheme_code=scheme_code)
    LOGGER.info("Fetching NAV data for %s (%s)", scheme_name, scheme_code)

    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    meta = payload.get("meta", {})

    records = payload.get("data", [])
    if not records:
        raise ValueError(f"No NAV data returned for {scheme_name} ({scheme_code})")

    dataframe = pd.DataFrame(records)
    dataframe["scheme_code"] = scheme_code
    dataframe["requested_scheme_name"] = scheme_name
    dataframe["scheme_name"] = meta.get("scheme_name", scheme_name)
    dataframe["fund_house"] = meta.get("fund_house")
    dataframe["scheme_type"] = meta.get("scheme_type")
    dataframe["scheme_category"] = meta.get("scheme_category")

    if dataframe["scheme_name"].iat[0] != scheme_name:
        LOGGER.warning(
            "Requested label '%s' differs from API scheme name '%s' for scheme code %s",
            scheme_name,
            dataframe["scheme_name"].iat[0],
            scheme_code,
        )

    if "date" in dataframe.columns:
        dataframe["date"] = pd.to_datetime(
            dataframe["date"], format="%d-%m-%Y", errors="coerce"
        )

    if "nav" in dataframe.columns:
        dataframe["nav"] = pd.to_numeric(dataframe["nav"], errors="coerce")

    dataframe = dataframe.sort_values("date").reset_index(drop=True)
    return dataframe


def save_fund_history(dataframe: pd.DataFrame, scheme_name: str, scheme_code: str) -> Path:
    """Save a single fund NAV history to CSV."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{scheme_code}_{sanitize_filename(scheme_name)}.csv"
    output_path = RAW_DATA_DIR / filename
    dataframe.to_csv(output_path, index=False)
    LOGGER.info("Saved %s rows to %s", len(dataframe), output_path.name)
    return output_path


def save_combined_history(dataframes: List[pd.DataFrame]) -> Path:
    """Save the combined NAV history file used for validation workflows."""
    combined = pd.concat(dataframes, ignore_index=True)
    output_path = RAW_DATA_DIR / "nav_history.csv"
    combined.to_csv(output_path, index=False)
    LOGGER.info("Saved combined NAV history to %s", output_path.name)
    return output_path


def main() -> None:
    """Fetch NAV histories for the required mutual funds."""
    successful_downloads: List[pd.DataFrame] = []

    for scheme_code, scheme_name in FUNDS.items():
        try:
            dataframe = fetch_nav_history(scheme_code=scheme_code, scheme_name=scheme_name)
            save_fund_history(dataframe, scheme_name=scheme_name, scheme_code=scheme_code)
            successful_downloads.append(dataframe)
        except requests.RequestException as exc:
            LOGGER.error(
                "Network error while fetching %s (%s): %s",
                scheme_name,
                scheme_code,
                exc,
            )
        except ValueError as exc:
            LOGGER.error("Data validation error for %s (%s): %s", scheme_name, scheme_code, exc)
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.exception("Unexpected error for %s (%s): %s", scheme_name, scheme_code, exc)

    if successful_downloads:
        save_combined_history(successful_downloads)
        print(f"Downloaded NAV history for {len(successful_downloads)} fund(s).")
    else:
        LOGGER.warning("No NAV histories were downloaded successfully.")
        print("No NAV histories were downloaded successfully.")


if __name__ == "__main__":
    main()
