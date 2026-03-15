# e - SAMPLING POINT DISCOVERY

from typing import Optional
import time
import geopandas as gpd
from shapely.geometry import Point

from .c_api import fetch_json
from ea_shared.c_geospatial import representative_point, compute_query_radius
from .a_config import POINT_FETCH_PAUSE

import logging
log = logging.getLogger(__name__)


def discover_sampling_points(poly, wb_name: Optional[str] = None):
    """
    Discover EA Water Quality sampling points within a waterbody polygon.

    - Endpoint: id/sampling-point with lat, long, dist (km) parameters
    - Returns a GeoDataFrame of points inside the polygon, plus metadata
    """

    log.info(f"[discover_sampling_points] Starting for {wb_name}")

    # --- Step 1: representative point ---
    lat, lon = representative_point(poly)
    log.info(f"[discover_sampling_points] Rep point: lat={lat:.6f}, lon={lon:.6f}")

    # --- Step 2: dynamic radius ---
    radius = compute_query_radius(poly)
    log.info(f"[discover_sampling_points] Query radius: {radius:.2f} km")

    # --- Step 3: API query ---
    log.info(f"[discover_sampling_points] Calling EA Water Quality API…")
    t0 = time.time()

    raw_items = fetch_json(
        "sampling-point",
        params={
            "lat": lat,
            "long": lon,
            "dist": radius,
        },
    )

    api_time = time.time() - t0
    log.info(
        f"[discover_sampling_points] API returned {len(raw_items)} items in {api_time:.2f}s"
    )

    time.sleep(POINT_FETCH_PAUSE)

    if not raw_items:
        log.warning(f"[discover_sampling_points] No items returned for {wb_name}")
        return gpd.GeoDataFrame(), lat, lon, radius, raw_items

    # --- Step 4: convert to GeoDataFrame ---
    rows = []
    for item in raw_items:
        try:
            lat_i = float(item.get("lat") or item.get("easting") or 0)
            lon_i = float(item.get("long") or item.get("northing") or 0)
        except Exception:
            continue

        if lat_i == 0 or lon_i == 0:
            continue

        rows.append({
            "notation":  item.get("notation"),
            "label":     item.get("label"),
            "lat":       lat_i,
            "long":      lon_i,
            "geometry":  Point(lon_i, lat_i),
        })

    if not rows:
        log.warning(f"[discover_sampling_points] No valid rows after parsing for {wb_name}")
        return gpd.GeoDataFrame(), lat, lon, radius, raw_items

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    log.info(f"[discover_sampling_points] Parsed {len(gdf)} candidate sampling points")

    # --- Step 5: spatial filter ---
    try:
        poly_gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")
        points_inside = gpd.sjoin(gdf, poly_gdf, predicate="within", how="inner")
    except Exception as e:
        log.warning(f"[discover_sampling_points] sjoin failed ({e}); falling back to within()")
        points_inside = gdf[gdf.within(poly)]

    log.info(
        f"[discover_sampling_points] {len(points_inside)} sampling points inside polygon "
        f"for {wb_name}"
    )

    return points_inside, lat, lon, radius, raw_items
