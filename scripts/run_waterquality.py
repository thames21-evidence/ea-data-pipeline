"""
Run the EA Water Quality pipeline.

For each waterbody in the catchment shapefile:
  1. Discover sampling points inside the polygon
  2. Fetch ammonia + phosphate observations (with checkpointing)
  3. Save a per-waterbody / per-determinand CSV

Then collate everything into Thames21-wide CSVs.

Usage:
    python scripts/run_waterquality.py
"""

import sys
import math
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

import logging
import geopandas as gpd

from ea_waterquality.a_config import (
    CATCHMENT_SHP,
    SELECTED_DETERMINANDS,
    DRY_RUN,
)
from ea_waterquality.e_site import load_region_sampling_points, filter_points_for_waterbody
from ea_waterquality.f_observations import fetch_measurements_for_determinand
from ea_waterquality.g_checkpoint import load_checkpoint, save_checkpoint, checkpoint_exists
from ea_waterquality.h_aggregation import rows_to_dataframe
from ea_waterquality.i_out import save_output
from ea_waterquality.j_pivot import collate_all_pivots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


def main():
    log.info("=== EA Water Quality Pipeline ===")
    if DRY_RUN:
        log.info("DRY RUN — no data will be written")

    waterbodies = gpd.read_file(CATCHMENT_SHP).to_crs("EPSG:4326")
    log.info(f"Loaded {len(waterbodies)} waterbodies from shapefile")

    group_field = None
    for col in ("CaBA_Catch", "WB_NAME", "wb_name", "name", "label"):
        if col in waterbodies.columns:
            group_field = col
            break
    log.info(f"Using '{group_field}' as waterbody name field")

    # Compute bounding circle of the study area to pass as spatial filter
    bounds = waterbodies.total_bounds  # [minx, miny, maxx, maxy] in WGS84
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    half_w_km = (bounds[2] - bounds[0]) / 2 * 111.32 * math.cos(math.radians(center_lat))
    half_h_km = (bounds[3] - bounds[1]) / 2 * 110.57
    radius_km = math.ceil(math.sqrt(half_w_km ** 2 + half_h_km ** 2) * 1.15)
    log.info(f"Bounding circle: lat={center_lat:.3f}, lon={center_lon:.3f}, radius={radius_km}km")

    all_points = load_region_sampling_points(lat=center_lat, lon=center_lon, radius=radius_km)
    log.info(f"Loaded {len(all_points)} sampling points total\n")

    for _, wb in waterbodies.iterrows():
        wb_name = wb[group_field] if group_field else str(wb.name)
        poly = wb.geometry

        log.info(f"\n--- Waterbody: {wb_name} ---")

        points_inside = filter_points_for_waterbody(all_points, poly, wb_name)

        if points_inside.empty:
            log.warning(f"No sampling points found inside {wb_name}, skipping")
            continue

        log.info(f"Found {len(points_inside)} sampling point(s)")

        for determinand in SELECTED_DETERMINANDS:
            if checkpoint_exists(wb_name, determinand):
                log.info(f"  [{determinand}] checkpoint found, loading from disk")
                rows = load_checkpoint(wb_name, determinand).to_dict("records")
            else:
                log.info(f"  [{determinand}] fetching observations…")
                rows = fetch_measurements_for_determinand(determinand, points_inside, wb_name)
                if rows:
                    save_checkpoint(wb_name, determinand, rows)

            log.info(f"  [{determinand}] {len(rows)} row(s)")

            if not DRY_RUN:
                df = rows_to_dataframe(rows)
                save_output(df, wb_name, determinand)

    log.info("\n=== Collating outputs ===")
    if not DRY_RUN:
        collate_all_pivots()

    log.info("=== Done ===")


if __name__ == "__main__":
    main()
