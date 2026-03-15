from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------
# REPO ROOT
# ---------------------------------------------------------

REPO_BASE = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------
# FILE PATHS (water-quality-specific)
# ---------------------------------------------------------

OUT_DIR = REPO_BASE / "data" / "output" / "ea_waterquality"
TMP_DIR = OUT_DIR / "_tmp"

OUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# WATER QUALITY API CONFIG
# ---------------------------------------------------------

BASE_URL = "https://environment.data.gov.uk/water-quality"

# API behaviour
BATCH_SIZE = 10
PAGINATION_SLEEP = 1.0
POINT_FETCH_PAUSE = 1.5
OBSERVATION_PAUSE = 1.0

DRY_RUN = False
TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H%M")

