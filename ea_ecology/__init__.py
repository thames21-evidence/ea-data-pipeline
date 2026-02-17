"""ea_ecology package: small helpers for the EA ecology ingestion scripts.

This package contains lightweight API and spatial helpers. The main
script imports these helpers so the implementation is easier to test and
reuse.
"""
from .api import fetch_json, fetch_all, safe_save, get_session
from .utils import _safe_name, haversine_km

__all__ = ["fetch_json", "fetch_all", "safe_save", "get_session", "_safe_name", "haversine_km"]
