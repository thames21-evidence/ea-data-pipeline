# j - PIVOTING
#
# Pivots water quality measurements into wide format.
# Each determinand becomes a column; rows are keyed by sampling point + date.

import pandas as pd
from pathlib import Path
from .a_config import OUT_DIR, SELECTED_DETERMINANDS
from .b_utils import _safe_name


# ---------------------------------------------------------
# 1. PIVOT A SINGLE DETERMINAND FOR A SINGLE CATCHMENT
# ---------------------------------------------------------

def pivot_determinand(df: pd.DataFrame, determinand: str) -> pd.DataFrame:
    """
    Pivot water quality measurements for one determinand into wide format.
    Result columns: index fields + one column per determinand label value.
    """

    if df is None or df.empty:
        return pd.DataFrame()

    # Drop rows with no result
    df = df[pd.to_numeric(df["result"], errors="coerce").notnull()].copy()
    df["result"] = df["result"].astype(float)

    if df.empty:
        return pd.DataFrame()

    index_cols = [
        c for c in ["notation", "point_label", "date", "waterbody", "determinand",
                    "unit", "lat", "long"]
        if c in df.columns
    ]

    if not index_cols:
        return pd.DataFrame()

    # For water quality, the natural wide format has one row per
    # (sampling point, date) and one column per determinand.
    # At the single-determinand stage we just return cleaned long format;
    # collation across determinands produces the wide pivot.
    return df[index_cols + ["result"]].reset_index(drop=True)


# ---------------------------------------------------------
# 2. THAMES-WIDE COLLATION INTO WIDE FORMAT
# ---------------------------------------------------------

def collate_pivot_determinand(determinand: str):
    """
    Combine all raw CSVs for a given determinand into one Thames21-wide CSV.
    """
    out_path = OUT_DIR / f"thames21_{determinand}.csv"
    files = list(OUT_DIR.glob(f"*__{determinand}__raw_*.csv"))

    if not files:
        print(f"[collate_pivot_determinand] No files found for determinand {determinand}")
        return None

    frames = [pd.read_csv(f) for f in files]
    combined = pd.concat(frames, ignore_index=True).drop_duplicates()
    combined.to_csv(out_path, index=False)
    print(f"[collate_pivot_determinand] Saved Thames21-wide → {out_path.name}")
    return out_path


def collate_wide():
    """
    Collate all determinands and produce one wide pivot table keyed by
    (notation, point_label, date, waterbody, lat, long).
    """
    frames = []

    for det in SELECTED_DETERMINANDS:
        files = list(OUT_DIR.glob(f"*__{det}__raw_*.csv"))
        for f in files:
            df = pd.read_csv(f)
            if not df.empty and "result" in df.columns:
                df = df.rename(columns={"result": det})
                frames.append(df)

    if not frames:
        print("[collate_wide] No data found.")
        return None

    combined = pd.concat(frames, ignore_index=True)

    index_cols = [c for c in ["notation", "point_label", "date", "waterbody", "lat", "long"]
                  if c in combined.columns]

    wide = combined.groupby(index_cols, as_index=False)[SELECTED_DETERMINANDS].first()

    out_path = OUT_DIR / "thames21_waterquality_wide.csv"
    wide.to_csv(out_path, index=False)
    print(f"[collate_wide] Saved wide pivot → {out_path.name}")
    return out_path


def collate_catchment(catchment_name: str, wb_names: list):
    """
    Collate all waterbody CSVs for a given catchment into one file per determinand.
    """
    safe_catch = _safe_name(catchment_name)

    for det in SELECTED_DETERMINANDS:
        frames = []
        for wb_name in wb_names:
            safe_wb = _safe_name(wb_name)
            for f in OUT_DIR.glob(f"{safe_wb}__{det}__raw_*.csv"):
                frames.append(pd.read_csv(f))

        if not frames:
            continue

        combined = pd.concat(frames, ignore_index=True).drop_duplicates()
        out_path = OUT_DIR / f"{safe_catch}__{det}.csv"
        combined.to_csv(out_path, index=False)
        print(f"[collate_catchment] {catchment_name} / {det} → {out_path.name}")


def collate_all_pivots():
    print("\n=== Collating Thames21-wide water quality outputs ===\n")
    for det in SELECTED_DETERMINANDS:
        collate_pivot_determinand(det)
    collate_wide()
    print("\n=== Done ===\n")
