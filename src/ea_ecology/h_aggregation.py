# h - AGGREGATION

from typing import List, Dict, Any
import pandas as pd


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
        return pd.DataFrame(rows)

    # Fallback
    return pd.DataFrame()