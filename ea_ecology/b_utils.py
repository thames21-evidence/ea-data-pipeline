# b - UTILITIES

import re
from math import radians, sin, cos, atan2, sqrt


def _safe_name(value: object) -> str:
    """
    Convert any string-like value into a filesystem-safe name.

    - Non-alphanumeric characters become underscores
    - Multiple underscores collapse into one
    - Leading/trailing underscores and hyphens are removed
    - Length capped at 180 characters
    """
    if value is None:
        return "unknown"

    s = str(value)
    s = re.sub(r"[^A-Za-z0-9\-_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_-")
    return s[:180]


def haversine_km(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Compute the great-circle distance between two lat/long points in kilometres.
    """
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return 6371.0 * c