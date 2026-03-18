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
        df = pd.DataFrame(rows)
        if "result" in df.columns:
            idx = df.columns.get_loc("result") + 1
            numeric = pd.to_numeric(
                df["result"].astype(str).str.replace(r"^[<>]\s*", "", regex=True),
                errors="coerce",
            )
            df.insert(idx, "result_numeric", numeric)
        return df

    return pd.DataFrame()
