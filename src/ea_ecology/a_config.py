from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# REPO ROOT (ecology-specific version)
# ---------------------------------------------------------

# This file lives in: <repo>/src/ea_ecology/a_config.py
# So repo root is three levels up.
REPO_BASE = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------
# FILE PATHS (ecology-specific)
# ---------------------------------------------------------

CATCHMENT_SHP = REPO_BASE / "data" / "gis" / "thames21_scorecard_waterbodies.shp"

if not CATCHMENT_SHP.exists():
    raise FileNotFoundError(
        f"Catchment shapefile not found at:\n{CATCHMENT_SHP}\n"
        "Expected location: data/gis/"
    )

OUT_DIR = REPO_BASE / "data" / "output" / "ea_ecology"
TMP_DIR = OUT_DIR / "_tmp"

OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# ECOLOGY API CONFIG
# ---------------------------------------------------------

BASE_URL = "https://environment.data.gov.uk/ecology/api/v1"

# Ecology-specific batching and timing
BATCH_SIZE = 10
PAGINATION_SLEEP = 1.0
SITE_FETCH_PAUSE = 2.0
BATCH_PAUSE = 2.0
PER_SITE_PAUSE = 1.5

DRY_RUN = False
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M")

# ---------------------------------------------------------
# ECOLOGY GROUPS
# ---------------------------------------------------------

GROUPS = [
    "invertebrates_metrics",
    "invertebrates_taxa",
    "diatoms",
    "macrophytes_taxa",
    "fresh_fish_taxa",
]

PIVOTABLE_GROUPS = [
    "invertebrates_metrics",
    "diatoms",
    "macrophytes_taxa",
    "fresh_fish_taxa",
]

SELECTED_GROUPS = [
    "diatoms",
    "invertebrates_taxa",
    "invertebrates_metrics",
    "macrophytes_taxa",
    "fresh_fish_taxa",
]

# ---------------------------------------------------------
# OBSERVATION TYPES
# ---------------------------------------------------------

OBS_TYPES = {
    "diatoms": "http://environment.data.gov.uk/ecology/def/bio/RiverDiatTaxaObservation",
    "invertebrates_taxa": "http://environment.data.gov.uk/ecology/def/bio/RiverInvTaxaObservation",
    "invertebrates_metrics": "http://environment.data.gov.uk/ecology/def/bio/RiverInvMetricsObservation",
    "fresh_fish_taxa": "http://environment.data.gov.uk/ecology/def/fish/FreshwaterFishSpeciesObservation",
    "macrophytes_taxa": "http://environment.data.gov.uk/ecology/def/bio/RiverMacpTaxaObservation",
}

# ---------------------------------------------------------
# LABEL FIELDS
# ---------------------------------------------------------

LABEL_FIELDS = {
    "invertebrates_metrics": "property_label",
    "fresh_fish_taxa": "ultimate_feature_of_interest_label",
}