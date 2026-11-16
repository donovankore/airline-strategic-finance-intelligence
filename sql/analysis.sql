-- U.S. Airline Strategic Finance & Operations Intelligence
-- All amounts originate from SEC XBRL facts; operational records originate from DOT/BTS.

-- 1. Latest-year peer comparison
SELECT
    ticker,
    carrier,
    year,
    ROUND(revenue_usd / 1000000000.0, 1) AS revenue_usd_bn,
    ROUND(operating_margin * 100.0, 1) AS operating_margin_pct,
    ROUND(cfo_margin * 100.0, 1) AS cfo_margin_pct,
    ROUND(fuel_cost_pct_revenue * 100.0, 1) AS fuel_cost_pct_revenue,
    ROUND(net_debt_usd / 1000000000.0, 1) AS net_debt_usd_bn,
    ROUND(load_factor * 100.0, 1) AS load_factor_pct
FROM carrier_annual_performance
WHERE year = 2025
ORDER BY operating_margin DESC;

-- 2. Recovery versus 2019
SELECT
    current.ticker,
    ROUND((current.revenue_usd / base.revenue_usd - 1.0) * 100.0, 1) AS revenue_growth_vs_2019_pct,
    ROUND((current.operating_margin - base.operating_margin) * 10000.0, 0) AS operating_margin_change_bps,
    ROUND((current.load_factor - base.load_factor) * 10000.0, 0) AS load_factor_change_bps
FROM carrier_annual_performance AS current
JOIN carrier_annual_performance AS base
  ON current.ticker = base.ticker
 AND base.year = 2019
WHERE current.year = 2025
ORDER BY revenue_growth_vs_2019_pct DESC;

-- 3. Monthly capacity utilization
SELECT
    ticker,
    substr(date, 1, 7) AS month,
    SUM(passengers) AS passengers,
    SUM(seats) AS seats,
    ROUND(100.0 * SUM(passengers) / NULLIF(SUM(seats), 0), 1) AS load_factor_pct
FROM carrier_monthly_operations
WHERE date >= '2024-01-01'
GROUP BY ticker, substr(date, 1, 7)
ORDER BY month, ticker;

-- 4. Fuel-cost sensitivity using 2025 actuals
WITH assumptions AS (
    SELECT 0.15 AS fuel_price_increase
)
SELECT
    p.ticker,
    ROUND(p.operating_income_usd / 1000000000.0, 2) AS actual_operating_income_usd_bn,
    ROUND(p.fuel_cost_usd * a.fuel_price_increase / 1000000000.0, 2) AS incremental_fuel_cost_usd_bn,
    ROUND((p.operating_income_usd - p.fuel_cost_usd * a.fuel_price_increase) / 1000000000.0, 2)
        AS stressed_operating_income_usd_bn,
    ROUND(100.0 * (p.operating_income_usd - p.fuel_cost_usd * a.fuel_price_increase) / p.revenue_usd, 1)
        AS stressed_operating_margin_pct
FROM carrier_annual_performance AS p
CROSS JOIN assumptions AS a
WHERE p.year = 2025
ORDER BY stressed_operating_margin_pct DESC;

-- 5. Source coverage and missing-data review
SELECT
    ticker,
    COUNT(*) AS annual_records,
    SUM(CASE WHEN revenue_usd IS NULL THEN 1 ELSE 0 END) AS missing_revenue,
    SUM(CASE WHEN operating_income_usd IS NULL THEN 1 ELSE 0 END) AS missing_operating_income,
    SUM(CASE WHEN load_factor IS NULL THEN 1 ELSE 0 END) AS missing_load_factor,
    MIN(year) AS first_year,
    MAX(year) AS last_year
FROM carrier_annual_performance
GROUP BY ticker
ORDER BY ticker;

