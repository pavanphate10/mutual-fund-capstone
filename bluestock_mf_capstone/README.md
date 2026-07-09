# Mutual Fund Analytics Capstone Project

## Overview

This repository packages the Mutual Fund Analytics capstone into a cleaner submission layout with reusable scripts, notebooks, SQL assets, dashboard files, and generated deliverables.

## Folder Structure

```text
bluestock_mf_capstone/
├── data/
│   ├── raw/
│   ├── processed/
│   └── db/
├── dashboard/
├── docs/
├── notebooks/
│   ├── 01_data_ingestion.ipynb
│   ├── 02_data_cleaning.ipynb
│   ├── 03_eda_analysis.ipynb
│   ├── 04_performance_analytics.ipynb
│   └── 05_advanced_analytics.ipynb
├── reports/
├── scripts/
│   ├── advanced_analytics.py
│   ├── compute_metrics.py
│   ├── data_ingestion.py
│   ├── day2_pipeline.py
│   ├── efficient_frontier.py
│   ├── email_report.py
│   ├── etl_pipeline.py
│   ├── fund_master_exploration.py
│   ├── live_nav_fetch.py
│   ├── monte_carlo_simulation.py
│   ├── performance_analytics.py
│   ├── recommender.py
│   ├── schedule_etl.py
│   └── validate_amfi_codes.py
├── sql/
│   ├── queries.sql
│   └── schema.sql
├── .gitignore
├── LICENSE
├── README.md
├── requirements.txt
├── streamlit_app.py
└── reports/
```

## Setup

Run these commands from the `bluestock_mf_capstone` directory:

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
- `reports/fund_scorecard.csv`
- `reports/alpha_beta.csv`
- `reports/benchmark_comparison_chart.png`

### Advanced Analytics Deliverables

```powershell
python .\scripts\advanced_analytics.py
python .\scripts\recommender.py Moderate
```

Outputs:

- `notebooks/05_advanced_analytics.ipynb`
- `reports/var_cvar_report.csv`
- `reports/rolling_sharpe_chart.png`

### Bonus Deliverables

```powershell
python .\scripts\email_report.py
python .\scripts\monte_carlo_simulation.py
python .\scripts\efficient_frontier.py
streamlit run .\streamlit_app.py
```

Generated artifacts include:

- `reports/weekly_report.html`
- `reports/monte_carlo_projection.csv`
- `reports/efficient_frontier.csv`
- `streamlit_app.py` for the interactive dashboard alternative

## Notes

- All scripts use `pathlib.Path` and resolve paths from the project root.
- The SQLite database is stored under `data/db/` and ignored by Git via `.gitignore`.
- Generated logs remain under `reports/` for traceability.
