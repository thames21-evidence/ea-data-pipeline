# i - OUTPUT WRITING

from pathlib import Path
import pandas as pd

from .b_utils import _safe_name
from .a_config import OUT_DIR, TIMESTAMP


def output_path(wb_name: str, determinand: str) -> Path:
    safe_wb = _safe_name(wb_name)
    safe_det = _safe_name(determinand)
    filename = f"{safe_wb}__{safe_det}__raw_{TIMESTAMP}.csv"
    return OUT_DIR / filename


def save_output(df: pd.DataFrame, wb_name: str, determinand: str) -> Path:
    path = output_path(wb_name, determinand)
    path.parent.mkdir(parents=True, exist_ok=True)

    if df is None or df.empty:
        print(f"No data for {wb_name} / {determinand}, skipping save")
        return path

    try:
        df.to_csv(path, index=False)
        print(f"Saved output: {path.name}")
    except Exception as e:
        print(f"Error saving output {path}: {e}")

    return path
