"""
Visualization suite — Madison vs. Austin housing study.
Mirrors the chart types used in the PEW Austin report.

Charts produced:
  1. rent_index.png       - Indexed rent (2017=100) Madison vs. Austin vs. US
  2. yoy_change.png       - Year-over-year % rent change
  3. permitting_rate.png  - Units permitted per 100k residents (bar, by year)
  4. affordability.png    - % AMI needed to afford median rent (line)
  5. cost_burden.png      - Cost burden rate by race, latest year (grouped bar)
  6. ami_gap.png          - Affordability gap by AMI tier, latest year (diverging bar)
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

PALETTE = {
    "Madison, WI": "#1f77b4",
    "Austin, TX":  "#d62728",
    "United States": "#7f7f7f",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})


def chart_rent_index():
    df = pd.read_csv("data/rent_trends_summary.csv", parse_dates=["date"])
    fig, ax = plt.subplots(figsize=(10, 5))
    for city, grp in df.groupby("RegionName"):
        if city not in PALETTE:
            continue
        grp = grp.sort_values("date")
        ax.plot(grp["date"], grp["zori_indexed"], label=city, color=PALETTE[city], linewidth=2)
    ax.axhline(100, color="#aaa", linewidth=0.8, linestyle="--")
    ax.set_title("Rent Index (Jan 2017 = 100)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Index")
    ax.legend()
    fig.tight_layout()
    fig.savefig("viz/rent_index.png")
    plt.close(fig)
    print("Saved viz/rent_index.png")


def chart_yoy_change():
    df = pd.read_csv("data/rent_trends_summary.csv", parse_dates=["date"])
    fig, ax = plt.subplots(figsize=(10, 5))
    for city, grp in df.groupby("RegionName"):
        if city not in PALETTE:
            continue
        grp = grp.sort_values("date")
        ax.plot(grp["date"], grp["zori_yoy"], label=city, color=PALETTE[city], linewidth=2)
    ax.axhline(0, color="#aaa", linewidth=0.8, linestyle="--")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_title("Year-over-Year Rent Change", fontsize=13, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig("viz/yoy_change.png")
    plt.close(fig)
    print("Saved viz/yoy_change.png")


def chart_permitting_rate():
    df = pd.read_csv("data/permitting_rate.csv")
    df = df[df["city"].isin(["Madison, WI", "Austin, TX"])].dropna(subset=["units_per_100k"])
    df = df[df["year"].between(2015, 2024)]

    pivot = df.groupby(["city", "year"])["units_per_100k"].sum().unstack("city")
    fig, ax = plt.subplots(figsize=(11, 5))
    pivot.plot(kind="bar", ax=ax, color=[PALETTE[c] for c in pivot.columns], width=0.7)
    ax.axhline(957, color="#d62728", linewidth=1, linestyle=":", alpha=0.6,
               label="Austin PEW benchmark (957)")
    ax.set_title("Residential Units Permitted per 100,000 Residents", fontsize=13, fontweight="bold")
    ax.set_ylabel("Units per 100k")
    ax.set_xlabel("")
    ax.legend()
    fig.tight_layout()
    fig.savefig("viz/permitting_rate.png")
    plt.close(fig)
    print("Saved viz/permitting_rate.png")


def chart_affordability_threshold():
    df = pd.read_csv("data/affordability_threshold.csv")
    fig, ax = plt.subplots(figsize=(10, 5))
    for city, grp in df.groupby("city"):
        if city not in PALETTE:
            continue
        ax.plot(grp["year"], grp["threshold_pct_ami"], label=city,
                color=PALETTE[city], linewidth=2, marker="o", markersize=4)
    # PEW reference lines
    ax.axhline(95, color="#d62728", linewidth=0.8, linestyle="--", alpha=0.5,
               label="Austin 2015 (PEW: 95% AMI)")
    ax.axhline(84, color="#d62728", linewidth=0.8, linestyle=":",  alpha=0.5,
               label="Austin 2024 (PEW: 84% AMI)")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_title("% of AMI Required to Afford Median Market Rent", fontsize=13, fontweight="bold")
    ax.set_ylabel("% Area Median Income")
    ax.legend()
    fig.tight_layout()
    fig.savefig("viz/affordability.png")
    plt.close(fig)
    print("Saved viz/affordability.png")


def chart_cost_burden_by_race():
    df = pd.read_csv("data/racial_equity.csv")
    latest = df.groupby("city").last().reset_index()

    races = ["White_NonHisp", "Black_AA", "Hispanic", "Asian"]
    race_labels = {"White_NonHisp": "White\n(non-Hisp)", "Black_AA": "Black/AA",
                   "Hispanic": "Hispanic", "Asian": "Asian"}

    cities = ["Madison, WI", "Austin, TX"]
    x = range(len(races))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 5))
    for i, city in enumerate(cities):
        row = latest[latest["city"] == city]
        if row.empty:
            continue
        vals = [float(row[f"{r}__burden_rate"].values[0] or 0) * 100 for r in races]
        offset = (i - 0.5) * width
        ax.bar([xi + offset for xi in x], vals, width=width,
               label=city, color=PALETTE[city], alpha=0.85)

    ax.set_xticks(list(x))
    ax.set_xticklabels([race_labels[r] for r in races])
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax.set_title("Renter Cost Burden Rate by Race (Latest ACS Year)", fontsize=13, fontweight="bold")
    ax.set_ylabel("% of renters spending 30%+ on rent")
    ax.legend()
    fig.tight_layout()
    fig.savefig("viz/cost_burden.png")
    plt.close(fig)
    print("Saved viz/cost_burden.png")


def chart_ami_gap():
    df = pd.read_csv("data/affordability_gap_by_tier.csv")
    latest = df.groupby(["city", "ami_tier"]).last().reset_index()

    tier_order = [
        "Extremely Low (30% AMI)",
        "Very Low (50% AMI)",
        "Low (80% AMI)",
        "Moderate (100% AMI)",
        "Middle (120% AMI)",
    ]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, city in zip(axes, ["Madison, WI", "Austin, TX"]):
        sub = latest[latest["city"] == city].set_index("ami_tier").reindex(tier_order)
        colors = ["#d62728" if g < 0 else "#2ca02c" for g in sub["gap"]]
        ax.barh(sub.index, sub["gap"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(city, fontsize=11, fontweight="bold")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))

    fig.suptitle("Monthly Affordability Gap by AMI Tier\n(Green = affordable, Red = unaffordable)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig("viz/ami_gap.png")
    plt.close(fig)
    print("Saved viz/ami_gap.png")


def run():
    chart_rent_index()
    chart_yoy_change()
    chart_permitting_rate()
    chart_affordability_threshold()
    chart_cost_burden_by_race()
    chart_ami_gap()


if __name__ == "__main__":
    run()


def chart_scenario_projection():
    df = pd.read_csv("data/scenario_projection.csv")
    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#aec7e8", "#1f77b4", "#d62728", "#ff7f0e"]
    bars = ax.barh(df["scenario"], df["projected_threshold_pct_ami_5yr"],
                   color=colors, edgecolor="white")
    ax.axvline(df[df["scenario"] == "Current pace"]["projected_threshold_pct_ami_5yr"].values[0],
               color="#aaa", linewidth=1.2, linestyle="--", label="Current trajectory")
    for bar, (_, row) in zip(bars, df.iterrows()):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                f"{row['projected_threshold_pct_ami_5yr']:.1f}% AMI ({row['change_pp_5yr']:+.1f} pp)",
                va="center", fontsize=9)
    ax.set_xlabel("% of AMI Needed to Afford Median Rent (5-yr projection)")
    ax.set_title("Madison: Supply Scenario Projections — AMI Affordability Threshold (5-Year)",
                 fontsize=12, fontweight="bold")
    ax.set_xlim(55, 80)
    fig.tight_layout()
    fig.savefig("viz/scenario_projection.png")
    plt.close(fig)
    print("Saved viz/scenario_projection.png")
