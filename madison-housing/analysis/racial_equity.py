"""
Cost burden by race — Madison vs. Austin.

ACS tables used:
  B25003[race] - Tenure by race (gives renter household counts)
  B19001[race] - Household income by race (16 income brackets)
  B25064        - Median gross rent (from acs_rent_income.csv)

Methodology:
  We estimate the share of renter households by race who are cost-burdened
  (spending 30%+ of income on rent) by identifying the income threshold below
  which market rent would consume 30%+ of income:

    income_threshold = median_gross_rent * 12 / 0.30

  Households earning below that threshold are considered likely cost-burdened.
  We sum the ACS income bracket counts below the threshold for each race group
  and divide by total renter households for that race group.

  This is a standard research proxy used when direct race x cost-burden tables
  are unavailable at the place level (ACS B25106 has no race variants).

Race groups:
  B   Black or African American alone
  D   Asian alone
  H   White alone, not Hispanic or Latino
  I   Hispanic or Latino
"""

import os
import time
import requests
import pandas as pd
import numpy as np

API_KEY = os.environ.get("CENSUS_API_KEY", "")
BASE = "https://api.census.gov/data"

PLACES = [
    ("Madison, WI",  "55", "48000"),
    ("Austin, TX",   "48", "05000"),
]

RACE_GROUPS = {
    "White_NonHisp": "H",
    "Black_AA":       "B",
    "Hispanic":       "I",
    "Asian":          "D",
}

# Income bracket upper bounds for B19001 cols 002-017 (in $)
INCOME_BRACKETS = [
    ("_002E", 9999),
    ("_003E", 14999),
    ("_004E", 19999),
    ("_005E", 24999),
    ("_006E", 29999),
    ("_007E", 34999),
    ("_008E", 39999),
    ("_009E", 44999),
    ("_010E", 49999),
    ("_011E", 59999),
    ("_012E", 74999),
    ("_013E", 99999),
    ("_014E", 124999),
    ("_015E", 149999),
    ("_016E", 199999),
    ("_017E", float("inf")),
]

YEARS = list(range(2015, 2024))


def build_variables(race_letter: str) -> list[str]:
    table_b = f"B25003{race_letter}"
    table_i = f"B19001{race_letter}"
    vars_ = [
        f"{table_b}_001E",  # total households
        f"{table_b}_003E",  # renter occupied
    ]
    vars_ += [f"{table_i}{suffix}" for suffix, _ in INCOME_BRACKETS]
    return vars_


def fetch_year_race(year: int, state: str, place: str, race_letter: str) -> dict:
    vars_ = build_variables(race_letter)
    url = (
        f"{BASE}/{year}/acs/acs5"
        f"?get={','.join(vars_)}"
        f"&for=place:{place}&in=state:{state}"
        f"&key={API_KEY}"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    rows = r.json()
    header, data = rows[0], rows[1]
    return dict(zip(header, data))


def estimate_burden_rate(raw: dict, race_letter: str, annual_income_threshold: float) -> float:
    """
    Fraction of renter HHs for this race group earning below the cost-burden threshold.
    We approximate: all renter HHs earning below threshold as cost-burdened.
    """
    table_i = f"B19001{race_letter}"
    renter_total = pd.to_numeric(raw.get(f"B25003{race_letter}_003E"), errors="coerce")
    if pd.isna(renter_total) or renter_total == 0:
        return np.nan

    # Sum income brackets entirely below the threshold
    burdened = 0.0
    for suffix, upper_bound in INCOME_BRACKETS:
        count = pd.to_numeric(raw.get(f"{table_i}{suffix}"), errors="coerce") or 0
        if upper_bound < annual_income_threshold:
            burdened += count
        elif upper_bound == float("inf"):
            pass  # above threshold — not burdened
        else:
            # Partially overlapping bracket: interpolate linearly
            bracket_lower = (
                INCOME_BRACKETS[INCOME_BRACKETS.index((suffix, upper_bound)) - 1][1] + 1
                if INCOME_BRACKETS.index((suffix, upper_bound)) > 0
                else 0
            )
            bracket_width = upper_bound - bracket_lower
            if bracket_width > 0:
                fraction = max(0, min(1, (annual_income_threshold - bracket_lower) / bracket_width))
                burdened += count * fraction

    return burdened / renter_total


def run():
    acs = pd.read_csv("data/acs_rent_income.csv")

    records = []
    for city_name, state, place in PLACES:
        for year in YEARS:
            # Get median rent for this city/year to compute threshold
            acs_row = acs[(acs["city"] == city_name) & (acs["year"] == year)]
            if acs_row.empty:
                continue
            median_rent = pd.to_numeric(acs_row.iloc[0]["median_gross_rent"], errors="coerce")
            if pd.isna(median_rent):
                continue
            income_threshold = median_rent * 12 / 0.30

            row = {"city": city_name, "year": year, "income_threshold": income_threshold}

            for race_name, race_letter in RACE_GROUPS.items():
                try:
                    raw = fetch_year_race(year, state, place, race_letter)
                    row[f"{race_name}__renter_total"] = pd.to_numeric(
                        raw.get(f"B25003{race_letter}_003E"), errors="coerce"
                    )
                    row[f"{race_name}__burden_rate"] = estimate_burden_rate(
                        raw, race_letter, income_threshold
                    )
                    time.sleep(0.15)
                except Exception as e:
                    print(f"  WARN {city_name} {year} {race_name}: {e}")
                    row[f"{race_name}__renter_total"] = np.nan
                    row[f"{race_name}__burden_rate"] = np.nan

            records.append(row)

    df = pd.DataFrame(records)
    out = "data/racial_equity.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} rows → {out}")

    rate_cols = [c for c in df.columns if c.endswith("__burden_rate")]
    print("\n--- Estimated cost burden rates by race (most recent year) ---")
    latest = df.groupby("city").last().reset_index()
    print(latest[["city", "year"] + rate_cols].to_string(index=False))


if __name__ == "__main__":
    run()
