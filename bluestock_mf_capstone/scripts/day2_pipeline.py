"""Day 2 pipeline: clean datasets, build SQLite warehouse, and export SQL assets."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"
DOCS_DIR = PROJECT_ROOT / "docs"
DB_PATH = PROJECT_ROOT / "data" / "db" / "bluestock_mf.db"
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"
QUERIES_PATH = PROJECT_ROOT / "sql" / "queries.sql"
DATA_DICTIONARY_PATH = DOCS_DIR / "methodology.md"
LOAD_REPORT_PATH = REPORTS_DIR / "day2_load_verification.md"
LOG_FILE = REPORTS_DIR / "day2_pipeline.log"

EXPECTED_FILES = {
    "fund_master": "fund_master.csv",
    "nav_history": "02_nav_history.csv",
    "aum_by_fund_house": "aum_by_fund_house.csv",
    "monthly_sip_inflows": "monthly_sip_inflows.csv",
    "category_inflows": "category_inflows.csv",
    "industry_folio_count": "industry_folio_count.csv",
    "scheme_performance": "scheme_performance.csv",
    "investor_transactions": "investor_transactions.csv",
    "portfolio_holdings": "portfolio_holdings.csv",
    "benchmark_indices": "benchmark_indices.csv",
}

NUMERIC_COLUMNS: Dict[str, List[str]] = {
    "fund_master": [
        "amfi_code",
        "expense_ratio_pct",
        "exit_load_pct",
        "min_sip_amount",
        "min_lumpsum_amount",
    ],
    "nav_history": ["amfi_code", "nav"],
    "aum_by_fund_house": ["aum_lakh_crore", "aum_crore", "num_schemes"],
    "monthly_sip_inflows": [
        "sip_inflow_crore",
        "active_sip_accounts_crore",
        "new_sip_accounts_lakh",
        "sip_aum_lakh_crore",
        "yoy_growth_pct",
    ],
    "category_inflows": ["net_inflow_crore"],
    "industry_folio_count": [
        "total_folios_crore",
        "equity_folios_crore",
        "debt_folios_crore",
        "hybrid_folios_crore",
        "others_folios_crore",
    ],
    "scheme_performance": [
        "amfi_code",
        "return_1yr_pct",
        "return_3yr_pct",
        "return_5yr_pct",
        "benchmark_3yr_pct",
        "alpha",
        "beta",
        "sharpe_ratio",
        "sortino_ratio",
        "std_dev_ann_pct",
        "max_drawdown_pct",
        "aum_crore",
        "expense_ratio_pct",
        "morningstar_rating",
    ],
    "investor_transactions": ["amfi_code", "amount_inr", "annual_income_lakh"],
    "portfolio_holdings": [
        "amfi_code",
        "weight_pct",
        "market_value_cr",
        "current_price_inr",
    ],
    "benchmark_indices": ["close_value"],
}


def configure_logging() -> logging.Logger:
    """Configure file and console logging."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("day2_pipeline")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


LOGGER = configure_logging()


def load_csv(file_name: str) -> pd.DataFrame:
    """Load a CSV from the raw data directory."""
    return pd.read_csv(RAW_DIR / file_name)


def to_datetime_column(dataframe: pd.DataFrame, column: str) -> pd.Series:
    """Parse a series to pandas datetime."""
    return pd.to_datetime(dataframe[column], errors="coerce")


def normalize_numeric_columns(dataset_name: str, dataframe: pd.DataFrame) -> pd.DataFrame:
    """Coerce known numeric columns to numeric types."""
    for column in NUMERIC_COLUMNS.get(dataset_name, []):
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
    return dataframe


def clean_nav_history(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Clean NAV history and attach anomaly flags."""
    issues: List[str] = []
    dataframe = dataframe.copy()
    dataframe = normalize_numeric_columns("nav_history", dataframe)
    dataframe["date"] = to_datetime_column(dataframe, "date")

    bad_dates = int(dataframe["date"].isna().sum())
    if bad_dates:
        issues.append(f"{bad_dates} NAV rows had invalid dates and were dropped.")
        dataframe = dataframe.dropna(subset=["date"])

    duplicate_count = int(dataframe.duplicated(subset=["amfi_code", "date"]).sum())
    if duplicate_count:
        issues.append(f"{duplicate_count} duplicate NAV rows removed.")
        dataframe = dataframe.drop_duplicates(subset=["amfi_code", "date"], keep="last")

    dataframe = dataframe.sort_values(["amfi_code", "date"]).reset_index(drop=True)

    non_positive_count = int((dataframe["nav"] <= 0).sum())
    if non_positive_count:
        issues.append(f"{non_positive_count} rows with NAV <= 0 removed.")
        dataframe = dataframe[dataframe["nav"] > 0].copy()

    dataframe["nav"] = dataframe.groupby("amfi_code")["nav"].ffill()
    remaining_missing_nav = int(dataframe["nav"].isna().sum())
    if remaining_missing_nav:
        issues.append(
            f"{remaining_missing_nav} rows still have missing NAV after forward fill."
        )

    dataframe["date"] = dataframe["date"].dt.strftime("%Y-%m-%d")
    dataframe["nav_quality_flag"] = "OK"
    if not issues:
        issues.append(
            "NAV source had no duplicates, no invalid dates, and no non-positive NAV values. "
            "Forward fill did not materially change rows because the source already had populated NAV values."
        )
    return dataframe, issues


def clean_investor_transactions(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Standardize transactions and validate core fields."""
    issues: List[str] = []
    dataframe = dataframe.copy()
    dataframe = normalize_numeric_columns("investor_transactions", dataframe)

    dataframe["transaction_date"] = to_datetime_column(dataframe, "transaction_date")
    bad_dates = int(dataframe["transaction_date"].isna().sum())
    if bad_dates:
        issues.append(f"{bad_dates} transaction rows had invalid dates and were dropped.")
        dataframe = dataframe.dropna(subset=["transaction_date"])

    mapping = {
        "sip": "SIP",
        "systematic investment plan": "SIP",
        "lumpsum": "Lumpsum",
        "lump sum": "Lumpsum",
        "redemption": "Redemption",
        "redeem": "Redemption",
    }
    normalized_types = (
        dataframe["transaction_type"]
        .astype(str)
        .str.strip()
        .str.lower()
        .map(mapping)
    )
    unknown_types = sorted(
        dataframe.loc[normalized_types.isna(), "transaction_type"].astype(str).unique()
    )
    if unknown_types:
        issues.append(
            "Unknown transaction_type values found: " + ", ".join(unknown_types)
        )
        normalized_types = normalized_types.fillna("Unknown")
    dataframe["transaction_type"] = normalized_types

    non_positive_count = int((dataframe["amount_inr"] <= 0).sum())
    if non_positive_count:
        issues.append(f"{non_positive_count} transaction rows with amount <= 0 removed.")
        dataframe = dataframe[dataframe["amount_inr"] > 0].copy()

    allowed_kyc = {"Verified", "Pending"}
    dataframe["kyc_status"] = dataframe["kyc_status"].astype(str).str.strip().str.title()
    invalid_kyc = sorted(set(dataframe["kyc_status"]) - allowed_kyc)
    if invalid_kyc:
        issues.append("Unexpected KYC status values: " + ", ".join(invalid_kyc))
        dataframe["kyc_status"] = dataframe["kyc_status"].where(
            dataframe["kyc_status"].isin(allowed_kyc), "Unknown"
        )

    dataframe["transaction_date"] = dataframe["transaction_date"].dt.strftime("%Y-%m-%d")
    if not issues:
        issues.append(
            "Transaction types were standardized, dates normalized, and all source amounts/KYC values passed validation."
        )
    return dataframe, issues


def clean_scheme_performance(dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate numeric performance fields and flag expense anomalies."""
    issues: List[str] = []
    dataframe = dataframe.copy()
    dataframe = normalize_numeric_columns("scheme_performance", dataframe)

    numeric_columns = NUMERIC_COLUMNS["scheme_performance"][1:]
    anomaly_flags: List[str] = []
    for _, row in dataframe.iterrows():
        flags: List[str] = []
        for column in numeric_columns:
            if pd.isna(row[column]):
                flags.append(f"NON_NUMERIC_{column.upper()}")
        expense_ratio = row["expense_ratio_pct"]
        if not pd.isna(expense_ratio) and not (0.1 <= expense_ratio <= 2.5):
            flags.append("EXPENSE_RATIO_OUTSIDE_EXPECTED_RANGE")
        anomaly_flags.append("OK" if not flags else ";".join(flags))

    dataframe["anomaly_flag"] = anomaly_flags
    flagged_rows = int((dataframe["anomaly_flag"] != "OK").sum())
    if flagged_rows:
        issues.append(f"{flagged_rows} scheme rows were flagged for numeric anomalies.")
    else:
        issues.append(
            "All return and risk fields are numeric, and all expense ratios fall within 0.1% to 2.5%."
        )
    return dataframe, issues


def clean_common_dataset(
    dataset_name: str,
    dataframe: pd.DataFrame,
    date_columns: Iterable[str],
) -> Tuple[pd.DataFrame, List[str]]:
    """Apply basic normalization for datasets without special business rules."""
    issues: List[str] = []
    dataframe = dataframe.copy()
    dataframe = normalize_numeric_columns(dataset_name, dataframe)

    for column in date_columns:
        dataframe[column] = to_datetime_column(dataframe, column)
        bad_dates = int(dataframe[column].isna().sum())
        if bad_dates:
            issues.append(f"{bad_dates} invalid values found in {column}.")
        dataframe[column] = dataframe[column].dt.strftime("%Y-%m-%d")

    duplicate_count = int(dataframe.duplicated().sum())
    if duplicate_count:
        issues.append(f"{duplicate_count} exact duplicate rows detected.")
        dataframe = dataframe.drop_duplicates().copy()

    if not issues:
        issues.append("No material data quality issues detected during standard cleaning.")
    return dataframe, issues


def build_cleaned_datasets() -> Tuple[Dict[str, pd.DataFrame], Dict[str, List[str]]]:
    """Clean all Day 2 datasets and return them with issue summaries."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cleaned: Dict[str, pd.DataFrame] = {}
    issues: Dict[str, List[str]] = {}

    fund_master, issues["fund_master"] = clean_common_dataset(
        "fund_master", load_csv(EXPECTED_FILES["fund_master"]), ["launch_date"]
    )
    cleaned["fund_master"] = fund_master

    nav_history, issues["nav_history"] = clean_nav_history(
        load_csv(EXPECTED_FILES["nav_history"])
    )
    cleaned["nav_history"] = nav_history

    aum, issues["aum_by_fund_house"] = clean_common_dataset(
        "aum_by_fund_house", load_csv(EXPECTED_FILES["aum_by_fund_house"]), ["date"]
    )
    cleaned["aum_by_fund_house"] = aum

    monthly_sip, issues["monthly_sip_inflows"] = clean_common_dataset(
        "monthly_sip_inflows", load_csv(EXPECTED_FILES["monthly_sip_inflows"]), ["month"]
    )
    cleaned["monthly_sip_inflows"] = monthly_sip

    category_inflows, issues["category_inflows"] = clean_common_dataset(
        "category_inflows", load_csv(EXPECTED_FILES["category_inflows"]), ["month"]
    )
    cleaned["category_inflows"] = category_inflows

    folios, issues["industry_folio_count"] = clean_common_dataset(
        "industry_folio_count", load_csv(EXPECTED_FILES["industry_folio_count"]), ["month"]
    )
    cleaned["industry_folio_count"] = folios

    scheme_performance, issues["scheme_performance"] = clean_scheme_performance(
        load_csv(EXPECTED_FILES["scheme_performance"])
    )
    cleaned["scheme_performance"] = scheme_performance

    transactions, issues["investor_transactions"] = clean_investor_transactions(
        load_csv(EXPECTED_FILES["investor_transactions"])
    )
    cleaned["investor_transactions"] = transactions

    portfolio, issues["portfolio_holdings"] = clean_common_dataset(
        "portfolio_holdings",
        load_csv(EXPECTED_FILES["portfolio_holdings"]),
        ["portfolio_date"],
    )
    cleaned["portfolio_holdings"] = portfolio

    benchmark, issues["benchmark_indices"] = clean_common_dataset(
        "benchmark_indices",
        load_csv(EXPECTED_FILES["benchmark_indices"]),
        ["date"],
    )
    cleaned["benchmark_indices"] = benchmark

    for name, dataframe in cleaned.items():
        output_path = PROCESSED_DIR / f"{name}.csv"
        dataframe.to_csv(output_path, index=False)
        LOGGER.info("Saved cleaned dataset to %s", output_path)

    return cleaned, issues


def build_dim_date(cleaned: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construct a shared date dimension."""
    all_dates = pd.concat(
        [
            pd.to_datetime(cleaned["fund_master"]["launch_date"]),
            pd.to_datetime(cleaned["nav_history"]["date"]),
            pd.to_datetime(cleaned["aum_by_fund_house"]["date"]),
            pd.to_datetime(cleaned["monthly_sip_inflows"]["month"]),
            pd.to_datetime(cleaned["category_inflows"]["month"]),
            pd.to_datetime(cleaned["industry_folio_count"]["month"]),
            pd.to_datetime(cleaned["investor_transactions"]["transaction_date"]),
            pd.to_datetime(cleaned["portfolio_holdings"]["portfolio_date"]),
            pd.to_datetime(cleaned["benchmark_indices"]["date"]),
        ],
        ignore_index=True,
    ).dropna()

    dim_date = pd.DataFrame({"full_date": sorted(all_dates.unique())})
    dim_date["date_key"] = dim_date["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim_date["day"] = dim_date["full_date"].dt.day
    dim_date["month"] = dim_date["full_date"].dt.month
    dim_date["month_name"] = dim_date["full_date"].dt.month_name()
    dim_date["quarter"] = dim_date["full_date"].dt.quarter
    dim_date["year"] = dim_date["full_date"].dt.year
    dim_date["day_of_week"] = dim_date["full_date"].dt.day_name()
    dim_date["is_weekend"] = dim_date["full_date"].dt.dayofweek >= 5
    dim_date["full_date"] = dim_date["full_date"].dt.strftime("%Y-%m-%d")
    return dim_date[
        [
            "date_key",
            "full_date",
            "day",
            "month",
            "month_name",
            "quarter",
            "year",
            "day_of_week",
            "is_weekend",
        ]
    ]


def build_dim_fund(cleaned: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Construct the fund dimension from fund master and scheme performance."""
    fund_master = cleaned["fund_master"].copy()
    performance_subset = cleaned["scheme_performance"][
        ["amfi_code", "aum_crore", "expense_ratio_pct", "risk_grade", "morningstar_rating"]
    ].copy()

    dim_fund = fund_master.merge(
        performance_subset,
        on="amfi_code",
        how="left",
        suffixes=("", "_performance"),
    )
    dim_fund = dim_fund.rename(columns={"risk_category": "risk_category_master"})
    dim_fund["fund_key"] = range(1, len(dim_fund) + 1)
    return dim_fund[
        [
            "fund_key",
            "amfi_code",
            "fund_house",
            "scheme_name",
            "category",
            "sub_category",
            "plan",
            "launch_date",
            "benchmark",
            "expense_ratio_pct",
            "exit_load_pct",
            "min_sip_amount",
            "min_lumpsum_amount",
            "fund_manager",
            "risk_category_master",
            "risk_grade",
            "morningstar_rating",
            "sebi_category_code",
            "aum_crore",
        ]
    ]


def build_star_facts(
    cleaned: Dict[str, pd.DataFrame], dim_fund: pd.DataFrame, dim_date: pd.DataFrame
) -> Dict[str, pd.DataFrame]:
    """Create fact tables for the requested star schema."""
    fund_key_map = dim_fund.set_index("amfi_code")["fund_key"]
    date_key_map = dim_date.set_index("full_date")["date_key"]

    fact_nav = cleaned["nav_history"].copy()
    fact_nav["fund_key"] = fact_nav["amfi_code"].map(fund_key_map)
    fact_nav["date_key"] = fact_nav["date"].map(date_key_map)
    fact_nav["nav_id"] = range(1, len(fact_nav) + 1)
    fact_nav = fact_nav[
        ["nav_id", "fund_key", "date_key", "amfi_code", "nav", "nav_quality_flag"]
    ]

    fact_transactions = cleaned["investor_transactions"].copy()
    fact_transactions["fund_key"] = fact_transactions["amfi_code"].map(fund_key_map)
    fact_transactions["date_key"] = fact_transactions["transaction_date"].map(date_key_map)
    fact_transactions["transaction_id_key"] = range(1, len(fact_transactions) + 1)
    fact_transactions = fact_transactions[
        [
            "transaction_id_key",
            "fund_key",
            "date_key",
            "investor_id",
            "amfi_code",
            "transaction_type",
            "amount_inr",
            "state",
            "city",
            "city_tier",
            "age_group",
            "gender",
            "annual_income_lakh",
            "payment_mode",
            "kyc_status",
        ]
    ]

    fact_performance = cleaned["scheme_performance"].copy()
    fact_performance["fund_key"] = fact_performance["amfi_code"].map(fund_key_map)
    fact_performance["performance_id"] = range(1, len(fact_performance) + 1)
    fact_performance = fact_performance[
        [
            "performance_id",
            "fund_key",
            "amfi_code",
            "return_1yr_pct",
            "return_3yr_pct",
            "return_5yr_pct",
            "benchmark_3yr_pct",
            "alpha",
            "beta",
            "sharpe_ratio",
            "sortino_ratio",
            "std_dev_ann_pct",
            "max_drawdown_pct",
            "aum_crore",
            "expense_ratio_pct",
            "morningstar_rating",
            "anomaly_flag",
        ]
    ]

    fact_aum = cleaned["aum_by_fund_house"].copy()
    fact_aum["date_key"] = fact_aum["date"].map(date_key_map)
    fact_aum["aum_id"] = range(1, len(fact_aum) + 1)
    fact_aum = fact_aum[
        [
            "aum_id",
            "date_key",
            "fund_house",
            "aum_lakh_crore",
            "aum_crore",
            "num_schemes",
        ]
    ]

    return {
        "fact_nav": fact_nav,
        "fact_transactions": fact_transactions,
        "fact_performance": fact_performance,
        "fact_aum": fact_aum,
    }


def write_schema_sql() -> str:
    """Return and persist the warehouse schema DDL."""
    schema_sql = """
DROP TABLE IF EXISTS dim_fund;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS fact_nav;
DROP TABLE IF EXISTS fact_transactions;
DROP TABLE IF EXISTS fact_performance;
DROP TABLE IF EXISTS fact_aum;

CREATE TABLE dim_fund (
    fund_key INTEGER PRIMARY KEY,
    amfi_code INTEGER NOT NULL UNIQUE,
    fund_house TEXT NOT NULL,
    scheme_name TEXT NOT NULL,
    category TEXT NOT NULL,
    sub_category TEXT,
    plan TEXT,
    launch_date TEXT,
    benchmark TEXT,
    expense_ratio_pct REAL,
    exit_load_pct REAL,
    min_sip_amount REAL,
    min_lumpsum_amount REAL,
    fund_manager TEXT,
    risk_category_master TEXT,
    risk_grade TEXT,
    morningstar_rating INTEGER,
    sebi_category_code TEXT,
    aum_crore REAL
);

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date TEXT NOT NULL UNIQUE,
    day INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    quarter INTEGER NOT NULL,
    year INTEGER NOT NULL,
    day_of_week TEXT NOT NULL,
    is_weekend INTEGER NOT NULL
);

CREATE TABLE fact_nav (
    nav_id INTEGER PRIMARY KEY,
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    amfi_code INTEGER NOT NULL,
    nav REAL NOT NULL CHECK (nav > 0),
    nav_quality_flag TEXT NOT NULL,
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE fact_transactions (
    transaction_id_key INTEGER PRIMARY KEY,
    fund_key INTEGER NOT NULL,
    date_key INTEGER NOT NULL,
    investor_id TEXT NOT NULL,
    amfi_code INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    amount_inr REAL NOT NULL CHECK (amount_inr > 0),
    state TEXT,
    city TEXT,
    city_tier TEXT,
    age_group TEXT,
    gender TEXT,
    annual_income_lakh REAL,
    payment_mode TEXT,
    kyc_status TEXT,
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key),
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);

CREATE TABLE fact_performance (
    performance_id INTEGER PRIMARY KEY,
    fund_key INTEGER NOT NULL,
    amfi_code INTEGER NOT NULL,
    return_1yr_pct REAL,
    return_3yr_pct REAL,
    return_5yr_pct REAL,
    benchmark_3yr_pct REAL,
    alpha REAL,
    beta REAL,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    std_dev_ann_pct REAL,
    max_drawdown_pct REAL,
    aum_crore REAL,
    expense_ratio_pct REAL,
    morningstar_rating INTEGER,
    anomaly_flag TEXT NOT NULL,
    FOREIGN KEY (fund_key) REFERENCES dim_fund(fund_key)
);

CREATE TABLE fact_aum (
    aum_id INTEGER PRIMARY KEY,
    date_key INTEGER NOT NULL,
    fund_house TEXT NOT NULL,
    aum_lakh_crore REAL NOT NULL,
    aum_crore REAL NOT NULL,
    num_schemes INTEGER NOT NULL,
    FOREIGN KEY (date_key) REFERENCES dim_date(date_key)
);
""".strip()
    SCHEMA_PATH.write_text(schema_sql + "\n", encoding="utf-8")
    return schema_sql


def write_queries_sql() -> None:
    """Persist 10 analytical SQL queries."""
    queries_sql = """
-- 1. Top 5 fund houses by latest AUM
WITH latest_aum_date AS (
    SELECT MAX(date_key) AS date_key FROM fact_aum
)
SELECT fa.fund_house, fa.aum_crore
FROM fact_aum fa
JOIN latest_aum_date lad ON fa.date_key = lad.date_key
ORDER BY fa.aum_crore DESC
LIMIT 5;

-- 2. Average NAV per month
SELECT dd.year, dd.month, ROUND(AVG(fn.nav), 4) AS avg_nav
FROM fact_nav fn
JOIN dim_date dd ON fn.date_key = dd.date_key
GROUP BY dd.year, dd.month
ORDER BY dd.year, dd.month;

-- 3. SIP YoY growth by calendar month from monthly_sip_inflows
SELECT
    substr(month, 1, 4) AS year,
    ROUND(AVG(yoy_growth_pct), 2) AS avg_yoy_growth_pct
FROM monthly_sip_inflows
GROUP BY substr(month, 1, 4)
ORDER BY year;

-- 4. Transactions by state
SELECT state, COUNT(*) AS transaction_count, ROUND(SUM(amount_inr), 2) AS total_amount_inr
FROM fact_transactions
GROUP BY state
ORDER BY total_amount_inr DESC;

-- 5. Funds with expense ratio below 1 percent
SELECT scheme_name, fund_house, expense_ratio_pct
FROM dim_fund
WHERE expense_ratio_pct < 1.0
ORDER BY expense_ratio_pct ASC, scheme_name;

-- 6. Top 5 funds by 5-year return
SELECT df.scheme_name, fp.return_5yr_pct
FROM fact_performance fp
JOIN dim_fund df ON fp.fund_key = df.fund_key
ORDER BY fp.return_5yr_pct DESC
LIMIT 5;

-- 7. Highest redemption value by state
SELECT state, ROUND(SUM(amount_inr), 2) AS redemption_amount_inr
FROM fact_transactions
WHERE transaction_type = 'Redemption'
GROUP BY state
ORDER BY redemption_amount_inr DESC;

-- 8. Benchmark index monthly average close
SELECT substr(date, 1, 7) AS month, index_name, ROUND(AVG(close_value), 2) AS avg_close_value
FROM benchmark_indices
GROUP BY substr(date, 1, 7), index_name
ORDER BY month, index_name;

-- 9. Category-level monthly inflows
SELECT month, category, net_inflow_crore
FROM category_inflows
ORDER BY month, net_inflow_crore DESC;

-- 10. Portfolio concentration: top holding weight per fund
SELECT
    ph.amfi_code,
    df.scheme_name,
    MAX(ph.weight_pct) AS top_holding_weight_pct
FROM portfolio_holdings ph
LEFT JOIN dim_fund df ON ph.amfi_code = df.amfi_code
GROUP BY ph.amfi_code, df.scheme_name
ORDER BY top_holding_weight_pct DESC;
""".strip()
    QUERIES_PATH.write_text(queries_sql + "\n", encoding="utf-8")


def write_data_dictionary(cleaned: Dict[str, pd.DataFrame]) -> None:
    """Create a markdown data dictionary for the cleaned datasets."""
    source_map = {
        "fund_master": "Google Drive / 01_fund_master.csv",
        "nav_history": "Google Drive / 02_nav_history.csv",
        "aum_by_fund_house": "Google Drive / 03_aum_by_fund_house.csv",
        "monthly_sip_inflows": "Google Drive / 04_monthly_sip_inflows.csv",
        "category_inflows": "Google Drive / 05_category_inflows.csv",
        "industry_folio_count": "Google Drive / 06_industry_folio_count.csv",
        "scheme_performance": "Google Drive / 07_scheme_performance.csv",
        "investor_transactions": "Google Drive / 08_investor_transactions.csv",
        "portfolio_holdings": "Google Drive / 09_portfolio_holdings.csv",
        "benchmark_indices": "Google Drive / 10_benchmark_indices.csv",
    }

    business_definitions = {
        "amfi_code": "AMFI-issued scheme identifier for a mutual fund plan.",
        "scheme_name": "Full scheme or plan name used for investor-facing reporting.",
        "fund_house": "Asset management company managing the scheme.",
        "category": "Broad mutual fund category such as Equity or Large Cap.",
        "sub_category": "More specific style bucket inside a category.",
        "plan": "Plan type such as Direct or Regular.",
        "launch_date": "Scheme inception date.",
        "benchmark": "Reference index used to compare scheme performance.",
        "expense_ratio_pct": "Annual fund expense ratio expressed as a percent.",
        "exit_load_pct": "Redemption fee charged within the applicable holding period.",
        "min_sip_amount": "Minimum SIP ticket size in INR.",
        "min_lumpsum_amount": "Minimum one-time investment amount in INR.",
        "fund_manager": "Primary named fund manager.",
        "risk_category": "Risk profile label from the source file.",
        "risk_grade": "Performance/risk table risk label.",
        "sebi_category_code": "Internal bucket or category code aligned to SEBI classification.",
        "date": "Observation date for time-series data.",
        "month": "Monthly period stored as YYYY-MM.",
        "nav": "Net asset value per unit on the observation date.",
        "nav_quality_flag": "Pipeline quality marker for the cleaned NAV row.",
        "aum_lakh_crore": "Assets under management expressed in lakh crore INR.",
        "aum_crore": "Assets under management expressed in crore INR.",
        "num_schemes": "Count of schemes managed by the fund house in the period.",
        "sip_inflow_crore": "Monthly SIP inflow amount in crore INR.",
        "active_sip_accounts_crore": "Active SIP account count in crore accounts.",
        "new_sip_accounts_lakh": "New SIP accounts opened in the month, in lakh accounts.",
        "sip_aum_lakh_crore": "SIP-linked AUM in lakh crore INR.",
        "yoy_growth_pct": "Year-over-year growth percentage.",
        "net_inflow_crore": "Net category money flow for the month in crore INR.",
        "total_folios_crore": "Total mutual fund folios in crore units.",
        "equity_folios_crore": "Equity folios in crore units.",
        "debt_folios_crore": "Debt folios in crore units.",
        "hybrid_folios_crore": "Hybrid folios in crore units.",
        "others_folios_crore": "Other folios in crore units.",
        "return_1yr_pct": "Trailing 1-year return percentage.",
        "return_3yr_pct": "Trailing 3-year return percentage.",
        "return_5yr_pct": "Trailing 5-year return percentage.",
        "benchmark_3yr_pct": "Trailing 3-year benchmark return percentage.",
        "alpha": "Alpha versus benchmark or category.",
        "beta": "Beta versus benchmark or market.",
        "sharpe_ratio": "Sharpe ratio for risk-adjusted return.",
        "sortino_ratio": "Sortino ratio for downside-adjusted return.",
        "std_dev_ann_pct": "Annualized standard deviation percentage.",
        "max_drawdown_pct": "Maximum historical drawdown percentage.",
        "morningstar_rating": "Morningstar-style numeric rating from the source file.",
        "anomaly_flag": "Pipeline anomaly flag for numeric validation or expense-ratio checks.",
        "investor_id": "Synthetic investor identifier.",
        "transaction_date": "Date of purchase, SIP, or redemption activity.",
        "transaction_type": "Standardized transaction bucket: SIP, Lumpsum, or Redemption.",
        "amount_inr": "Transaction amount in INR.",
        "state": "Investor state.",
        "city": "Investor city.",
        "city_tier": "Investor city classification such as T30 or B30.",
        "age_group": "Investor age bucket.",
        "gender": "Investor gender label.",
        "annual_income_lakh": "Investor annual income in lakh INR.",
        "payment_mode": "Channel used to fund the transaction.",
        "kyc_status": "KYC completion state.",
        "stock_symbol": "Ticker or short symbol for a portfolio constituent.",
        "stock_name": "Name of the portfolio constituent.",
        "sector": "Sector classification for a portfolio constituent.",
        "weight_pct": "Portfolio weight of the security as a percent.",
        "market_value_cr": "Holding market value in crore INR.",
        "current_price_inr": "Security market price in INR.",
        "portfolio_date": "Portfolio disclosure date.",
        "index_name": "Benchmark or market index name.",
        "close_value": "Index closing value on the date.",
    }

    lines: List[str] = ["# Data Dictionary", ""]
    for dataset_name, dataframe in cleaned.items():
        lines.append(f"## {dataset_name}")
        lines.append("")
        lines.append(f"- Source: {source_map[dataset_name]}")
        lines.append(f"- Cleaned output: `data/processed/{dataset_name}.csv`")
        lines.append(f"- Row count: {len(dataframe)}")
        lines.append("")
        lines.append("| Column | Data Type | Business Definition |")
        lines.append("|---|---|---|")
        for column, dtype in dataframe.dtypes.items():
            definition = business_definitions.get(column, "Business definition to be confirmed.")
            lines.append(f"| {column} | {dtype} | {definition} |")
        lines.append("")

    DATA_DICTIONARY_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_load_report(
    source_frames: Dict[str, pd.DataFrame],
    cleaned_frames: Dict[str, pd.DataFrame],
    db_table_counts: Dict[str, int],
    issues: Dict[str, List[str]],
) -> None:
    """Persist row-count verification and data quality notes."""
    lines = ["# Day 2 Load Verification", ""]
    lines.append("| Dataset | Source Rows | Cleaned Rows | SQLite Rows | Notes |")
    lines.append("|---|---:|---:|---:|---|")
    for dataset_name in cleaned_frames:
        lines.append(
            "| {dataset} | {source_rows} | {cleaned_rows} | {db_rows} | {note} |".format(
                dataset=dataset_name,
                source_rows=len(source_frames[dataset_name]),
                cleaned_rows=len(cleaned_frames[dataset_name]),
                db_rows=db_table_counts.get(dataset_name, 0),
                note="; ".join(issues[dataset_name]),
            )
        )
    LOAD_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_into_sqlite(
    cleaned: Dict[str, pd.DataFrame],
) -> Dict[str, int]:
    """Load cleaned datasets and star-schema tables into SQLite."""
    if DB_PATH.exists():
        DB_PATH.unlink()

    schema_sql = write_schema_sql()
    write_queries_sql()
    write_data_dictionary(cleaned)

    dim_date = build_dim_date(cleaned)
    dim_fund = build_dim_fund(cleaned)
    facts = build_star_facts(cleaned, dim_fund, dim_date)

    engine = create_engine(f"sqlite:///{DB_PATH}")

    with engine.begin() as connection:
        for statement in [stmt.strip() for stmt in schema_sql.split(";") if stmt.strip()]:
            connection.execute(text(statement))

        for name, dataframe in cleaned.items():
            dataframe.to_sql(name, connection, if_exists="replace", index=False)

        dim_fund.to_sql("dim_fund", connection, if_exists="append", index=False)
        dim_date.to_sql("dim_date", connection, if_exists="append", index=False)
        for name, dataframe in facts.items():
            dataframe.to_sql(name, connection, if_exists="append", index=False)

    table_counts: Dict[str, int] = {}
    with engine.connect() as connection:
        for table_name in list(cleaned.keys()) + ["dim_fund", "dim_date"] + list(facts.keys()):
            count = connection.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            table_counts[table_name] = int(count)
    return table_counts


def main() -> None:
    """Run the Day 2 cleaning and SQLite load pipeline."""
    source_frames = {name: load_csv(file_name) for name, file_name in EXPECTED_FILES.items()}
    cleaned, issues = build_cleaned_datasets()
    table_counts = load_into_sqlite(cleaned)
    write_load_report(source_frames, cleaned, table_counts, issues)

    print("Day 2 pipeline complete.")
    print(f"Cleaned CSVs saved to: {PROCESSED_DIR}")
    print(f"SQLite database created at: {DB_PATH}")
    print(f"Schema SQL written to: {SCHEMA_PATH}")
    print(f"Analytical queries written to: {QUERIES_PATH}")
    print(f"Data dictionary written to: {DATA_DICTIONARY_PATH}")


if __name__ == "__main__":
    main()
