# Mutual Fund Analytics Capstone Project

## Overview

This repository packages the Mutual Fund Analytics capstone into a cleaner submission layout with reusable scripts, notebooks, SQL assets, dashboard files, and generated deliverables.

## Folder Structure

```text
mutual_fund_project/
├── data/
│   ├── raw/
│   ├── processed/
│   └── db/
├── dashboard/
├── notebooks/
│   ├── 04_performance_analytics.ipynb
│   └── 05_advanced_analytics.ipynb
├── reports/
├── scripts/
│   ├── advanced_analytics.py
│   ├── data_ingestion.py
│   ├── day2_pipeline.py
│   ├── fund_master_exploration.py
│   ├── live_nav_fetch.py
│   ├── performance_analytics.py
│   ├── recommender.py
│   └── validate_amfi_codes.py
├── sql/
│   ├── queries.sql
│   └── schema.sql
├── powerbi_assets/
├── .gitignore
├── README.md
├── alpha_beta.csv
├── benchmark_comparison_chart.png
├── fund_scorecard.csv
├── rolling_sharpe_chart.png
└── var_cvar_report.csv
```

## Setup

Run these commands from the `mutual_fund_project` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run Order

### Day 1 and Day 2 Pipeline

```powershell
python .\scripts\live_nav_fetch.py
python .\scripts\data_ingestion.py
python .\scripts\fund_master_exploration.py
python .\scripts\validate_amfi_codes.py
python .\scripts\day2_pipeline.py
```

### Performance Analytics Deliverables

```powershell
python .\scripts\performance_analytics.py
```

Outputs:

- `notebooks/04_performance_analytics.ipynb`
- `fund_scorecard.csv`
- `alpha_beta.csv`
- `benchmark_comparison_chart.png`

### Advanced Analytics Deliverables

```powershell
python .\scripts\advanced_analytics.py
python .\scripts\recommender.py Moderate
```

Outputs:

- `notebooks/05_advanced_analytics.ipynb`
- `var_cvar_report.csv`
- `rolling_sharpe_chart.png`

## Notes

- All scripts use `pathlib.Path` and resolve paths from the project root.
- The SQLite database is stored under `data/db/` and ignored by Git via `.gitignore`.
- Generated logs remain under `reports/` for traceability.
