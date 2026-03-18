# e - SAMPLING POINT DISCOVERY

from typing import Optional, Tuple
import re
import logging
import geopandas as gpd
from shapely.geometry import Point
from pyproj import Transformer

from .c_api import fetch_all
from .a_config import PAGINATION_SLEEP, PAGE_SIZE, SAMPLING_POINT_TYPE

log = logging.getLogger(__name__)

# BNG (EPSG:27700) -> WGS84 (EPSG:4326) — fallback if Accept-Crs header ignored
_BNG_TO_WGS84 = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
_WKT_POINT_RE = re.compile(r"POINT\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)", re.IGNORECASE)


def _parse_geometry(item: dict) -> Optional[Tuple[float, float]]:
    """
    Extract (lon, lat) in WGS84.
    With Accept-Crs: EPSG:4326 header the API returns lat/long directly.
    Falls back to parsing BNG WKT if those fields aren't present.
    """
    # WGS84 direct fields (when Accept-Crs: 4326 header is honoured)
    lat = item.get("lat") or item.get("latitude")
    lon = item.get("long") or item.get("longitude")
    if lat and lon:
        return float(lon), float(lat)

    # Fallback: parse BNG WKT
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
    lon_r, lat_r = _BNG_TO_WGS84.transform(easting, northing)
    return lon_r, lat_r


def load_region_sampling_points(
    lat: float,
    lon: float,
    radius: float,
) -> gpd.GeoDataFrame:
    """
    Fetch sampling points from the EA Water Quality API using a bounding circle.
    The API requires a spatial filter (lat/long/radius in km).
    Call once at pipeline start with the bounding circle of your study area;
    then use filter_points_for_waterbody() per polygon for exact spatial filtering.
    """
    log.info(
        f"[load_region_sampling_points] Fetching sampling points "
        f"lat={lat:.3f}, lon={lon:.3f}, radius={radius:.0f}km…"
    )

    raw_items = fetch_all(
        "sampling-point",
        params={
            "latitude": lat,
            "longitude": lon,
            "radius": radius,
            "samplingPointType": SAMPLING_POINT_TYPE,
        },
        page_size=PAGE_SIZE,
        pagination_sleep=PAGINATION_SLEEP,
    )

    log.info(f"[load_region_sampling_points] Got {len(raw_items)} raw items")

    rows = []
    for item in raw_items:
        coords = _parse_geometry(item)
        if coords is None:
            continue
        lon_i, lat_i = coords
        rows.append({
            "notation": item.get("notation"),
            "label":    item.get("prefLabel") or item.get("altLabel") or item.get("notation"),
            "lat":      lat_i,
            "long":     lon_i,
            "geometry": Point(lon_i, lat_i),
        })

    if not rows:
        log.warning("[load_region_sampling_points] No sampling points with geometry found")
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
    log.info(f"[load_region_sampling_points] Parsed {len(gdf)} sampling points")
    return gdf


def filter_points_for_waterbody(
    all_points: gpd.GeoDataFrame,
    poly,
    wb_name: Optional[str] = None,
    buffer_m: float = 100,
) -> gpd.GeoDataFrame:
    """
    Spatially filter pre-loaded sampling points to those within a waterbody polygon.
    A buffer (default 100m) is applied to the polygon before matching so that points
    on or near the boundary are included.
    """
    if all_points.empty:
        return gpd.GeoDataFrame()

    try:
        # Build polygon GDF in WGS84, project to BNG for buffering in metres, then back
        poly_gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")
        poly_buffered = poly_gdf.to_crs("EPSG:27700").buffer(buffer_m)
        poly_buffered_wgs84 = gpd.GeoDataFrame(geometry=poly_buffered).set_crs("EPSG:27700").to_crs("EPSG:4326")
        points_inside = gpd.sjoin(all_points, poly_buffered_wgs84, predicate="within", how="inner")
    except Exception as e:
        log.warning(f"[filter_points_for_waterbody] sjoin failed ({e}); falling back to within()")
        points_inside = all_points[all_points.within(poly)]

    log.info(f"[filter_points_for_waterbody] {len(points_inside)} point(s) inside {wb_name}")
    return points_inside
