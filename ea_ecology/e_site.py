# e - SITE DISCOVERY — FINAL, CORRECT, OLD-BEHAVIOUR VERSION

from typing import Optional
import time
import geopandas as gpd
from shapely.geometry import Point

from .c_api import fetch_all
from .d_geospatial import representative_point, compute_query_radius
from .a_config import SITE_FETCH_PAUSE

import logging
log = logging.getLogger(__name__)


def discover_sites(poly, wb_name: Optional[str] = None):
    """
    Correct EA Ecology site discovery:
    - Uses the correct endpoint: 'sites'
    - Uses correct spatial parameters: lat, long, distance_km
    - Parses correct fields: lat, long, site_id, label
    - Performs spatial join to filter sites inside polygon
    """

    log.info(f"[discover_sites] Starting site discovery for {wb_name}")

    # --- Step 1: representative point ---
    lat, lon = representative_point(poly)
    log.info(f"[discover_sites] Rep point: lat={lat:.6f}, lon={lon:.6f}")

    # --- Step 2: dynamic radius ---
    radius = compute_query_radius(poly)
    log.info(f"[discover_sites] Query radius: {radius:.2f} km")

    # --- Step 3: API query (correct endpoint + correct params) ---
    log.info(f"[discover_sites] Calling EA API (sites)…")
    t0 = time.time()

    raw_items = fetch_all(
        "sites",
        params={
            "mode": "minimal",
            "lat": lat,
            "long": lon,
            "distance_km": radius,
        },
    )

    api_time = time.time() - t0
    log.info(f"[discover_sites] EA API returned {len(raw_items)} items in {api_time:.2f}s")

    time.sleep(SITE_FETCH_PAUSE)

    if not raw_items:
        log.warning(f"[discover_sites] No raw items returned for {wb_name}")
        return gpd.GeoDataFrame(), lat, lon, radius, raw_items

    # --- Step 4: convert to GeoDataFrame ---
    log.info(f"[discover_sites] Converting raw items to GeoDataFrame…")
    rows = []
    for item in raw_items:
        try:
            lat_i = float(item.get("lat"))
            lon_i = float(item.get("long"))
        except Exception:
            continue

        rows.append({
            "site_id": item.get("site_id"),
            "label": item.get("label"),
            "lat": lat_i,
            "long": lon_i,
            "geometry": Point(lon_i, lat_i),
        })

    if not rows:
        log.warning(f"[discover_sites] No valid rows after parsing raw items")
        return gpd.GeoDataFrame(), lat, lon, radius, raw_items

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    log.info(f"[discover_sites] Parsed into {len(gdf)} candidate sites")

    # --- Step 5: spatial filter using sjoin ---
    log.info(f"[discover_sites] Performing spatial join…")
    t1 = time.time()

    try:
        poly_gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")
        sites_inside = gpd.sjoin(gdf, poly_gdf, predicate="within", how="inner")
        filter_time = time.time() - t1
        log.info(f"[discover_sites] Spatial join complete in {filter_time:.2f}s")
    except Exception as e:
        log.warning(f"[discover_sites] Spatial join failed ({e}); falling back to slow method")
        t2 = time.time()
        sites_inside = gdf[gdf.within(poly)]
        slow_time = time.time() - t2
        log.info(f"[discover_sites] Slow within() filter complete in {slow_time:.2f}s")

    log.info(f"[discover_sites] {len(sites_inside)} sites found inside polygon for {wb_name}")

    return sites_inside, lat, lon, radius, raw_items