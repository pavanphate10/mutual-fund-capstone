# Day 2 Load Verification

| Dataset | Source Rows | Cleaned Rows | SQLite Rows | Notes |
|---|---:|---:|---:|---|
| fund_master | 40 | 40 | 40 | No material data quality issues detected during standard cleaning. |
| nav_history | 46000 | 46000 | 46000 | NAV source had no duplicates, no invalid dates, and no non-positive NAV values. Forward fill did not materially change rows because the source already had populated NAV values. |
| aum_by_fund_house | 90 | 90 | 90 | No material data quality issues detected during standard cleaning. |
| monthly_sip_inflows | 48 | 48 | 48 | No material data quality issues detected during standard cleaning. |
| category_inflows | 144 | 144 | 144 | No material data quality issues detected during standard cleaning. |
| industry_folio_count | 21 | 21 | 21 | No material data quality issues detected during standard cleaning. |
| scheme_performance | 40 | 40 | 40 | All return and risk fields are numeric, and all expense ratios fall within 0.1% to 2.5%. |
| investor_transactions | 32778 | 32778 | 32778 | Transaction types were standardized, dates normalized, and all source amounts/KYC values passed validation. |
| portfolio_holdings | 322 | 322 | 322 | No material data quality issues detected during standard cleaning. |
| benchmark_indices | 8050 | 8050 | 8050 | No material data quality issues detected during standard cleaning. |
