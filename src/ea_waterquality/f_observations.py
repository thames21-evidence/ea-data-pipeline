# f - MEASUREMENT FETCHING

from typing import List, Dict, Any
import time

from .c_api import fetch_all
from .a_config import (
    BATCH_SIZE,
    OBSERVATION_PAUSE,
    DETERMINANDS,
    START_DATE,
    END_DATE,
    PAGE_SIZE,
    PAGINATION_SLEEP,
)


def fetch_measurements_for_determinand(
    determinand_name: str,
    points_inside,
    wb_name: str,
) -> List[Dict[str, Any]]:
    """
    Fetch all measurements for a given determinand across all sampling points.
    Each row is enriched with waterbody name, sampling point label, and coordinates.
    """

    if determinand_name not in DETERMINANDS:
        print(f"Unknown determinand '{determinand_name}', skipping")
        return []

    det_notation = DETERMINANDS[determinand_name]

    # Build lookup tables
    notations = list(points_inside["notation"])
    point_labels = dict(zip(points_inside["notation"], points_inside["label"]))
    point_attrs = points_inside.set_index("notation")

    raw_rows: List[Dict[str, Any]] = []

    for i in range(0, len(notations), BATCH_SIZE):
        batch = notations[i : i + BATCH_SIZE]

        for notation in batch:
            try:
                items = fetch_all(
                    f"sampling-point/{notation}/observation",
                    params={
                        "determinand": int(det_notation),
                        "dateFrom": START_DATE,
                        "dateTo": END_DATE,
                    },
                    page_size=PAGE_SIZE,
                    pagination_sleep=PAGINATION_SLEEP,
                )
            except Exception as e:
                print(f"Error fetching measurements for {notation} / {determinand_name}: {e}")
                items = []

            for item in items:
                row: Dict[str, Any] = {
                    "determinand":        determinand_name,
                    "determinand_code":   det_notation,
                    "waterbody":          wb_name,
                    "notation":           notation,
                    "point_label":        point_labels.get(notation),
                    "date":               _extract_date(item),
                    "result":             _extract_result(item),
                    "unit":               _extract_unit(item),
                    "determinand_label":  _extract_determinand_label(item),
                }

                # Enrich with spatial attributes
                for col in ["lat", "long"]:
                    try:
                        row[col] = point_attrs.loc[notation, col]
                    except KeyError:
                        row[col] = None

                raw_rows.append(row)

            time.sleep(OBSERVATION_PAUSE)

    return raw_rows


# ---------------------------------------------------------
# FIELD EXTRACTORS
# ---------------------------------------------------------

def _extract_date(item: Dict[str, Any]) -> str:
    # API returns ISO datetime in "phenomenonTime" e.g. "2020-03-05T08:52:00"
    dt = item.get("phenomenonTime", "")
    return str(dt)[:10] if dt else ""


def _extract_result(item: Dict[str, Any]) -> Any:
    # API returns the numeric value as a string in "hasSimpleResult"
    result = item.get("hasSimpleResult")
    if result is None:
        return None
    try:
        return float(result)
    except (TypeError, ValueError):
        return result


def _extract_unit(item: Dict[str, Any]) -> str:
    # API returns unit label directly in "hasUnit" e.g. "mg/l"
    return str(item.get("hasUnit", ""))


def _extract_determinand_label(item: Dict[str, Any]) -> str:
    # observedProperty may hold the determinand label; fall back to empty string
    prop = item.get("observedProperty", {})
    if isinstance(prop, dict):
        return prop.get("label", "") or prop.get("prefLabel", "")
    return ""
