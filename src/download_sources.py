#!/usr/bin/env python3
"""Download the official public source files used by the project."""

from __future__ import annotations

import os
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SOURCES = {
    "t100_carrier.csv": "https://data.transportation.gov/api/v3/views/q4tb-tbff/export.csv?accessType=DOWNLOAD",
    "average_fare_by_carrier.csv": "https://data.transportation.gov/api/v3/views/gjp5-nh2u/export.csv?accessType=DOWNLOAD",
    "sec_DAL_companyfacts.json": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000027904.json",
    "sec_UAL_companyfacts.json": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000100517.json",
    "sec_AAL_companyfacts.json": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000006201.json",
    "sec_LUV_companyfacts.json": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000092380.json",
}


def main() -> None:
    user_agent = os.environ.get(
        "SEC_USER_AGENT",
        "airline-strategic-finance research project contact@example.com",
    )
    RAW.mkdir(parents=True, exist_ok=True)
    for filename, url in SOURCES.items():
        response = requests.get(url, headers={"User-Agent": user_agent}, timeout=180)
        response.raise_for_status()
        (RAW / filename).write_bytes(response.content)
        print(f"Downloaded {filename}: {len(response.content):,} bytes")


if __name__ == "__main__":
    main()

