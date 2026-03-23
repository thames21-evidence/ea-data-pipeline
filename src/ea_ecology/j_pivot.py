# j_pivot.py
#
# Universal pivoting logic for harmonised EA ecology datasets.
# This expects the output from your aggregation step,
# where columns like simple_result, date, site_label, waterbody, etc. exist.

import pandas as pd
from pathlib import Path
from .a_config import OUT_DIR


# ---------------------------------------------------------
# 0. FILTERING LOGIC FOR EACH GROUP
# ---------------------------------------------------------

def filter_for_pivot(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """
    Keep only the numeric abundance/metric rows needed for pivoting.
    Raw tables still contain everything; this only affects the pivot.
    """

    # -----------------------------
    # Invertebrate abundance (taxa)
    # -----------------------------
    if group == "invertebrates_taxa":
        return df[df["property_label"] == "TOTAL_ABUNDANCE"]

    # -----------------------------
    # Fish abundance (taxa)
    # -----------------------------
    if group == "fresh_fish_taxa":
        df = df.copy()

        # 1. Convert presence/absence to 1
        df.loc[
            df["simple_result"].astype(str).str.contains("Present", case=False, na=False),
            "simple_result"
        ] = 1

        # 2. Convert abundance ranges like "10 to 99 [Best Run]" → 10
        mask_range = df["simple_result"].astype(str).str.contains("to", case=False, na=False)
        df.loc[mask_range, "simple_result"] = (
            df.loc[mask_range, "simple_result"]
            .astype(str)
            .str.extract(r"(\d+)\s*to")[0]   # extract the first number
            .astype(float)
        )

        # 3. Keep only rows where simple_result is numeric
        df = df[pd.to_numeric(df["simple_result"], errors="coerce").notnull()]

        # 4. Convert to float
        df["simple_result"] = df["simple_result"].astype(float)

        return df

    # -----------------------------
    # Diatoms (cover band)
    # -----------------------------
    if group == "diatoms_taxa":
        return df[df["property_label"] == "PERCENTAGE_COVER_BAND"]

    # -----------------------------
    # Invertebrate metrics
    # -----------------------------
    if group == "invertebrates_metrics":
        return df

    # -----------------------------
    # Default: keep everything (macrophytes etc.)
    # -----------------------------
    return df


# ---------------------------------------------------------
# 1. PIVOT A SINGLE GROUP FOR A SINGLE CATCHMENT
# ---------------------------------------------------------

def pivot_group(df: pd.DataFrame, group: str) -> pd.DataFrame:
    """
    Pivot EA ecology observations into wide format.
    Works with raw EA API schema (simple_result + taxon/metric label).
    """

    if df is None or df.empty:
        return pd.DataFrame()

    # Apply group-specific filtering
    df = filter_for_pivot(df, group)

    if df.empty:
        return pd.DataFrame()

    # Detect the label column (taxon or metric)
    if group == "invertebrates_metrics":
        # Metrics ALWAYS use observed_property_label
        label_col = "property_label"
    else:
        # Taxa groups use the taxon label
        label_col = next(
            (
                c
                for c in [
                    "ultimate_feature_of_interest_label",  # taxon (inverts, diatoms, fish)
                    "observed_property_label",             # metric name (diatoms/macrophytes)
                ]
                if c in df.columns
            ),
            None,
        )

    if label_col is None:
        return pd.DataFrame()

    # Build "Latin (English)" combined label for column headers
    if label_col == "ultimate_feature_of_interest_label" and "common_name" in df.columns:
        df = df.copy()
        df["_pivot_label"] = df.apply(
            lambda r: f"{r[label_col]} ({r['common_name']})" if r.get("common_name") else r[label_col],
            axis=1,
        )
        label_col = "_pivot_label"

    # Index columns
    index_cols = [
        c
        for c in ["site_id", "site_label", "date", "waterbody", "group", "lat", "long",]
        if c in df.columns
    ]

    if not index_cols:
        return pd.DataFrame()

    # Pivot: taxon/metric becomes columns, numeric values become values
    pivot = df.pivot_table(
        index=index_cols,
        columns=label_col,
        values="simple_result",
        aggfunc="first",
        fill_value= 0 
    ).reset_index()

    # Flatten column names
    pivot.columns = [str(c) for c in pivot.columns]

    return pivot


# ---------------------------------------------------------
# 2. THAMES-WIDE COLLATION OF PIVOT FILES
# ---------------------------------------------------------

def collate_pivot_group(group: str):
    """
    Combine all pivot files for a given group into one Thames21-wide CSV.
    """
    pivot_dir = OUT_DIR / "_pivot"
    out_path = OUT_DIR / f"thames21_{group}.csv"

    files = list(pivot_dir.glob(f"*__{group}__pivot_*.csv"))
    if not files:
        print(f"[collate_pivot_group] No pivot files found for group {group}")
        return None

    frames = []
    for f in files:
        df = pd.read_csv(f)
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True).drop_duplicates()
    combined = combined.fillna(0)
    combined.to_csv(out_path, index=False)

    print(f"[collate_pivot_group] ✓ Saved Thames21-wide pivot → {out_path.name}")
    return out_path


from ea_ecology.a_config import SELECTED_GROUPS

def collate_all_pivots():
    print("\n=== Collating Thames21-wide pivot outputs ===\n")

    for g in SELECTED_GROUPS:
        collate_pivot_group(g)

    print("\n=== ✓ All Thames21-wide pivot outputs created ===\n")