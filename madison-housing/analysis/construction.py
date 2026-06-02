"""
Units built by type, year, and affordability tier — Madison vs. Austin.

PEW framework adapted:
  - Track SF vs. MF_small vs. MF_large permit trends over time
  - Identify the "supply surge" window (Austin: 2021-2023)
  - Calculate cumulative units added per capita (Austin: 120k units 2015-2024)
  - Flag whether Madison is above/below Austin's 957-per-100k benchmark
"""

import pandas as pd


def run():
    permits = pd.read_csv("data/permits_summary.csv")
    acs = pd.read_csv("data/acs_rent_income.csv")

    pop = (
        acs[["city", "year", "population"]]
        .assign(population=lambda d: pd.to_numeric(d["population"], errors="coerce"))
    )

    # Annual totals by permit class
    annual = (
        permits.groupby(["city", "year", "permit_class"])["units_permitted"]
        .sum()
        .reset_index()
    )

    # Per-capita rates
    annual = annual.merge(pop, on=["city", "year"], how="left")
    annual["units_per_100k"] = annual["units_permitted"] / annual["population"] * 100_000

    # Cumulative units 2015-2024 (PEW: Austin added 120k)
    cumulative = (
        annual[annual["year"].between(2015, 2024)]
        .groupby(["city", "permit_class"])["units_permitted"]
        .sum()
        .reset_index()
        .rename(columns={"units_permitted": "units_2015_2024"})
    )

    # Supply surge detection: year with highest MF_large permits
    mf_large = annual[annual["permit_class"] == "MF_large"].copy()
    surge_year = (
        mf_large.loc[mf_large.groupby("city")["units_permitted"].idxmax()]
        [["city", "year", "units_permitted"]]
        .rename(columns={"year": "peak_mf_year", "units_permitted": "peak_mf_units"})
    )

    annual.to_csv("data/construction_annual.csv", index=False)
    cumulative.to_csv("data/construction_cumulative.csv", index=False)
    surge_year.to_csv("data/supply_surge.csv", index=False)

    print("Saved construction_annual.csv, construction_cumulative.csv, supply_surge.csv")
    print("\n--- Cumulative 2015-2024 ---")
    print(cumulative.to_string(index=False))
    print("\n--- Peak multifamily year ---")
    print(surge_year.to_string(index=False))


if __name__ == "__main__":
    run()
