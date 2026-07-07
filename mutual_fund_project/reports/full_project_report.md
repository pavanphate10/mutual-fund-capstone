# Full Project Report

## Project Name

Mutual Fund Analytics Capstone Project

## Project Objective

This project builds a mutual fund analytics platform that covers:

- data ingestion and cleaning
- NAV history validation
- processed dataset generation
- SQLite-ready pipeline outputs
- performance analytics
- advanced risk and investor analytics
- report-ready visual and tabular deliverables

The overall goal is to transform raw mutual fund data into a structured analytics project that can support notebooks, Python scripts, SQL analysis, and dashboard reporting.

## Project Structure

The project is organized into the following major folders:

- `data/raw/` for source CSV files
- `data/processed/` for cleaned and analysis-ready datasets
- `data/db/` for SQLite database assets
- `scripts/` for reusable Python pipelines and analytics modules
- `notebooks/` for notebook-based analysis
- `reports/` for logs, validation notes, and summary reports
- `sql/` for schema creation and query files
- `dashboard/` and `powerbi_assets/` for BI deliverables

## Available Datasets

The project uses the following cleaned datasets from `data/processed/`:

| Dataset | Rows | Purpose |
|---|---:|---|
| `fund_master.csv` | 40 | Master reference for scheme attributes, fund house, benchmark, category, and risk labels |
| `nav_history.csv` | 46000 | Daily NAV history used for return, VaR, CVaR, and rolling Sharpe calculations |
| `aum_by_fund_house.csv` | 90 | Fund house AUM trend analysis |
| `monthly_sip_inflows.csv` | 48 | SIP industry trend analysis |
| `category_inflows.csv` | 144 | Monthly category-level net flow analysis |
| `industry_folio_count.csv` | 21 | Industry folio trend analysis |
| `scheme_performance.csv` | 40 | Return, risk, Sharpe, drawdown, AUM, and rating metrics |
| `investor_transactions.csv` | 32778 | Cohort, SIP continuity, and investor behavior analytics |
| `portfolio_holdings.csv` | 322 | Concentration and HHI analysis from scheme holdings |
| `benchmark_indices.csv` | 8050 | Benchmark comparison and performance analytics |

## Data Quality and Validation Summary

### Day 1 Validation

Based on `reports/day1_data_quality.md`:

- fund master scheme codes: 40
- NAV history scheme codes: 40
- matched scheme codes: 40
- missing scheme codes: 0

This confirms that the NAV history fully matches the scheme universe in fund master.

### Day 2 Load Verification

Based on `reports/day2_load_verification.md`:

- all major datasets were loaded successfully into the cleaned layer
- no material data quality issues were reported for the main source files
- `nav_history.csv` had no duplicates, invalid dates, or non-positive NAV values
- `scheme_performance.csv` risk and return fields were validated as numeric
- `investor_transactions.csv` transaction types and dates were standardized successfully
- `portfolio_holdings.csv` loaded without material issues

## Existing Report Files

The `reports/` folder currently contains:

- `day1_nav_fetch.log`
- `day1_data_ingestion.log`
- `day1_fund_master_exploration.log`
- `day1_amfi_validation.log`
- `day1_data_quality.md`
- `day2_pipeline.log`
- `day2_load_verification.md`

These files provide traceability for ingestion, validation, and processing stages.

## Python Pipeline and Analytics Scripts

Key scripts in the project include:

- `scripts/live_nav_fetch.py` for NAV source preparation
- `scripts/data_ingestion.py` for raw-to-processed data ingestion
- `scripts/fund_master_exploration.py` for fund master review
- `scripts/validate_amfi_codes.py` for code consistency checks
- `scripts/day2_pipeline.py` for processed data and database pipeline execution
- `scripts/performance_analytics.py` for return and benchmark analytics
- `scripts/advanced_analytics.py` for advanced analytics deliverables
- `scripts/recommender.py` for command-line fund recommendation

## Performance Analytics Deliverables

The project includes performance analytics outputs such as:

- `fund_scorecard.csv`
- `alpha_beta.csv`
- `benchmark_comparison_chart.png`
- `notebooks/04_performance_analytics.ipynb`

These support return analysis, benchmark comparison, and risk-adjusted performance interpretation.

## Advanced Analytics Deliverables

The advanced analytics module produces:

- `Advanced_Analytics.ipynb`
- `var_cvar_report.csv`
- `rolling_sharpe_chart.png`
- `recommender.py`

### Advanced Analytics Coverage

The advanced analytics work includes:

- historical daily return computation from NAV
- scheme-level 95% VaR and CVaR
- rolling 90-day Sharpe ratio for 5 key funds
- investor cohort analysis using first transaction year
- SIP continuity analysis using average gap between SIP transactions
- fund recommendation by risk appetite and Sharpe ratio
- HHI concentration analysis for equity funds
- markdown insight generation for notebook reporting

## Recommender Summary

The recommender module supports:

- `recommend_funds("Low")`
- `recommend_funds("Moderate")`
- `recommend_funds("High")`

Funds are mapped to matching risk grades and ranked by descending Sharpe ratio. The returned fields are:

- `scheme_name`
- `risk_grade`
- `sharpe_ratio`
- `return_3yr_pct`
- `aum_crore`

## SQL and Dashboard Assets

The project also includes:

- `sql/schema.sql`
- `sql/queries.sql`
- `dashboard/bluestock_mf_dashboard.pbix`
- `powerbi_assets/measures_dax.txt`
- `powerbi_assets/bluestock_theme.json`
- `powerbi_assets/powerbi_build_guide.md`

These assets extend the project from pure Python analysis into queryable data models and dashboard reporting.

## End-to-End Workflow

Recommended execution flow:

1. Run NAV and ingestion scripts.
2. Validate AMFI code consistency and data quality.
3. Execute the day 2 transformation pipeline.
4. Generate performance analytics outputs.
5. Generate advanced analytics outputs.
6. Use SQL and Power BI assets for reporting and visualization.

## Commands Used in the Project

Typical run order from the project root:

```powershell
python .\scripts\live_nav_fetch.py
python .\scripts\data_ingestion.py
python .\scripts\fund_master_exploration.py
python .\scripts\validate_amfi_codes.py
python .\scripts\day2_pipeline.py
python .\scripts\performance_analytics.py
python .\scripts\advanced_analytics.py
python .\scripts\recommender.py Moderate
```

## Project Status

The project is organized and executable as a full analytics workflow. It includes:

- validated processed datasets
- documented quality checks
- reusable Python analytics scripts
- notebook deliverables
- CSV and chart outputs
- recommendation logic
- SQL assets
- dashboard support files

## Conclusion

This mutual fund project is now documented in a single full-project report under `reports/`. The report brings together the ingestion stage, validation outputs, processed datasets, analytics modules, and final deliverables in a structured format suitable for submission, review, or handoff.
