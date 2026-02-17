# d - GEOSPATIAL LOGIC

from typing import Tuple, Optional
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon

from .b_utils import haversine_km
from .a_config import RADIUS_BUFFER_KM, MAX_RADIUS_KM


def representative_point(poly) -> Tuple[float, float]:
    """
    Return a guaranteed-inside representative point (lat, lon) for a polygon.
    """
    pt = poly.representative_point()
    return float(pt.y), float(pt.x)  # lat, lon


def max_distance_to_boundary(poly, lat: float, lon: float) -> float:
    """
    Compute the maximum haversine distance (km) from a point to the polygon boundary.
    Handles both Polygon and MultiPolygon.
    """
    maxd = 0.0

    # Normalise to list of polygons
    if isinstance(poly, Polygon):
        parts = [poly]
    elif isinstance(poly, MultiPolygon):
        parts = list(poly.geoms)
    else:
        return 0.0

    for part in parts:
        try:
            coords = list(part.exterior.coords)
        except Exception:
            continue

        for lon_b, lat_b in coords:
            d = haversine_km(lon, lat, lon_b, lat_b)
            if d > maxd:
                maxd = d

    return maxd


def compute_query_radius(poly, rep_pt=None) -> float:
    """
    Compute the dynamic radius for EA site discovery:
    - representative point inside polygon (unless provided)
    - max distance to boundary
    - add buffer
    - cap to MAX_RADIUS_KM

    This restores the old behaviour where the caller may pass rep_pt.
    """
    # Old script allowed passing rep_pt externally
    if rep_pt is None:
        lat, lon = representative_point(poly)
    else:
        lat, lon = float(rep_pt.y), float(rep_pt.x)

    maxd = max_distance_to_boundary(poly, lat, lon)
    radius = min(maxd + RADIUS_BUFFER_KM, MAX_RADIUS_KM)
    return radius