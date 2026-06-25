# Mutual Fund Analytics Capstone Project

## Project Overview

This project is a Python-based capstone for Mutual Fund Analytics, focused on **Day 1: Data Ingestion**. It provides a clean project structure and production-ready scripts to:

- download live historical NAV data from `https://api.mfapi.in`
- profile and validate raw CSV files
- explore fund master metadata
- validate AMFI/scheme codes across datasets
- document Day 1 data quality findings

## Folder Structure

```text
mutual_fund_project/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── sql/
├── dashboard/
├── reports/
│   └── day1_data_quality.md
├── data_ingestion.py
├── live_nav_fetch.py
├── fund_master_exploration.py
├── validate_amfi_codes.py
├── requirements.txt
└── README.md
```

## Setup Instructions

1. Create and activate a Python virtual environment.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Install dependencies.

```powershell
pip install -r requirements.txt
```

3. Place any source datasets such as `fund_master.csv` inside `data/raw/`.

## How to Run

Run the commands below from the `mutual_fund_project` directory.

### 1. Fetch live NAV data

```powershell
python live_nav_fetch.py
```

What it does:

- downloads historical NAV data for six large-cap mutual funds
- saves one CSV per fund in `data/raw/`
- creates a combined `data/raw/nav_history.csv` file for validation

### 2. Ingest and profile raw CSV files

```powershell
python data_ingestion.py
```

What it does:

- loads all CSV files from `data/raw/`
- prints file name, shape, data types, preview rows, missing values, and duplicate counts
- logs ingestion issues and anomalies to `reports/day1_data_ingestion.log`

### 3. Explore the fund master dataset

```powershell
python fund_master_exploration.py
```

What it does:

- loads `data/raw/fund_master.csv`
- prints unique fund houses, categories, sub-categories, and risk grades
- generates summary statistics and lightweight insights

### 4. Validate AMFI codes

```powershell
python validate_amfi_codes.py
```

What it does:

- compares AMFI/scheme codes from `fund_master.csv` and `nav_history.csv`
- reports missing codes and prints a validation summary

## Deliverables

- project scaffold for the Mutual Fund Analytics capstone
- dependency manifest in `requirements.txt`
- live NAV ingestion script
- raw CSV ingestion and anomaly detection script
- fund master exploration script
- AMFI/scheme code validation script
- Day 1 data quality report template in `reports/day1_data_quality.md`

## Notes

- The project uses defensive error handling and logging across all scripts.
- `fund_master.csv` is expected to be provided separately in `data/raw/`.
- Generated logs are stored in the `reports/` folder for traceability.
