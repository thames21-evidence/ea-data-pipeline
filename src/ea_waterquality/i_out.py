# i - OUTPUT WRITING

from pathlib import Path
import pandas as pd

from .b_utils import _safe_name
from .a_config import OUT_DIR, TIMESTAMP


def catchment_output_path(catch_name: str) -> Path:
    safe = _safe_name(catch_name)
    return OUT_DIR / f"{safe}__raw_{TIMESTAMP}.csv"


def save_catchment_output(df: pd.DataFrame, catch_name: str) -> Path:
    path = catchment_output_path(catch_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    if df is None or df.empty:
        print(f"No data for {catch_name}, skipping save")
        return path

    try:
        df.to_csv(path, index=False)
        print(f"Saved output: {path.name}")
    except Exception as e:
        print(f"Error saving output {path}: {e}")

    return path
