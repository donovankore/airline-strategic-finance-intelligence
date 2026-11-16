# Methodology

## Scope

The analysis compares American Airlines, Delta Air Lines, Southwest Airlines and United Airlines from 2019 through 2025. The financial period is the calendar year for all four carriers.

## Source hierarchy

1. SEC Company Facts API for financial statement values reported in Forms 10-K.
2. DOT/BTS T-100 carrier summaries for passengers, seats, departures and domestic/international traffic.
3. DOT/BTS average-fare-by-carrier data for reported domestic market fares through 2024.

Financial values are selected from annual 10-K facts with fiscal-period code `FY` and a duration between 300 and 400 days. When a company reports current and non-current debt separately, the model adds both balances.

## Metric definitions

- Operating margin: operating income divided by revenue.
- Operating cash flow margin: operating cash flow divided by revenue.
- Fuel cost as a percentage of revenue: reported aircraft fuel expense divided by revenue.
- Net debt: total debt less cash and restricted cash.
- Load factor: passengers divided by available seats from the T-100 carrier summary.
- International passenger share: inbound and outbound international passengers divided by total passengers.

## Known limitations

- Public data cannot establish route-level profitability. The project does not claim that it can.
- SEC tags and presentation choices differ by carrier. The extraction logic documents the fallback tags used.
- Cash includes restricted cash to maintain year-to-year availability across the peer group.
- The DOT fare dataset shows a break in reported market-passenger coverage beginning in the second half of 2025. Fare analysis is therefore limited to 2019–2024 pending confirmation of source methodology.
- The downside case is a sensitivity analysis, not company guidance.

