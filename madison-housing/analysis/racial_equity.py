"""
Cost burden by race — Madison vs. Austin.

ACS tables used:
  B25106  - Tenure by housing costs as % of household income by race
  Specifically: B25106B (Black/AA), B25106H (White non-Hispanic),
                B25106I (Hispanic), B25106D (Asian)

  For each group:
    _002E = Owner-occupied (total)
    _006E = Renter-occupied 30-34%
    _008E = Renter-occupied 35-39%
    _010E = Renter-occupied 40-49%
    _012E = Renter-occupied 50%+
    _003E = Renter-occupied total
"""

import os
import time
import requests
import pandas as pd

API_KEY = os.environ.get("CENSUS_API_KEY", "")
BASE = "https://api.census.gov/data"

PLACES = [
    ("Madison, WI",  "55", "48000"),
    ("Austin, TX",   "48", "05000"),
]

RACE_TABLES = {
    "White_NonHisp": "B25106H",
    "Black_AA":       "B25106B",
    "Hispanic":       "B25106I",
    "Asian":          "B25106D",
}

# Suffixes within each race table
SUFFIXES = {
    "renter_total":       "003E",
    "burden_30_34":       "006E",
    "burden_35_39":       "008E",
    "burden_40_49":       "010E",
    "burden_50plus":      "012E",
}

YEARS = list(range(2015, 2024))


def build_var_list() -> tuple[list[str], dict[str, str]]:
    """Returns (variable_list, var→readable_name mapping)."""
    vars_out, name_map = [], {}
    for race, table in RACE_TABLES.items():
        for label, suffix in SUFFIXES.items():
            var = f"{table}_{suffix}"
            vars_out.append(var)
            name_map[var] = f"{race}__{label}"
    return vars_out, name_map


def fetch_year(year: int, state: str, place: str, var_list: list[str]) -> dict:
    chunk_size = 45  # Census API limit per request
    row = {}
    for i in range(0, len(var_list), chunk_size):
        chunk = var_list[i : i + chunk_size]
        url = (
            f"{BASE}/{year}/acs/acs5"
            f"?get={','.join(chunk)}"
            f"&for=place:{place}&in=state:{state}"
            f"&key={API_KEY}"
        )
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        header, data = r.json()[0], r.json()[1]
        row.update(dict(zip(header, data)))
        time.sleep(0.2)
    return row


def run():
    var_list, name_map = build_var_list()
    records = []

    for city_name, state, place in PLACES:
        for year in YEARS:
            try:
                raw = fetch_year(year, state, place, var_list)
                row = {"city": city_name, "year": year}
                for var, readable in name_map.items():
                    row[readable] = pd.to_numeric(raw.get(var), errors="coerce")
                records.append(row)
                time.sleep(0.25)
            except Exception as e:
                print(f"  WARN {city_name} {year}: {e}")

    df = pd.DataFrame(records)

    # Derive cost burden rate per race group
    for race in RACE_TABLES:
        burden_cols = [f"{race}__burden_{s}" for s in ["30_34", "35_39", "40_49", "50plus"]]
        df[f"{race}__burdened"] = df[burden_cols].sum(axis=1)
        df[f"{race}__burden_rate"] = df[f"{race}__burdened"] / df[f"{race}__renter_total"]

    out = "data/racial_equity.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")

    # Print summary
    rate_cols = [c for c in df.columns if c.endswith("__burden_rate")]
    print("\n--- Cost burden rates by race (most recent year) ---")
    latest = df.groupby("city").last().reset_index()
    print(latest[["city", "year"] + rate_cols].to_string(index=False))


if __name__ == "__main__":
    run()
