# Madison Housing Study

Comparative housing analysis: Madison, WI vs. Austin, TX.
Adapted from PEW Trusts, *"Austin's Surge of New Housing Construction Drove Down Rents"* (March 2026).

## Quick start

```bash
pip install -r requirements.txt
export CENSUS_API_KEY="your_key_here"   # free at api.census.gov/data/key_signup.html

# 1. Collect data
python data/fetch_census.py
python data/fetch_housing_tracker.py
python data/fetch_zillow.py

# 2. Run analysis
python analysis/rent_trends.py
python analysis/construction.py
python analysis/affordability.py
python analysis/racial_equity.py

# 3. Generate charts and maps
python viz/charts.py
python viz/maps.py

# 4. Build report
python report/generate.py
# → report/madison_housing_report.md
```

## What each script does

| Script | Output | PEW metric replicated |
|---|---|---|
| `fetch_census.py` | `data/acs_rent_income.csv` | Median rent, income, cost burden |
| `fetch_housing_tracker.py` | `data/permits_summary.csv` | Units permitted by type/year |
| `fetch_zillow.py` | `data/zillow_zori.csv` | Rent index (2017=100) |
| `analysis/rent_trends.py` | `rent_trends_summary.csv`, `permitting_rate.csv`, `ami_affordability.csv` | 957 units/100k benchmark; 4% below US median |
| `analysis/construction.py` | `construction_annual.csv`, `construction_cumulative.csv`, `supply_surge.csv` | 120k units 2015-2024; peak MF year |
| `analysis/affordability.py` | `affordability_threshold.csv`, `affordability_gap_by_tier.csv`, `cost_burden_summary.csv` | 95%→84% AMI shift |
| `analysis/racial_equity.py` | `racial_equity.csv` | Cost burden by race |
| `viz/charts.py` | 6 PNG charts | All PEW chart types |
| `viz/maps.py` | 2 permit density maps | Geographic distribution |
| `report/generate.py` | `report/madison_housing_report.md` | Full structured report |

## Key PEW findings being tested for Madison

1. Austin permitted **957 apartments per 100k residents** (2021-2023) vs. 346 in San Antonio
2. Median rent fell to **4% below the US median** by Jan 2026
3. Class C rents declined **11%** in 2023-2024
4. Affordability threshold shifted **95% → 84% AMI**
5. **120,000 units** added 2015-2024
