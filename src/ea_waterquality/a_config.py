from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# REPO ROOT
# ---------------------------------------------------------

# This file lives in: <repo>/src/ea_waterquality/a_config.py
# So repo root is three levels up.
REPO_BASE = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------
# FILE PATHS (water-quality-specific)
# ---------------------------------------------------------

CATCHMENT_SHP = REPO_BASE / "data" / "gis" / "thames21_scorecard_waterbodies.shp"

if not CATCHMENT_SHP.exists():
    raise FileNotFoundError(
        f"Catchment shapefile not found at:\n{CATCHMENT_SHP}\n"
        "Expected location: data/gis/"
    )

OUT_DIR = REPO_BASE / "data" / "output" / "ea_waterquality"
TMP_DIR = OUT_DIR / "_tmp"

OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# WATER QUALITY API CONFIG
# ---------------------------------------------------------

BASE_URL = "https://environment.data.gov.uk/water-quality"

# Region code for sampling point discovery (confirmed from API responses)
REGION = "TH"  # Thames

# API behaviour
BATCH_SIZE = 10
PAGE_SIZE = 500  # API likely caps below 2000; use safe value
PAGINATION_SLEEP = 1.0
POINT_FETCH_PAUSE = 1.5
OBSERVATION_PAUSE = 1.0

DRY_RUN = False
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M")

# ---------------------------------------------------------
# DATE RANGE FOR MEASUREMENTS
# ---------------------------------------------------------

START_DATE = "2000-01-01"
END_DATE = datetime.now().strftime("%Y-%m-%d")

# ---------------------------------------------------------
# DETERMINANDS OF INTEREST
# ---------------------------------------------------------

# EA Water Quality Archive notation codes (4-digit strings).
# Full list: https://environment.data.gov.uk/water-quality/api/def/determinand
DETERMINANDS = {
    "phosphate":           "0180",  # Orthophosphate reactive as P
    "ammonia":             "0111",  # Ammoniacal nitrogen as N
    "nitrate":             "0116",  # Nitrate as N
    "nitrite":             "0117",  # Nitrite as N
    "dissolved_oxygen":    "0009",  # Dissolved oxygen
    "bod":                 "0077",  # BOD ATU
    "suspended_solids":    "0135",  # Suspended solids
    "ph":                  "0082",  # pH
    "conductivity":        "0061",  # Conductivity at 25C
    "temperature":         "0076",  # Temperature of water
}

SELECTED_DETERMINANDS = ["ammonia", "phosphate"]  # 0111, 0180
