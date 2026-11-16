#!/usr/bin/env python3
"""Build the analytical dataset from official DOT/BTS and SEC files.

The script expects the source files in ``data/raw``. Use ``download_sources.py``
to refresh them. Values are not imputed. Missing observations remain missing.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

CARRIERS = {
    "DAL": {"bts": "Delta Air Lines Inc.", "fare": "DL", "name": "Delta Air Lines"},
    "UAL": {"bts": "United Air Lines Inc.", "fare": "UA", "name": "United Airlines"},
    "AAL": {"bts": "American Airlines Inc.", "fare": "AA", "name": "American Airlines"},
    "LUV": {"bts": "Southwest Airlines Co.", "fare": "WN", "name": "Southwest Airlines"},
}

YEARS = list(range(2019, 2026))


def number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.astype(str).str.replace(",", "", regex=False), errors="coerce")


def sec_entries(document: dict, tag: str) -> list[dict]:
    fact = document.get("facts", {}).get("us-gaap", {}).get(tag, {})
    return fact.get("units", {}).get("USD", [])


def annual_duration(document: dict, tags: list[str], year: int) -> float | None:
    for tag in tags:
        candidates = []
        for item in sec_entries(document, tag):
            if item.get("form") != "10-K" or item.get("fp") != "FY":
                continue
            if item.get("fy") != year or not item.get("end", "").startswith(str(year)):
                continue
            if "start" not in item:
                continue
            days = (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days
            if 300 <= days <= 400:
                candidates.append(item)
        if candidates:
            candidates.sort(key=lambda x: x.get("filed", ""))
            return float(candidates[-1]["val"])
    return None


def annual_instant(document: dict, tags: list[str], year: int) -> float | None:
    for tag in tags:
        candidates = [
            item
            for item in sec_entries(document, tag)
            if item.get("form") == "10-K"
            and item.get("fp") == "FY"
            and item.get("fy") == year
            and item.get("end", "").startswith(str(year))
        ]
        if candidates:
            candidates.sort(key=lambda x: x.get("filed", ""))
            return float(candidates[-1]["val"])
    return None


def total_debt(document: dict, year: int) -> float | None:
    current = annual_instant(document, ["LongTermDebtCurrent"], year)
    noncurrent = annual_instant(document, ["LongTermDebtNoncurrent"], year)
    if current is not None and noncurrent is not None:
        return current + noncurrent
    return annual_instant(
        document,
        ["LongTermDebtAndCapitalLeaseObligations", "LongTermDebt", "LongTermDebtNoncurrent"],
        year,
    )


def build_sec_actuals() -> pd.DataFrame:
    rows = []
    for ticker, metadata in CARRIERS.items():
        document = json.loads((RAW / f"sec_{ticker}_companyfacts.json").read_text())
        for year in YEARS:
            revenue = annual_duration(
                document,
                ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet"],
                year,
            )
            operating_income = annual_duration(document, ["OperatingIncomeLoss"], year)
            net_income = annual_duration(document, ["NetIncomeLoss"], year)
            operating_cash_flow = annual_duration(
                document,
                ["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
                year,
            )
            fuel_cost = annual_duration(document, ["FuelCosts"], year)
            cash = annual_instant(
                document,
                [
                    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
                    "CashAndCashEquivalentsAtCarryingValue",
                ],
                year,
            )
            debt = total_debt(document, year)
            rows.append(
                {
                    "ticker": ticker,
                    "carrier": metadata["name"],
                    "year": year,
                    "revenue_usd": revenue,
                    "operating_income_usd": operating_income,
                    "net_income_usd": net_income,
                    "operating_cash_flow_usd": operating_cash_flow,
                    "fuel_cost_usd": fuel_cost,
                    "cash_and_restricted_cash_usd": cash,
                    "total_debt_usd": debt,
                }
            )
    frame = pd.DataFrame(rows)
    frame["operating_margin"] = frame["operating_income_usd"] / frame["revenue_usd"]
    frame["cfo_margin"] = frame["operating_cash_flow_usd"] / frame["revenue_usd"]
    frame["fuel_cost_pct_revenue"] = frame["fuel_cost_usd"] / frame["revenue_usd"]
    frame["net_debt_usd"] = frame["total_debt_usd"] - frame["cash_and_restricted_cash_usd"]
    return frame


def build_operations() -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(RAW / "t100_carrier.csv", low_memory=False)
    reverse = {meta["bts"]: ticker for ticker, meta in CARRIERS.items()}
    source = source[source["Carrier"].isin(reverse)].copy()
    source["ticker"] = source["Carrier"].map(reverse)
    source["date"] = pd.to_datetime(source["Date"], format="%Y %b %d %I:%M:%S %p")
    source["year"] = source["date"].dt.year
    source = source[source["year"].isin(YEARS)].copy()

    numeric_columns = [
        "Total Departures",
        "Total Passengers",
        "Total Seats",
        "Domestic Passengers",
        "Outbound International Passengers",
        "Inbound International Passengers",
    ]
    for column in numeric_columns:
        source[column] = number(source[column])

    monthly = source[
        ["ticker", "Carrier", "date", "year", *numeric_columns]
    ].rename(
        columns={
            "Carrier": "carrier_source_name",
            "Total Departures": "departures",
            "Total Passengers": "passengers",
            "Total Seats": "seats",
            "Domestic Passengers": "domestic_passengers",
            "Outbound International Passengers": "outbound_international_passengers",
            "Inbound International Passengers": "inbound_international_passengers",
        }
    )
    monthly["load_factor"] = monthly["passengers"] / monthly["seats"]
    monthly["international_passengers"] = (
        monthly["outbound_international_passengers"] + monthly["inbound_international_passengers"]
    )

    annual = (
        monthly.groupby(["ticker", "year"], as_index=False)[
            ["departures", "passengers", "seats", "domestic_passengers", "international_passengers"]
        ]
        .sum(min_count=1)
    )
    annual["load_factor"] = annual["passengers"] / annual["seats"]
    annual["passengers_per_departure"] = annual["passengers"] / annual["departures"]
    annual["international_passenger_share"] = annual["international_passengers"] / annual["passengers"]
    return monthly, annual


def build_fares() -> tuple[pd.DataFrame, pd.DataFrame]:
    source = pd.read_csv(RAW / "average_fare_by_carrier.csv", low_memory=False)
    reverse = {meta["fare"]: ticker for ticker, meta in CARRIERS.items()}
    source = source[source["RpCarrier"].isin(reverse)].copy()
    source["ticker"] = source["RpCarrier"].map(reverse)
    source["quarter_date"] = pd.to_datetime(source["Year_Quarter"], format="%Y %b %d %I:%M:%S %p")
    source["year"] = source["quarter_date"].dt.year
    source = source[source["year"].between(2019, 2024)].copy()

    mapping = {
        "Average Market Fare (Current $)": "average_market_fare_usd",
        "Market Passengers": "market_passengers",
        "Market Revenue (Current $)": "market_revenue_usd",
        "Average Market Yield (Current $/sm)": "average_yield_usd_per_mile",
        "Average Market Miles Flown (sm)": "average_market_miles",
    }
    for source_column in mapping:
        source[source_column] = number(source[source_column])
    quarterly = source[["ticker", "quarter_date", "year", *mapping]].rename(columns=mapping)

    annual = (
        quarterly.groupby(["ticker", "year"], as_index=False)
        .agg(
            average_market_fare_usd=("average_market_fare_usd", "mean"),
            average_yield_usd_per_mile=("average_yield_usd_per_mile", "mean"),
            average_market_miles=("average_market_miles", "mean"),
        )
    )
    return quarterly, annual


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    finance = build_sec_actuals()
    operations_monthly, operations_annual = build_operations()
    fares_quarterly, fares_annual = build_fares()

    annual = finance.merge(operations_annual, on=["ticker", "year"], how="left")
    annual = annual.merge(fares_annual, on=["ticker", "year"], how="left")
    annual = annual.sort_values(["year", "ticker"]).reset_index(drop=True)

    annual.to_csv(PROCESSED / "carrier_annual_performance.csv", index=False)
    operations_monthly.to_csv(PROCESSED / "carrier_monthly_operations.csv", index=False)
    fares_quarterly.to_csv(PROCESSED / "carrier_quarterly_fares.csv", index=False)

    database = ROOT / "data" / "airline_intelligence.sqlite"
    database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(database) as connection:
        annual.to_sql("carrier_annual_performance", connection, if_exists="replace", index=False)
        operations_monthly.to_sql("carrier_monthly_operations", connection, if_exists="replace", index=False)
        fares_quarterly.to_sql("carrier_quarterly_fares", connection, if_exists="replace", index=False)
        connection.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_annual_ticker_year
            ON carrier_annual_performance(ticker, year);
            CREATE INDEX IF NOT EXISTS idx_monthly_ticker_date
            ON carrier_monthly_operations(ticker, date);
            """
        )

    checks = {
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "annual_rows": int(len(annual)),
        "expected_annual_rows": len(CARRIERS) * len(YEARS),
        "duplicate_ticker_year": int(annual.duplicated(["ticker", "year"]).sum()),
        "missing_revenue": int(annual["revenue_usd"].isna().sum()),
        "missing_operating_income": int(annual["operating_income_usd"].isna().sum()),
        "invalid_load_factor": int(((annual["load_factor"] < 0) | (annual["load_factor"] > 1)).sum()),
        "monthly_rows": int(len(operations_monthly)),
        "fare_2025_excluded": True,
        "fare_exclusion_reason": "A coverage break appears in reported market-passenger counts beginning in 2025 Q3; fare analysis is limited to 2019-2024 pending source review.",
    }
    (PROCESSED / "data_quality_report.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()

