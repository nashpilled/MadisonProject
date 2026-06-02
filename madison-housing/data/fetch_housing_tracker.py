"""
Fetch building permit data for Madison, WI and Austin, TX.

Madison: City of Madison ArcGIS Feature Server
  https://services.arcgis.com/v400IkDOw1ad7Yad/ArcGIS/rest/services/Building_Permits/FeatureServer/0
  Key fields: issueddate_yr, housingunitstotal, workclassmapped, permitclassmapped

Austin: City of Austin Open Data (Socrata)
  https://data.austintexas.gov/resource/3syk-w9eu.json
  Key fields: issue_date, housing_units, permit_type_desc, work_class

Both are normalized to: city, year, permit_type, units, permit_class
  permit_class: SF (single-family), MF_small (2-4 units), MF_large (5+ units)
"""

import requests
import pandas as pd

MADISON_FEATURE_URL = (
    "https://services.arcgis.com/v400IkDOw1ad7Yad/ArcGIS/rest/services/"
    "Building_Permits/FeatureServer/0/query"
)

AUSTIN_BASE_URL = "https://data.austintexas.gov/resource/3syk-w9eu.json"


def classify_units(n: int) -> str:
    if n == 1:
        return "SF"
    if n <= 4:
        return "MF_small"
    return "MF_large"


def fetch_madison() -> pd.DataFrame:
    print("Fetching Madison permits (ArcGIS)...")
    records = []
    offset = 0
    page_size = 2000

    while True:
        params = {
            "where": "workclassmapped='New' AND permitclassmapped='Residential'",
            "outFields": "issueddate_yr,housingunitstotal,permitclassmapped,workclassmapped",
            "returnGeometry": "false",
            "resultOffset": offset,
            "resultRecordCount": page_size,
            "f": "json",
        }
        r = requests.get(MADISON_FEATURE_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        features = data.get("features", [])
        if not features:
            break
        for feat in features:
            attrs = feat.get("attributes", {})
            raw_units = attrs.get("housingunitstotal")
            records.append({
                "year": attrs.get("issueddate_yr"),
                "units": raw_units if raw_units and raw_units > 0 else 1,
            })
        if len(features) < page_size:
            break
        offset += page_size

    df = pd.DataFrame(records)
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(1).astype(int)
    df["permit_class"] = df["units"].apply(classify_units)
    df["city"] = "Madison, WI"
    print(f"  Madison: {len(df)} permit records")
    return df[["city", "year", "permit_class", "units"]].dropna(subset=["year"])


def fetch_austin() -> pd.DataFrame:
    print("Fetching Austin permits (Socrata)...")
    records = []
    offset = 0
    page_size = 50000

    while True:
        params = {
            "$limit": page_size,
            "$offset": offset,
            "$where": "permit_type_desc='Building Permit' AND work_class='New'",
            "$select": "issue_date,housing_units,permit_class",
        }
        r = requests.get(AUSTIN_BASE_URL, params=params, timeout=120)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        records.extend(data)
        if len(data) < page_size:
            break
        offset += page_size

    df = pd.DataFrame(records)
    df["issued_date"] = pd.to_datetime(df["issue_date"], errors="coerce")
    df["year"] = df["issued_date"].dt.year
    df["units"] = pd.to_numeric(df["housing_units"], errors="coerce").fillna(1).astype(int)
    df["permit_class"] = df["units"].apply(classify_units)
    df["city"] = "Austin, TX"
    print(f"  Austin: {len(df)} permit records")
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
