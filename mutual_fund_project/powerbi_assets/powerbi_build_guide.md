# Power BI Build Guide

This package prepares the model and design spec for the Bluestock Mutual Fund dashboard. A real `.pbix`, PDF export, and page screenshots still need to be created inside Power BI Desktop because that requires GUI interaction.

## What To Load

The cleaned layer contains **10** CSV files, not 8. Your page requirements use **9** of them.

Load these 9 required tables:

1. `data/processed/fund_master.csv`
2. `data/processed/nav_history.csv`
3. `data/processed/scheme_performance.csv`
4. `data/processed/benchmark_indices.csv`
5. `data/processed/aum_by_fund_house.csv`
6. `data/processed/monthly_sip_inflows.csv`
7. `data/processed/category_inflows.csv`
8. `data/processed/industry_folio_count.csv`
9. `data/processed/investor_transactions.csv`

Optional table:

1. `data/processed/portfolio_holdings.csv`

If you prefer a database connection, use SQLite and point Power BI to:

- `d:\Mutual_fund\mutual_fund_project\bluestock_mf.db`

## Relationships

Create these relationships:

1. `fund_master[amfi_code]` 1-to-many `nav_history[amfi_code]`
2. `fund_master[amfi_code]` 1-to-many `scheme_performance[amfi_code]`
3. `fund_master[amfi_code]` 1-to-many `investor_transactions[amfi_code]`
4. `fund_master[amfi_code]` 1-to-many `portfolio_holdings[amfi_code]` if loaded

For dates, create a dedicated date table first, then relate it to fact tables:

1. `Date[Date]` 1-to-many `nav_history[date]`
2. `Date[Date]` 1-to-many `benchmark_indices[date]`
3. `Date[Date]` 1-to-many `aum_by_fund_house[date]`
4. `Date[Date]` 1-to-many `investor_transactions[transaction_date]`

Create a month-start date column in Power Query for the month-based tables and relate those to `Date[MonthStart]`:

1. `monthly_sip_inflows[month]` -> `month_start`
2. `category_inflows[month]` -> `month_start`
3. `industry_folio_count[month]` -> `month_start`

Use single-direction filtering from dimension to fact.

## Date Table DAX

```DAX
Date =
ADDCOLUMNS (
    CALENDAR ( DATE ( 2022, 1, 1 ), DATE ( 2026, 12, 31 ) ),
    "Year", YEAR ( [Date] ),
    "MonthNo", MONTH ( [Date] ),
    "Month", FORMAT ( [Date], "MMM" ),
    "YearMonth", FORMAT ( [Date], "YYYY-MM" ),
    "MonthStart", DATE ( YEAR ( [Date] ), MONTH ( [Date] ), 1 ),
    "Quarter", "Q" & FORMAT ( [Date], "Q" ),
    "FY", "FY" & IF ( MONTH ( [Date] ) >= 4, YEAR ( [Date] ) + 1, YEAR ( [Date] ) )
)
```

## Power Query Fixes

Apply these transformations during import:

1. Set all `date` and `transaction_date` columns to `Date`
2. Convert `month` text columns like `2025-03` into `month_start` using the first day of month
3. Ensure INR and percentage fields are numeric
4. Hide technical columns like `nav_quality_flag` and `anomaly_flag` from report view unless needed for QA

## Measures

Create the DAX measures from:

- [measures_dax.txt](./measures_dax.txt)

## Theme

Import this report theme:

- [bluestock_theme.json](./bluestock_theme.json)

No Bluestock logo asset exists in the repo right now, so add the official logo file manually in Power BI if you have it.

## Page Build Spec

### Page 1: Industry Overview

Visuals:

1. KPI card: `Latest AUM Cr`
2. KPI card: `Latest SIP Inflow Cr`
3. KPI card: `Latest Total Folios Cr`
4. KPI card: `Total Schemes`
5. Line chart: `Date[Date]` vs `SUM(aum_by_fund_house[aum_crore])`
6. Bar chart: `fund_house` vs `Latest AUM Cr`

Notes:

1. Format the KPI display units to show crore/lakh crore labels manually in titles or subtitles
2. The exact values in your prompt should be used only if they match the latest dataset after import

### Page 2: Fund Performance

Visuals:

1. Scatter plot:
   X = `scheme_performance[return_3yr_pct]`
   Y = `scheme_performance[std_dev_ann_pct]`
   Size = `scheme_performance[aum_crore]`
   Details = `scheme_performance[scheme_name]`
2. Sortable table using `fund_scorecard.csv`
3. Line chart: `nav_history[date]` vs `nav_history[nav]`
4. Overlay benchmark line from `benchmark_indices[close_value]`
5. Slicers: `fund_house`, `category`, `plan`

Recommended:

1. Import `fund_scorecard.csv` from the project root as an additional table
2. Import `alpha_beta.csv` if you want regression metrics visible in detail views

### Page 3: Investor Analytics

Visuals:

1. Bar chart: `state` vs `SUM(amount_inr)`
2. Donut chart: `transaction_type` vs `SUM(amount_inr)`
3. Bar chart: `age_group` vs `Avg SIP Amount`
4. Line chart: `transaction_date` vs `SUM(amount_inr)`
5. Slicers: `state`, `age_group`, `city_tier`

### Page 4: SIP & Market Trends

Visuals:

1. Combo chart:
   Column = `monthly_sip_inflows[sip_inflow_crore]`
   Line = `Nifty 50 Close`
   Axis = `Date[MonthStart]`
2. Heatmap-style matrix:
   Rows = `category`
   Columns = `Date[FY]` or `Date[YearMonth]`
   Values = `Category Net Inflow Cr`
   Conditional formatting = background color scale
3. Bar chart: top 5 categories by `Category Net Inflow Cr` filtered to FY25

## Drill-Through

Create a detail page named `Fund NAV Detail`.

Add these drill-through fields:

1. `scheme_name`
2. `amfi_code`

Suggested visuals on drill-through page:

1. NAV trend
2. Benchmark trend
3. Fund score
4. Alpha, beta, Sharpe, Sortino
5. Drawdown window dates

## Tooltips

Add report page tooltips or standard tooltips to all visuals. Best tooltip fields:

1. `scheme_name`
2. `fund_house`
3. `category`
4. `return_3yr_pct`
5. `std_dev_ann_pct`
6. `aum_crore`
7. `alpha`
8. `beta`

## Export Steps

After the report is built in Power BI Desktop:

1. Save as `bluestock_mf_dashboard.pbix`
2. Export to PDF as `Dashboard.pdf`
3. Export each page as PNG using Power BI Desktop screenshot workflow or Power BI Service export

## Limits From This Environment

I could not produce these final binary/UI deliverables here:

1. `bluestock_mf_dashboard.pbix`
2. `Dashboard.pdf`
3. Real page screenshots exported from Power BI

Those require interactive Power BI Desktop operations.
