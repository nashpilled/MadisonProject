"""
AMI vs. market rent gap analysis — Madison vs. Austin.

PEW key metrics adapted:
  - Affordability threshold: what % AMI is required to afford median 1BR?
    (PEW: Austin shifted from 95% AMI → 84% AMI as supply grew)
  - Cost burden rate: share of renters spending 30%+ of income on rent
  - Severe cost burden: 50%+ of income on rent
  - "Affordability gap": monthly rent minus 30% of monthly income at each AMI level
"""

import pandas as pd
import numpy as np


# HUD AMI tiers as % of area median income
AMI_TIERS = {
    "Extremely Low (30% AMI)": 0.30,
    "Very Low (50% AMI)":      0.50,
    "Low (80% AMI)":           0.80,
    "Moderate (100% AMI)":     1.00,
    "Middle (120% AMI)":       1.20,
}


def affordability_threshold(acs: pd.DataFrame) -> pd.DataFrame:
    """
    What % of AMI does a household need to afford median market rent
    (spending no more than 30% of income)?
    threshold_pct_ami = (annual_rent / 0.30) / area_median_income * 100
    """
    df = acs.copy()
    df["median_gross_rent"] = pd.to_numeric(df["median_gross_rent"], errors="coerce")
    df["median_hh_income"] = pd.to_numeric(df["median_hh_income"], errors="coerce")
    df["annual_rent"] = df["median_gross_rent"] * 12
    df["income_needed"] = df["annual_rent"] / 0.30
    df["threshold_pct_ami"] = df["income_needed"] / df["median_hh_income"] * 100
    return df[["city", "year", "median_gross_rent", "threshold_pct_ami"]]


def affordability_gap_by_tier(acs: pd.DataFrame) -> pd.DataFrame:
    """
    Monthly gap between market rent and what each AMI tier can afford.
    Negative = unaffordable for that tier.
    """
    rows = []
    for _, row in acs.iterrows():
        rent = pd.to_numeric(row["median_gross_rent"], errors="coerce")
        ami = pd.to_numeric(row["median_hh_income"], errors="coerce")
        if pd.isna(rent) or pd.isna(ami):
            continue
        for tier_name, pct in AMI_TIERS.items():
            affordable_rent = ami * pct * 0.30 / 12
            rows.append({
                "city": row["city"],
                "year": row["year"],
                "ami_tier": tier_name,
                "affordable_monthly_rent": round(affordable_rent, 2),
                "market_rent": rent,
                "gap": round(affordable_rent - rent, 2),
            })
    return pd.DataFrame(rows)


def cost_burden_summary(acs: pd.DataFrame) -> pd.DataFrame:
    df = acs.copy()
    for col in ["cost_burden_rate", "renter_occupied_units", "cost_burdened_count"]:
        df[col] = pd.to_numeric(df.get(col, np.nan), errors="coerce")

    df["severe_burden_count"] = pd.to_numeric(
        df.get("rent_burden_50plus_pct", np.nan), errors="coerce"
    )
    df["severe_burden_rate"] = df["severe_burden_count"] / df["renter_occupied_units"]

    return df[["city", "year", "cost_burden_rate", "severe_burden_rate", "renter_occupied_units"]]


def run():
    acs = pd.read_csv("data/acs_rent_income.csv")

    threshold = affordability_threshold(acs)
    threshold.to_csv("data/affordability_threshold.csv", index=False)

    gap = affordability_gap_by_tier(acs)
    gap.to_csv("data/affordability_gap_by_tier.csv", index=False)

    burden = cost_burden_summary(acs)
    burden.to_csv("data/cost_burden_summary.csv", index=False)

    print("Saved affordability_threshold.csv, affordability_gap_by_tier.csv, cost_burden_summary.csv")

    print("\n--- Affordability threshold (% AMI needed to afford market rent) ---")
    print(threshold.sort_values(["city", "year"]).to_string(index=False))


if __name__ == "__main__":
    run()
