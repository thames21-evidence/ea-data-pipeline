# e - SAMPLING POINT DISCOVERY

from typing import Optional, Tuple
import re
import time
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

from .c_api import fetch_all
from ea_shared.c_geospatial import representative_point, compute_query_radius
from .a_config import POINT_FETCH_PAUSE, PAGINATION_SLEEP

# BNG (EPSG:27700) -> WGS84 (EPSG:4326)
_BNG_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
# Matches "POINT(easting northing)" from the API's asWKT field
_WKT_POINT_RE = re.compile(r"POINT\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)", re.IGNORECASE)


def _parse_geometry(item: dict) -> Optional[Tuple[float, float]]:
    """
    Extract (lon, lat) in WGS84 from a sampling-point API item.
    The API returns geometry as WKT in BNG (EPSG:27700):
      geometry.asWKT = "POINT(490739 288855) <...EPSG/0/27700>"
    Returns None if geometry cannot be parsed.
    """
    geom = item.get("geometry", {})
    if not isinstance(geom, dict):
        return None
    wkt = geom.get("asWKT", "")
    if not wkt:
        return None
    m = _WKT_POINT_RE.search(wkt)
    if not m:
        return None
    easting, northing = float(m.group(1)), float(m.group(2))
    lon, lat = _BNG_TO_WGS84.transform(easting, northing)
    return lon, lat

import logging
log = logging.getLogger(__name__)


def discover_sampling_points(poly, wb_name: Optional[str] = None):
    """
    Discover EA Water Quality sampling points within a waterbody polygon.

    - Endpoint: GET /sampling-point with latitude, longitude, radius (km) parameters
    - Geometry is returned as WKT in BNG (EPSG:27700) and converted to WGS84
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

    raw_items = fetch_all(
        "sampling-point",
        params={
            "latitude": lat,
            "longitude": lon,
            "radius": radius,
        },
        pagination_sleep=PAGINATION_SLEEP,
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
    # Geometry is WKT in BNG (EPSG:27700); convert to WGS84 lon/lat.
    rows = []
    for item in raw_items:
        coords = _parse_geometry(item)
        if coords is None:
            log.debug(f"[discover_sampling_points] Skipping item with no geometry: {item.get('notation')}")
            continue
        lon_i, lat_i = coords

        rows.append({
            "notation":  item.get("notation"),
            "label":     item.get("prefLabel") or item.get("altLabel") or item.get("notation"),
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
