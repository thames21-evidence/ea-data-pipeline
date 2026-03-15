# a - GEOSPATIAL LOGIC

from pathlib import Path

# Repo base
REPO_BASE = Path(__file__).resolve().parents[2]

# Shared geospatial constants
RADIUS_BUFFER_KM = 1.0
MAX_RADIUS_KM = 500.0

# Optional: shared output base
OUTPUT_BASE = REPO_BASE / "data" / "output"