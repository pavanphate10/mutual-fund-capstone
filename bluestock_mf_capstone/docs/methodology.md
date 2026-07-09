# Data Dictionary

## fund_master

- Source: Google Drive / 01_fund_master.csv
- Cleaned output: `data/processed/fund_master.csv`
- Row count: 40

| Column | Data Type | Business Definition |
|---|---|---|
| amfi_code | int64 | AMFI-issued scheme identifier for a mutual fund plan. |
| fund_house | object | Asset management company managing the scheme. |
| scheme_name | object | Full scheme or plan name used for investor-facing reporting. |
| category | object | Broad mutual fund category such as Equity or Large Cap. |
| sub_category | object | More specific style bucket inside a category. |
| plan | object | Plan type such as Direct or Regular. |
| launch_date | object | Scheme inception date. |
| benchmark | object | Reference index used to compare scheme performance. |
| expense_ratio_pct | float64 | Annual fund expense ratio expressed as a percent. |
| exit_load_pct | float64 | Redemption fee charged within the applicable holding period. |
| min_sip_amount | int64 | Minimum SIP ticket size in INR. |
| min_lumpsum_amount | int64 | Minimum one-time investment amount in INR. |
| fund_manager | object | Primary named fund manager. |
| risk_category | object | Risk profile label from the source file. |
| sebi_category_code | object | Internal bucket or category code aligned to SEBI classification. |

## nav_history

- Source: Google Drive / 02_nav_history.csv
- Cleaned output: `data/processed/nav_history.csv`
- Row count: 46000

| Column | Data Type | Business Definition |
|---|---|---|
| amfi_code | int64 | AMFI-issued scheme identifier for a mutual fund plan. |
| date | object | Observation date for time-series data. |
| nav | float64 | Net asset value per unit on the observation date. |
| nav_quality_flag | object | Pipeline quality marker for the cleaned NAV row. |

## aum_by_fund_house

- Source: Google Drive / 03_aum_by_fund_house.csv
- Cleaned output: `data/processed/aum_by_fund_house.csv`
- Row count: 90

| Column | Data Type | Business Definition |
|---|---|---|
| date | object | Observation date for time-series data. |
| fund_house | object | Asset management company managing the scheme. |
| aum_lakh_crore | float64 | Assets under management expressed in lakh crore INR. |
| aum_crore | int64 | Assets under management expressed in crore INR. |
| num_schemes | int64 | Count of schemes managed by the fund house in the period. |

## monthly_sip_inflows

- Source: Google Drive / 04_monthly_sip_inflows.csv
- Cleaned output: `data/processed/monthly_sip_inflows.csv`
- Row count: 48

| Column | Data Type | Business Definition |
|---|---|---|
| month | object | Monthly period stored as YYYY-MM. |
| sip_inflow_crore | int64 | Monthly SIP inflow amount in crore INR. |
| active_sip_accounts_crore | float64 | Active SIP account count in crore accounts. |
| new_sip_accounts_lakh | float64 | New SIP accounts opened in the month, in lakh accounts. |
| sip_aum_lakh_crore | float64 | SIP-linked AUM in lakh crore INR. |
| yoy_growth_pct | float64 | Year-over-year growth percentage. |

## category_inflows

- Source: Google Drive / 05_category_inflows.csv
- Cleaned output: `data/processed/category_inflows.csv`
- Row count: 144

| Column | Data Type | Business Definition |
|---|---|---|
| month | object | Monthly period stored as YYYY-MM. |
| category | object | Broad mutual fund category such as Equity or Large Cap. |
| net_inflow_crore | float64 | Net category money flow for the month in crore INR. |

## industry_folio_count

- Source: Google Drive / 06_industry_folio_count.csv
- Cleaned output: `data/processed/industry_folio_count.csv`
- Row count: 21

| Column | Data Type | Business Definition |
|---|---|---|
| month | object | Monthly period stored as YYYY-MM. |
| total_folios_crore | float64 | Total mutual fund folios in crore units. |
| equity_folios_crore | float64 | Equity folios in crore units. |
| debt_folios_crore | float64 | Debt folios in crore units. |
| hybrid_folios_crore | float64 | Hybrid folios in crore units. |
| others_folios_crore | float64 | Other folios in crore units. |

## scheme_performance

- Source: Google Drive / 07_scheme_performance.csv
- Cleaned output: `data/processed/scheme_performance.csv`
- Row count: 40

| Column | Data Type | Business Definition |
|---|---|---|
| amfi_code | int64 | AMFI-issued scheme identifier for a mutual fund plan. |
| scheme_name | object | Full scheme or plan name used for investor-facing reporting. |
| fund_house | object | Asset management company managing the scheme. |
| category | object | Broad mutual fund category such as Equity or Large Cap. |
| plan | object | Plan type such as Direct or Regular. |
| return_1yr_pct | float64 | Trailing 1-year return percentage. |
| return_3yr_pct | float64 | Trailing 3-year return percentage. |
| return_5yr_pct | float64 | Trailing 5-year return percentage. |
| benchmark_3yr_pct | float64 | Trailing 3-year benchmark return percentage. |
| alpha | float64 | Alpha versus benchmark or category. |
| beta | float64 | Beta versus benchmark or market. |
| sharpe_ratio | float64 | Sharpe ratio for risk-adjusted return. |
| sortino_ratio | float64 | Sortino ratio for downside-adjusted return. |
| std_dev_ann_pct | float64 | Annualized standard deviation percentage. |
| max_drawdown_pct | float64 | Maximum historical drawdown percentage. |
| aum_crore | int64 | Assets under management expressed in crore INR. |
| expense_ratio_pct | float64 | Annual fund expense ratio expressed as a percent. |
| morningstar_rating | int64 | Morningstar-style numeric rating from the source file. |
| risk_grade | object | Performance/risk table risk label. |
| anomaly_flag | object | Pipeline anomaly flag for numeric validation or expense-ratio checks. |

## investor_transactions

- Source: Google Drive / 08_investor_transactions.csv
- Cleaned output: `data/processed/investor_transactions.csv`
- Row count: 32778

| Column | Data Type | Business Definition |
|---|---|---|
| investor_id | object | Synthetic investor identifier. |
| transaction_date | object | Date of purchase, SIP, or redemption activity. |
| amfi_code | int64 | AMFI-issued scheme identifier for a mutual fund plan. |
| transaction_type | object | Standardized transaction bucket: SIP, Lumpsum, or Redemption. |
| amount_inr | int64 | Transaction amount in INR. |
| state | object | Investor state. |
| city | object | Investor city. |
| city_tier | object | Investor city classification such as T30 or B30. |
| age_group | object | Investor age bucket. |
| gender | object | Investor gender label. |
| annual_income_lakh | float64 | Investor annual income in lakh INR. |
| payment_mode | object | Channel used to fund the transaction. |
| kyc_status | object | KYC completion state. |

## portfolio_holdings

- Source: Google Drive / 09_portfolio_holdings.csv
- Cleaned output: `data/processed/portfolio_holdings.csv`
- Row count: 322

| Column | Data Type | Business Definition |
|---|---|---|
| amfi_code | int64 | AMFI-issued scheme identifier for a mutual fund plan. |
| stock_symbol | object | Ticker or short symbol for a portfolio constituent. |
| stock_name | object | Name of the portfolio constituent. |
| sector | object | Sector classification for a portfolio constituent. |
| weight_pct | float64 | Portfolio weight of the security as a percent. |
| market_value_cr | float64 | Holding market value in crore INR. |
| current_price_inr | float64 | Security market price in INR. |
| portfolio_date | object | Portfolio disclosure date. |

## benchmark_indices

- Source: Google Drive / 10_benchmark_indices.csv
- Cleaned output: `data/processed/benchmark_indices.csv`
- Row count: 8050

| Column | Data Type | Business Definition |
|---|---|---|
| date | object | Observation date for time-series data. |
| index_name | object | Benchmark or market index name. |
| close_value | float64 | Index closing value on the date. |
