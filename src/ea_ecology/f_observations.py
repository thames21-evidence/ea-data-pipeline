# f - OBSERVATION FETCHING

from typing import List, Dict, Any
import time

from .c_api import fetch_all
from .a_config import (
    BATCH_SIZE,
    BATCH_PAUSE,
    PER_SITE_PAUSE,
    OBS_TYPES,
    LABEL_FIELDS,
)


def fetch_observations_for_group(
    group: str,
    sites_inside,
    wb_name: str,
) -> List[Dict[str, Any]]:

    if group not in OBS_TYPES:
        print(f"Unknown group '{group}', skipping")
        return []

    obs_type_uri = OBS_TYPES[group]
    label_field = LABEL_FIELDS.get(group, "label")

    # Extract site IDs and labels
    site_ids = list(sites_inside["site_id"])
    site_labels = dict(zip(sites_inside["site_id"], sites_inside["label"]))

    # Build lookup table for enrichment fields
    site_attrs = sites_inside.set_index("site_id")

    raw_rows: List[Dict[str, Any]] = []

    # --- Batch requests -------------------------------------------------------
    for i in range(0, len(site_ids), BATCH_SIZE):
        batch = site_ids[i : i + BATCH_SIZE]

        try:
            items = fetch_all(
                "observations",
                params={
                    "site_id": batch,
                    "type_id": obs_type_uri,
                },
            )
        except Exception as e:
            print(f"Batch error for group={group} batch={batch}: {e}")
            items = []

        # ----------------------------------------------------------------------
        # FALLBACK: Per-site requests
        # ----------------------------------------------------------------------
        if not items:
            for sid in batch:
                try:
                    per_items = fetch_all(
                        "observations",
                        params={
                            "site_id": sid,
                            "type_id": obs_type_uri,
                        },
                    )
                except Exception as e:
                    print(f"Per-site error for {sid}: {e}")
                    per_items = []

                for row in per_items:
                    row["group"] = group
                    row["waterbody"] = wb_name
                    row["site_id"] = sid
                    row["site_label"] = site_labels.get(sid)

                    # --- ADD ENRICHMENT FIELDS ---
                    for col in ["lat", "long", "CaBA_Catch", "WB_NAME"]:
                        try:
                            row[col] = site_attrs.loc[sid, col]
                        except KeyError:
                            row[col] = None

                    raw_rows.append(row)

                time.sleep(PER_SITE_PAUSE)

        # ----------------------------------------------------------------------
        # NORMAL BATCH BRANCH
        # ----------------------------------------------------------------------
        else:
            for row in items:
                sid = row.get("site_id")
                row["group"] = group
                row["waterbody"] = wb_name
                row["site_id"] = sid
                row["site_label"] = site_labels.get(sid)

                # --- ADD ENRICHMENT FIELDS ---
                for col in ["lat", "long", "CaBA_Catch", "WB_NAME"]:
                    try:
                        row[col] = site_attrs.loc[sid, col]
                    except KeyError:
                        row[col] = None

                raw_rows.append(row)

        time.sleep(BATCH_PAUSE)

    return raw_rows