# scripts/ecology_aj.py

import sys
import logging
import time
from pathlib import Path
import geopandas as gpd
import pandas as pd

LOG_PATH = Path(__file__).resolve().parents[1] / "run_ecology.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.append(str(SRC))

from ea_ecology.a_config import SELECTED_GROUPS, CATCHMENT_SHP, TMP_DIR
from ea_ecology.b_utils import _safe_name
from ea_ecology.d_geospatial import compute_query_radius
from ea_ecology.e_site import discover_sites
from ea_ecology.f_observations import fetch_observations_for_group
from ea_ecology.g_checkpoint import save_checkpoint, checkpoint_exists, load_checkpoint
from ea_ecology.h_aggregation import rows_to_dataframe
from ea_ecology.j_pivot import pivot_group, collate_all_pivots

RAW_DIR = ROOT / "data" / "output" / "ea_ecology" / "_raw"
PIVOT_DIR = ROOT / "data" / "output" / "ea_ecology" / "_pivot"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PIVOT_DIR.mkdir(parents=True, exist_ok=True)

from ea_ecology.a_config import DRY_RUN


def main():
    log.info(f"Loading catchment polygons from {CATCHMENT_SHP}")
    catch_gdf = gpd.read_file(CATCHMENT_SHP)

    if catch_gdf.crs and catch_gdf.crs.to_epsg() != 4326:
        log.info(f"Reprojecting from {catch_gdf.crs} to EPSG:4326")
        catch_gdf = catch_gdf.to_crs(epsg=4326)

    # pick a grouping field
    group_field = None
    for col in ("CaBA_Catch", "WB_NAME", "wb_name", "name", "label"):
        if col in catch_gdf.columns:
            group_field = col
            break

    if group_field:
        dissolved = catch_gdf.dissolve(by=group_field, as_index=False)
    else:
        dissolved = catch_gdf.copy().reset_index().rename(columns={"index": "feature_index"})

    # MAIN LOOP
    for idx, row in dissolved.iterrows():
        raw_name = row[group_field] if group_field else f"catch_{idx}"
        safe_name = _safe_name(raw_name)

        log.info(f"=== Processing {raw_name} ===")

        poly = row.geometry
        rep_pt = poly.representative_point()
        lat, long = float(rep_pt.y), float(rep_pt.x)

        maxd = compute_query_radius(poly, rep_pt)
        radius = maxd + 1.0

        log.info(f"Discovering sites inside {raw_name}")
        sites_inside, lat, long, radius, raw_items = discover_sites(poly, raw_name)

        if sites_inside.empty:
            log.warning(f"No sites found for {raw_name}")
            continue

        # --- CLEAN UP ANY PREVIOUS JOIN COLUMNS ---
        for col in ["index_right", "index_left"]:
            if col in sites_inside.columns:
                sites_inside = sites_inside.drop(columns=[col])

        # --- ENRICH SITES WITH POLYGON ATTRIBUTES ---
        poly_gdf = gpd.GeoDataFrame([row], geometry="geometry", crs=dissolved.crs)

        for col in ["index_right", "index_left"]:
            if col in poly_gdf.columns:
                poly_gdf = poly_gdf.drop(columns=[col])

        sites_inside = gpd.sjoin(
            sites_inside,
            poly_gdf,
            how="left",
            predicate="within",
        )

        # GROUP LOOP — ALWAYS RUNS
        for group in SELECTED_GROUPS:
            log.info(f"   → Starting group: {group}")

            # FETCH OR LOAD RAW
            if checkpoint_exists(safe_name, group):
                log.info(f"   Loading checkpoint for {group}")
                rows = load_checkpoint(safe_name, group)
            else:
                log.info(f"   Fetching observations for {group}")
                rows = fetch_observations_for_group(group, sites_inside, raw_name)
                save_checkpoint(safe_name, group, rows)

            # Convert rows to DataFrame FIRST
            df = rows_to_dataframe(rows)

            # Now safely check emptiness
            if df is None or df.empty:
                log.warning(f"   No observations for {group}")
                continue

            timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H%M")

            # SAVE RAW
            raw_path = RAW_DIR / f"{safe_name}__{group}__raw_{timestamp}.csv"
            df.to_csv(raw_path, index=False)
            log.info(f"   ✓ Raw saved → {raw_path.name}")

            # ALWAYS PIVOT
            pivot_df = pivot_group(df, group)
            if not pivot_df.empty:
                pivot_path = PIVOT_DIR / f"{safe_name}__{group}__pivot_{timestamp}.csv"
                pivot_df.to_csv(pivot_path, index=False)
                log.info(f"   ✓ Pivot saved → {pivot_path.name}")
            else:
                log.warning(f"   Pivot empty for {group}")

        log.info(f"=== Finished {raw_name} ===\n")

    # WAIT FOR FILESYSTEM FLUSH
    log.info("Waiting for filesystem flush before collation…")
    time.sleep(2)

    # COLLATE
    collate_all_pivots()


if __name__ == "__main__":
    main()