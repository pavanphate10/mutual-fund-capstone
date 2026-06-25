# Day 1 Data Quality Report

## Ingestion Summary

- Raw CSV files discovered in `data/raw/`: 7
- Day 1 target mentioned in the brief: 10
- Current gap: 3 dataset(s) are not present in the workspace
- Available files:
- `118632_nippon_large_cap.csv`
- `119092_axis_bluechip.csv`
- `119551_sbi_bluechip.csv`
- `120503_icici_bluechip.csv`
- `120841_kotak_bluechip.csv`
- `125497_hdfc_top_100_direct.csv`
- `nav_history.csv`

## Profiling Results

- All 7 available CSVs loaded successfully with pandas.
- No missing values were found in any of the currently available files.
- No duplicate rows were found in any of the currently available files.
- `nav_history.csv` contains 19,894 rows across 6 distinct scheme codes.
- NAV date coverage in `nav_history.csv` spans `2012-12-31` to `2026-06-23`.

## Anomalies Noted

- `fund_master.csv` is missing, so fund-house/category/sub-category/risk-grade exploration is currently blocked.
- AMFI code validation is blocked because `fund_master.csv` is not available.
- `120503_icici_bluechip.csv` contains one non-positive NAV record: `2013-04-07`, NAV `0.0`.
- Because `nav_history.csv` is the union of the fetched scheme files, that same zero-NAV record also appears there.
- The latest live pull from `mfapi.in` shows major requested-label vs API-name mismatches:
- `125497`: requested `HDFC Top 100 Direct`, API returned `SBI Small Cap Fund - Direct Plan - Growth`
- `119551`: requested `SBI Bluechip`, API returned `Aditya Birla Sun Life Banking & PSU Debt Fund - DIRECT - IDCW`
- `120503`: requested `ICICI Bluechip`, API returned `Axis ELSS Tax Saver Fund - Direct Plan - Growth Option`
- `119092`: requested `Axis Bluechip`, API returned `HDFC Money Market Fund - Growth Option - Direct Plan`
- `120841`: requested `Kotak Bluechip`, API returned `quant Mid Cap Fund - Growth Option - Direct Plan`
- `118632` is the only code that appears directionally consistent with the requested scheme family, though the full API name is more specific than the requested label.
- Conclusion: the supplied scheme-code-to-name mapping should be rechecked against AMFI or fresh mfapi metadata before downstream analysis.

## AMFI Validation Summary

- Validation blocked: `fund_master.csv` not found at `data/raw/fund_master.csv`.
- Current implication: coverage of all fund master AMFI codes inside `nav_history.csv` cannot yet be confirmed.

## Next Actions

- Add the missing source datasets, especially `fund_master.csv`.
- Re-run `python fund_master_exploration.py` after `fund_master.csv` is added.
- Re-run `python validate_amfi_codes.py` to confirm every fund master code exists in `nav_history.csv`.
- Re-fetch NAV history with the updated `live_nav_fetch.py` so API-reported scheme names are stored alongside requested labels.
- Correct the scheme-code list before building any fund-comparison dashboard or report.
