"""
Fetch ACS 5-year estimates for Madison, WI (FIPS 55025 / place 48000)
and Austin, TX (FIPS 48453 / place 05000) for comparison.

Requires: CENSUS_API_KEY env var  (get free key at api.census.gov/data/key_signup.html)

Variables pulled:
  B25064_001E  - Median gross rent
  B19013_001E  - Median household income
  B01003_001E  - Total population
  B25070_007E..B25070_010E - Rent burden 30-49% and 50%+ (severe)
  B25003_001E  - Total occupied housing units
  B25003_002E  - Owner-occupied units
"""

import os
import time
import requests
import pandas as pd

API_KEY = os.environ.get("CENSUS_API_KEY", "")
BASE = "https://api.census.gov/data"

# (name, state_fips, place_fips)
PLACES = [
    ("Madison, WI",  "55", "48000"),
    ("Austin, TX",   "48", "05000"),
]

VARIABLES = {
    "B25064_001E": "median_gross_rent",
    "B19013_001E": "median_hh_income",
    "B01003_001E": "population",
    "B25070_007E": "rent_burden_30_34pct",
    "B25070_008E": "rent_burden_35_39pct",
    "B25070_009E": "rent_burden_40_49pct",
    "B25070_010E": "rent_burden_50plus_pct",
    "B25003_001E": "total_occupied_units",
    "B25003_002E": "owner_occupied_units",
}

YEARS = list(range(2015, 2024))  # ACS 5-year goes to 2023 (vintage 2023)


def fetch_year(year: int, state: str, place: str) -> dict:
    vars_str = ",".join(VARIABLES.keys())
    url = (
        f"{BASE}/{year}/acs/acs5"
        f"?get=NAME,{vars_str}"
        f"&for=place:{place}&in=state:{state}"
        f"&key={API_KEY}"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    rows = r.json()
    header, data = rows[0], rows[1]
    row = dict(zip(header, data))
    return {VARIABLES.get(k, k): v for k, v in row.items()}


def run():
    records = []
    for name, state, place in PLACES:
        for year in YEARS:
            try:
                row = fetch_year(year, state, place)
                row["city"] = name
                row["year"] = year
                records.append(row)
                time.sleep(0.25)  # gentle on the API
            except Exception as e:
                print(f"  WARN {name} {year}: {e}")

    df = pd.DataFrame(records)

    # Derive rent burden share (% of renter households spending 30%+ of income on rent)
    burden_cols = [
        "rent_burden_30_34pct", "rent_burden_35_39pct",
        "rent_burden_40_49pct", "rent_burden_50plus_pct",
    ]
    for col in burden_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["renter_occupied_units"] = (
        pd.to_numeric(df["total_occupied_units"], errors="coerce")
        - pd.to_numeric(df["owner_occupied_units"], errors="coerce")
    )
    df["cost_burdened_count"] = df[burden_cols].sum(axis=1)
    df["cost_burden_rate"] = df["cost_burdened_count"] / df["renter_occupied_units"]

    out = "data/acs_rent_income.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")


if __name__ == "__main__":
    run()
