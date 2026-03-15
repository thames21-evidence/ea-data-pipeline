"""
Fetch EA Water Quality compliance data for a geographic area.

Data source: https://environment.data.gov.uk/water-quality/

CONFIG section at the top — set your area centre, radius, and date range.
Outputs:
  data/output/water_quality/sampling_points_<timestamp>.csv
  data/output/water_quality/water_quality_compliance_<timestamp>.csv
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# ── CONFIG ────────────────────────────────────────────────────────────────────

# Centre of area (decimal degrees, WGS84)
LAT = 51.5
LON = -0.1
DIST_KM = 20  # search radius in km

START_DATE = "2015-01-01"
END_DATE = "2025-01-01"

# CS = Compliance, RO = Routine monitoring, set to None to fetch all purposes
SAMPLING_PURPOSE = "CS"

# ── PATHS ─────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "output" / "water_quality"

WQ_BASE = "https://environment.data.gov.uk/water-quality"
PAGE_SIZE = 500
PAUSE = 0.5  # seconds between requests

# ── API HELPERS ───────────────────────────────────────────────────────────────

_session = requests.Session()


def _get(url, params=None, max_retries=5):
    backoff = 1.0
    for attempt in range(max_retries):
        try:
            r = _session.get(url, params=params, timeout=30)
            if r.status_code in (429, 500, 502, 503, 504):
                print(f"  HTTP {r.status_code} — backing off {backoff:.0f}s")
                time.sleep(backoff)
                backoff *= 2
                continue
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            print(f"  Request error (attempt {attempt + 1}/{max_retries}): {e}")
            time.sleep(backoff)
            backoff *= 2
    return {}


def fetch_sampling_points(lat, lon, dist_km):
    """Return all sampling point items within dist_km of lat/lon."""
    data = _get(
        f"{WQ_BASE}/id/sampling-points",
        params={"latLong": f"{lat},{lon}", "dist": dist_km},
    )
    items = data.get("items", [])
    print(f"Found {len(items)} sampling points within {dist_km} km of ({lat}, {lon})")
    return items


def fetch_measurements(notation, start_date, end_date, sampling_purpose=None):
    """Fetch all paginated measurement observations for one sampling point."""
    params = {
        "samplingPoint": notation,
        "startdate": start_date,
        "enddate": end_date,
        "_limit": PAGE_SIZE,
        "_offset": 0,
    }
    if sampling_purpose:
        params["samplingPurpose"] = sampling_purpose

    all_items = []
    while True:
        data = _get(f"{WQ_BASE}/data/measurement", params=params.copy())
        items = data.get("items", [])
        all_items.extend(items)
        if len(items) < PAGE_SIZE:
            break
        params["_offset"] += PAGE_SIZE
        time.sleep(PAUSE)

    return all_items


# ── PARSING ───────────────────────────────────────────────────────────────────

def _wkt_bng_to_easting_northing(wkt):
    """Parse 'POINT(490739 288855) <...27700>' → (easting, northing)."""
    if not wkt:
        return None, None
    m = re.match(r"POINT\(([0-9.]+)\s+([0-9.]+)\)", str(wkt))
    if m:
        return float(m.group(1)), float(m.group(2))
    return None, None


def parse_observation(obs):
    """Flatten a sosa:Observation dict into a plain row dict."""
    sp = obs.get("hasSamplingPoint") or {}
    result = obs.get("hasResult") or {}
    prop = obs.get("observedProperty") or {}
    unit_obj = result.get("hasUnit") or {}
    sample = obs.get("hasSample") or {}
    mat = sample.get("sampleMaterialType") or {}
    sampling_event = sample.get("isResultOf") or {}
    purpose = sampling_event.get("samplingPurpose") or {}
    geom = sp.get("geometry") or {}

    easting, northing = _wkt_bng_to_easting_northing(geom.get("asWKT"))

    return {
        "observation_id": obs.get("id"),
        "sampling_point": sp.get("notation"),
        "sampling_point_label": sp.get("prefLabel") or sp.get("label"),
        "easting_bng": easting,
        "northing_bng": northing,
        "region": (sp.get("region") or {}).get("notation"),
        "region_label": (sp.get("region") or {}).get("prefLabel"),
        "area": (sp.get("area") or {}).get("notation"),
        "sampling_point_type": (sp.get("samplingPointType") or {}).get("notation"),
        "sampling_point_type_label": (sp.get("samplingPointType") or {}).get("prefLabel"),
        "phenomenon_time": obs.get("phenomenonTime"),
        "determinand_notation": prop.get("notation"),
        "determinand_label": prop.get("prefLabel"),
        "determinand_alt_label": prop.get("altLabel"),
        # hasSimpleResult is the raw string e.g. "<0.231" or "7"
        "result_string": obs.get("hasSimpleResult"),
        # Structured result — numericValue is null when value is a bound
        "result_numeric": result.get("numericValue"),
        "result_upper_bound": result.get("upperBound"),
        "result_lower_bound": result.get("lowerBound"),
        "unit": unit_obj.get("altLabel") or obs.get("hasUnit"),
        "sample_material": mat.get("prefLabel"),
        "sampling_purpose": purpose.get("notation"),
        "sampling_purpose_label": purpose.get("prefLabel"),
    }


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")

    # ── 1. Discover sampling points ──────────────────────────────────────────
    points = fetch_sampling_points(LAT, LON, DIST_KM)
    if not points:
        print("No sampling points found — check LAT, LON, DIST_KM in the config.")
        sys.exit(1)

    sp_df = pd.DataFrame(points)
    sp_path = OUT_DIR / f"sampling_points_{timestamp}.csv"
    sp_df.to_csv(sp_path, index=False)
    print(f"Saved {len(sp_df)} sampling points → {sp_path.name}\n")

    # ── 2. Fetch observations for each point ─────────────────────────────────
    all_rows = []
    for i, point in enumerate(points, 1):
        notation = point.get("notation")
        label = point.get("label") or point.get("prefLabel") or notation
        if not notation:
            continue

        print(f"[{i}/{len(points)}] {notation}  ({label})")
        obs_items = fetch_measurements(notation, START_DATE, END_DATE, SAMPLING_PURPOSE)
        print(f"  → {len(obs_items)} observations")

        for o in obs_items:
            all_rows.append(parse_observation(o))

        time.sleep(PAUSE)

    if not all_rows:
        print("\nNo observations returned — the area may have no compliance data in that date range.")
        sys.exit(0)

    df = pd.DataFrame(all_rows)

    # Sort by site then time for readability
    if "phenomenon_time" in df.columns:
        df = df.sort_values(["sampling_point", "phenomenon_time"])

    out_path = OUT_DIR / f"water_quality_compliance_{timestamp}.csv"
    df.to_csv(out_path, index=False)

    print(f"\n{'─' * 60}")
    print(f"Saved {len(df):,} observations → {out_path}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSample rows:")
    preview_cols = ["sampling_point", "phenomenon_time", "determinand_label", "result_string", "unit"]
    print(df[preview_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
