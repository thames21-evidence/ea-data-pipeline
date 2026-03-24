"""
Upload Thames21 output CSVs to ArcGIS Online.

Lists all thames21_*.csv files across the data/output directories, lets you
choose which ones to upload, and overwrites any item that already exists on
your account with the same title.

Usage:
    python scripts/upload_to_arcgis.py
"""

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parents[1] / "src"))

from arcgis.gis import GIS

# ------------------------------------------------------------------ #
# Config
# ------------------------------------------------------------------ #

REPO_ROOT = pathlib.Path(__file__).parents[1]

OUTPUT_DIRS = [
    REPO_ROOT / "data" / "output" / "ea_ecology",
    REPO_ROOT / "data" / "output" / "ea_waterquality",
]

# ------------------------------------------------------------------ #
# Connect
# ------------------------------------------------------------------ #

# 'profile' saves credentials locally after the first OAuth login.
# Subsequent runs load from the saved profile — no browser popup needed.
gis = GIS(
    "https://theriverstrust.maps.arcgis.com",
    client_id="QqCukKbHG8MFzv3Q",
    redirect_uri="http://localhost:8888",
    profile="thames21",
)
print(f"Connected as: {gis.users.me}\n")

# ------------------------------------------------------------------ #
# Discover files
# ------------------------------------------------------------------ #

files = []
for d in OUTPUT_DIRS:
    files.extend(sorted(d.glob("thames21_*.csv")))

if not files:
    print("No thames21_*.csv files found in output directories.")
    sys.exit(0)

print("Available files:")
for i, f in enumerate(files, 1):
    print(f"  [{i}] {f.name}  ({f.parent.name})")

print()

# ------------------------------------------------------------------ #
# Selection
# ------------------------------------------------------------------ #

raw = input("Enter numbers to upload (comma-separated), or 'all': ").strip()

if raw.lower() == "all":
    selected = files
else:
    try:
        indices = [int(x.strip()) for x in raw.split(",")]
        selected = [files[i - 1] for i in indices]
    except (ValueError, IndexError):
        print("Invalid selection.")
        sys.exit(1)

if not selected:
    print("Nothing selected.")
    sys.exit(0)

print()

# ------------------------------------------------------------------ #
# Upload / overwrite
# ------------------------------------------------------------------ #

me = gis.users.me.username

for path in selected:
    title = path.stem          # e.g. "thames21_diatoms"
    print(f"Uploading: {path.name} → '{title}'")

    # --- 1. Add or update the source CSV item ---
    existing_csv = gis.content.search(
        query=f'title:"{title}" AND owner:{me}',
        item_type="CSV",
        max_items=5,
    )
    existing_csv = [i for i in existing_csv if i.title == title]

    if existing_csv:
        csv_item = existing_csv[0]
        csv_item.update(data=str(path))
        print(f"  ✓ CSV updated (id={csv_item.id})")
    else:
        csv_item = gis.content.add(
            item_properties={
                "title": title,
                "type": "CSV",
                "tags": "thames21,water-quality,ecology",
            },
            data=str(path),
        )
        print(f"  ✓ CSV created (id={csv_item.id})")

    # --- 2. Publish (or overwrite) as a hosted feature layer ---
    fl_item = csv_item.publish(overwrite=True)
    print(f"  ✓ Feature layer: {fl_item.title} (id={fl_item.id})")

print("\nDone.")
