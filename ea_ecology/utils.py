import re
from math import radians, sin, cos, atan2, sqrt


def _safe_name(s: object) -> str:
    if s is None:
        return "unknown"
    s = str(s)
    s = re.sub(r"[^A-Za-z0-9\-_]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_-")
    return s[:180]


def haversine_km(lon1, lat1, lon2, lat2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return 6371.0 * c
