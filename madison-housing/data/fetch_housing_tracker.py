"""
Fetch building permit data for Madison, WI and Austin, TX.

Madison: City of Madison Open Data portal (Socrata)
  https://data-cityofmadison.opendata.arcgis.com/
  Dataset: Building Permits (residential focus)

Austin: City of Austin Open Data (Socrata)
  https://data.austintexas.gov/
  Dataset: Issued Construction Permits

Both are normalized to: city, year, permit_type, units, permit_class
  permit_class: SF (single-family), MF_small (2-4 units), MF_large (5+ units)
"""

import requests
import pandas as pd
from io import StringIO

MADISON_PERMITS_URL = (
    "https://data-cityofmadison.opendata.arcgis.com/api/explore/v2.1/catalog/datasets/"
    "building-permits/exports/csv?lang=en&timezone=US%2FChicago"
)

AUSTIN_PERMITS_URL = (
    "https://data.austintexas.gov/resource/3syk-w9eu.csv"
    "?$limit=200000"
    "&$where=permit_type_desc='BUILDING PERMIT' AND work_class='New'"
    "&$select=issued_date,units_added,housing_unit_count,permit_type_desc,project_id"
)


def classify_units(n: int) -> str:
    if n == 1:
        return "SF"
    if n <= 4:
        return "MF_small"
    return "MF_large"


def fetch_madison() -> pd.DataFrame:
    print("Fetching Madison permits...")
    r = requests.get(MADISON_PERMITS_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), low_memory=False)

    # Column names vary by export version — normalize
    df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]

    date_col = next((c for c in df.columns if "date" in c and "issue" in c), None)
    units_col = next((c for c in df.columns if "unit" in c), None)

    df["issued_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["year"] = df["issued_date"].dt.year
    df["units"] = pd.to_numeric(df.get(units_col, 1), errors="coerce").fillna(1).astype(int)
    df["permit_class"] = df["units"].apply(classify_units)
    df["city"] = "Madison, WI"

    return df[["city", "year", "permit_class", "units"]].dropna(subset=["year"])


def fetch_austin() -> pd.DataFrame:
    print("Fetching Austin permits...")
    r = requests.get(AUSTIN_PERMITS_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), low_memory=False)

    df["issued_date"] = pd.to_datetime(df["issued_date"], errors="coerce")
    df["year"] = df["issued_date"].dt.year

    units_col = "housing_unit_count" if "housing_unit_count" in df.columns else "units_added"
    df["units"] = pd.to_numeric(df[units_col], errors="coerce").fillna(1).astype(int)
    df["permit_class"] = df["units"].apply(classify_units)
    df["city"] = "Austin, TX"

    return df[["city", "year", "permit_class", "units"]].dropna(subset=["year"])


def run():
    frames = []
    for fetcher in [fetch_madison, fetch_austin]:
        try:
            frames.append(fetcher())
        except Exception as e:
            print(f"  WARN: {e}")

    df = pd.concat(frames, ignore_index=True)
    df = df[df["year"].between(2010, 2025)]

    summary = (
        df.groupby(["city", "year", "permit_class"])["units"]
        .sum()
        .reset_index()
        .rename(columns={"units": "units_permitted"})
    )

    out = "data/permits_summary.csv"
    summary.to_csv(out, index=False)
    print(f"Saved {len(summary)} rows → {out}")


if __name__ == "__main__":
    run()
