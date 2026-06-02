"""
Geographic permit maps — Madison vs. Austin (geopandas + contextily).

Maps produced:
  1. madison_permits_map.png  - Permit density by census tract, Madison
  2. austin_permits_map.png   - Permit density by census tract, Austin

Requires: geopandas, contextily, shapely
Census TIGER tract shapefiles downloaded automatically via Census API.
"""

import pandas as pd
import geopandas as gpd
import contextily as ctx
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import requests
from pathlib import Path
import zipfile
import io

TIGER_BASE = "https://www2.census.gov/geo/tiger/TIGER2023/TRACT"

CITY_CONFIG = {
    "Madison, WI": {
        "state_fips": "55",
        "county_fips": "025",
        "center": (-89.40, 43.07),
        "zoom": 11,
    },
    "Austin, TX": {
        "state_fips": "48",
        "county_fips": "453",
        "center": (-97.74, 30.27),
        "zoom": 10,
    },
}


def download_tract_shapefile(state_fips: str, county_fips: str) -> gpd.GeoDataFrame:
    fname = f"tl_2023_{state_fips}_tract.zip"
    cache_path = Path(f"data/{fname}")
    if not cache_path.exists():
        url = f"{TIGER_BASE}/{fname}"
        print(f"  Downloading {url} ...")
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        cache_path.write_bytes(r.content)
    gdf = gpd.read_file(f"zip://{cache_path}")
    return gdf[gdf["COUNTYFP"] == county_fips].copy()


def geocode_permits_to_tracts(permits_raw: pd.DataFrame, tracts: gpd.GeoDataFrame,
                               city: str) -> gpd.GeoDataFrame:
    """
    Aggregates permit counts to census tract level.
    Expects permits_raw to have lat/lon columns; falls back to tract-level
    random jitter if coordinates are unavailable (placeholder until real geocoding).
    """
    if "latitude" in permits_raw.columns and "longitude" in permits_raw.columns:
        pts = gpd.GeoDataFrame(
            permits_raw,
            geometry=gpd.points_from_xy(permits_raw["longitude"], permits_raw["latitude"]),
            crs="EPSG:4326",
        )
        tracts_proj = tracts.to_crs("EPSG:4326")
        joined = gpd.sjoin(pts, tracts_proj[["GEOID", "geometry"]], how="left", predicate="within")
        counts = joined.groupby("GEOID")["units"].sum().reset_index(name="units_permitted")
    else:
        # No geocoordinates: distribute permits uniformly for placeholder map
        print(f"  NOTE: No lat/lon for {city} permits — showing placeholder distribution.")
        counts = pd.DataFrame({
            "GEOID": tracts["GEOID"].values,
            "units_permitted": 0,
        })

    merged = tracts.merge(counts, on="GEOID", how="left")
    merged["units_permitted"] = merged["units_permitted"].fillna(0)
    return merged


def make_map(city: str):
    cfg = CITY_CONFIG[city]
    print(f"Building map: {city}")

    tracts = download_tract_shapefile(cfg["state_fips"], cfg["county_fips"])
    permits_raw = pd.read_csv("data/permits_summary.csv")
    city_permits = permits_raw[permits_raw["city"] == city].copy()

    gdf = geocode_permits_to_tracts(city_permits, tracts, city)
    gdf = gdf.to_crs(epsg=3857)

    fig, ax = plt.subplots(1, 1, figsize=(10, 10))
    gdf.plot(
        column="units_permitted",
        cmap="YlOrRd",
        linewidth=0.3,
        edgecolor="white",
        ax=ax,
        legend=True,
        legend_kwds={"label": "Units Permitted", "orientation": "horizontal", "shrink": 0.6},
        missing_kwds={"color": "#eeeeee"},
    )
    try:
        ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=cfg["zoom"])
    except Exception:
        pass  # basemap is cosmetic; skip if network unavailable

    ax.set_axis_off()
    ax.set_title(f"{city}: Residential Permits by Census Tract", fontsize=14, fontweight="bold")
    out = f"viz/{city.replace(', ', '_').replace(' ', '_').lower()}_permits_map.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Saved {out}")


def run():
    for city in CITY_CONFIG:
        try:
            make_map(city)
        except Exception as e:
            print(f"  ERROR {city}: {e}")


if __name__ == "__main__":
    run()
