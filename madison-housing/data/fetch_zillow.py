"""
Download Zillow Observed Rent Index (ZORI) CSVs for Madison and Austin,
plus the national series for benchmarking.

Zillow publishes these as public CSVs — no API key required.
All-homes ZORI (smoothed, seasonally adjusted):
  https://files.zillowstatic.com/research/public_csvs/zori/Metro_zori_uc_sfrcondomfr_sm_sa_month.csv

City-level series keyed by RegionName (e.g. "Madison, WI", "Austin, TX").
"""

import requests
import pandas as pd
from io import StringIO

ZORI_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zori/"
    "Metro_zori_uc_sfrcondomfr_sm_sa_month.csv"
)

CITIES_OF_INTEREST = {"Madison, WI", "Austin, TX", "United States"}


def run():
    print("Downloading Zillow ZORI...")
    r = requests.get(ZORI_URL, timeout=60)
    r.raise_for_status()

    df = pd.read_csv(StringIO(r.text))

    # Keep only rows for our cities
    mask = df["RegionName"].isin(CITIES_OF_INTEREST)
    df = df[mask].copy()

    # Wide → long: columns are month strings like "2015-01-31"
    id_cols = ["RegionID", "SizeRank", "RegionName", "RegionType", "StateName"]
    date_cols = [c for c in df.columns if c not in id_cols]

    df_long = df.melt(id_vars=id_cols, value_vars=date_cols, var_name="date", value_name="zori")
    df_long["date"] = pd.to_datetime(df_long["date"], errors="coerce")
    df_long = df_long.dropna(subset=["date", "zori"])
    df_long["year"] = df_long["date"].dt.year
    df_long["month"] = df_long["date"].dt.month

    # Index to Jan 2017 = 100 for easy comparison
    base = df_long[df_long["date"].dt.to_period("M") == "2017-01"].set_index("RegionName")["zori"]
    df_long["zori_indexed"] = df_long.apply(
        lambda row: row["zori"] / base.get(row["RegionName"], row["zori"]) * 100, axis=1
    )

    out = "data/zillow_zori.csv"
    df_long.to_csv(out, index=False)
    print(f"Saved {len(df_long)} rows → {out}")


if __name__ == "__main__":
    run()
