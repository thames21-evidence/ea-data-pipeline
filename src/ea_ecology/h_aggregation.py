# h - AGGREGATION

import pandas as pd


def rows_to_dataframe(rows):
    if rows is None:
        return pd.DataFrame()
    if isinstance(rows, pd.DataFrame):
        return rows
    if isinstance(rows, list):
        if len(rows) == 0:
            return pd.DataFrame()
        return pd.DataFrame(rows)
    return pd.DataFrame()