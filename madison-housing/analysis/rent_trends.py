"""
Replicates PEW's core rent-trend analysis for Madison vs. Austin.

PEW key findings to replicate:
  - Austin rents rose 93% from 2010-2019, then fell back after supply surge
  - By Jan 2026 Austin median rent was 4% BELOW the U.S. median
  - Austin permitted 957 apartments per 100k residents (2021-2023)

Outputs:
  - rent_trends_summary.csv  (year-over-year % change, indexed levels)
  - permitting_rate.csv      (units per 100k residents by city/year)
"""

import pandas as pd
import numpy as np


def load_data():
    zori = pd.read_csv("data/zillow_zori.csv", parse_dates=["date"])
    acs = pd.read_csv("data/acs_rent_income.csv")
    permits = pd.read_csv("data/permits_summary.csv")
    return zori, acs, permits


def rent_trend_analysis(zori: pd.DataFrame) -> pd.DataFrame:
    monthly = (
        zori[zori["RegionName"].isin(["Madison, WI", "Austin, TX", "United States"])]
        .sort_values(["RegionName", "date"])
        .copy()
    )

    # YoY % change
    monthly["zori_yoy"] = monthly.groupby("RegionName")["zori"].pct_change(12) * 100

    # Gap vs. national (Austin PEW finding: rent fell 4% below US median)
    national = monthly[monthly["RegionName"] == "United States"][["date", "zori"]].rename(
        columns={"zori": "us_zori"}
    )
    monthly = monthly.merge(national, on="date", how="left")
    monthly["pct_vs_national"] = (monthly["zori"] / monthly["us_zori"] - 1) * 100

    return monthly


def permitting_rate(permits: pd.DataFrame, acs: pd.DataFrame) -> pd.DataFrame:
    total_permits = (
        permits.groupby(["city", "year"])["units_permitted"].sum().reset_index()
    )
    pop = acs[["city", "year", "population"]].copy()
    pop["population"] = pd.to_numeric(pop["population"], errors="coerce")

    merged = total_permits.merge(pop, on=["city", "year"], how="left")
    merged["units_per_100k"] = merged["units_permitted"] / merged["population"] * 100_000

    # PEW benchmark: Austin 957 units/100k (2021-2023), San Antonio 346
    pew_benchmark = pd.DataFrame({
        "city": ["Austin, TX (PEW 2021-23)", "San Antonio (PEW 2021-23)"],
        "year": [2022, 2022],
        "units_per_100k": [957, 346],
    })
    return pd.concat([merged, pew_benchmark], ignore_index=True)


def ami_affordability(acs: pd.DataFrame) -> pd.DataFrame:
    """
    PEW tracked: median 1BR affordability shifted from 95% AMI → 84% AMI in Austin.
    We approximate: median gross rent as % of AMI (AMI ≈ HH income / 1.2 for renter household).
    """
    df = acs.copy()
    df["median_gross_rent"] = pd.to_numeric(df["median_gross_rent"], errors="coerce")
    df["median_hh_income"] = pd.to_numeric(df["median_hh_income"], errors="coerce")
    # Annual rent as % of area median income
    df["annual_rent"] = df["median_gross_rent"] * 12
    df["rent_pct_ami"] = df["annual_rent"] / df["median_hh_income"] * 100
    return df[["city", "year", "median_gross_rent", "median_hh_income", "annual_rent", "rent_pct_ami"]]


def run():
    zori, acs, permits = load_data()

    trends = rent_trend_analysis(zori)
    trends.to_csv("data/rent_trends_summary.csv", index=False)
    print("Saved rent_trends_summary.csv")

    perm_rate = permitting_rate(permits, acs)
    perm_rate.to_csv("data/permitting_rate.csv", index=False)
    print("Saved permitting_rate.csv")

    ami = ami_affordability(acs)
    ami.to_csv("data/ami_affordability.csv", index=False)
    print("Saved ami_affordability.csv")

    # Print headline comparison
    print("\n--- Headline Comparison ---")
    for city in ["Madison, WI", "Austin, TX"]:
        city_ami = ami[ami["city"] == city].sort_values("year")
        if not city_ami.empty:
            first = city_ami.iloc[0]
            last = city_ami.iloc[-1]
            print(f"{city}: rent/AMI {first['rent_pct_ami']:.1f}% ({first['year']}) "
                  f"→ {last['rent_pct_ami']:.1f}% ({last['year']})")


if __name__ == "__main__":
    run()
