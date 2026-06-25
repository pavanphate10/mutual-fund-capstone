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
