# i - OUTPUT WRITING

from pathlib import Path
import pandas as pd

from .b_utils import _safe_name
from .a_config import OUT_DIR, TIMESTAMP


def output_path(wb_name: str, group: str) -> Path:
    """
    Build the final output CSV path for a given waterbody + group.
    """
    safe_wb = _safe_name(wb_name)
    safe_group = _safe_name(group)
    filename = f"{safe_wb}__{safe_group}__raw_{TIMESTAMP}.csv"
    return OUT_DIR / filename


def save_output(df: pd.DataFrame, wb_name: str, group: str) -> Path:
    """
    Save the final DataFrame for a waterbody + group.
    Returns the path to the saved file.
    """
    path = output_path(wb_name, group)
    path.parent.mkdir(parents=True, exist_ok=True)

    if df is None or df.empty:
        print(f"No data for {wb_name} / {group}, skipping save")
        return path

    try:
        df.to_csv(path, index=False)
        print(f"Saved output: {path.name}")
    except Exception as e:
        print(f"Error saving output {path}: {e}")

    return path