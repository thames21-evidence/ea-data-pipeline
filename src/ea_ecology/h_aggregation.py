# h - AGGREGATION

import pandas as pd
from .k_species_names import get_common_names

TAXA_COL = "ultimate_feature_of_interest_label"


def rows_to_dataframe(rows):
    # Nothing returned
    if rows is None:
        return pd.DataFrame()

    # Already a DataFrame
    if isinstance(rows, pd.DataFrame):
        return rows

    # List of dicts (normal case)
    if isinstance(rows, list):
        if len(rows) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(rows)

        # Add common_name column immediately after the Latin name column
        if TAXA_COL in df.columns:
            names = df[TAXA_COL].dropna().unique().tolist()
            lookup = get_common_names(names)
            idx = df.columns.get_loc(TAXA_COL) + 1
            df.insert(idx, "common_name", df[TAXA_COL].map(lookup).fillna(""))

        return df

    # Fallback
    return pd.DataFrame()