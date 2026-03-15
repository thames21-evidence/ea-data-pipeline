# g - CHECKPOINTING

from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from .b_utils import _safe_name
from .a_config import OUT_DIR, TMP_DIR


def checkpoint_path(wb_name: str, determinand: str) -> Path:
    safe_wb = _safe_name(wb_name)
    safe_det = _safe_name(determinand)
    return TMP_DIR / f"{safe_wb}__{safe_det}__checkpoint.csv"


def load_checkpoint(wb_name: str, determinand: str) -> Optional[pd.DataFrame]:
    path = checkpoint_path(wb_name, determinand)
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            print(f"Error loading checkpoint {path}: {e}")
            return None
    return None


def save_checkpoint(wb_name: str, determinand: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    df = pd.DataFrame(rows)
    path = checkpoint_path(wb_name, determinand)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(path, index=False)
    except Exception as e:
        print(f"Error saving checkpoint {path}: {e}")


def checkpoint_exists(wb_name: str, determinand: str) -> bool:
    return checkpoint_path(wb_name, determinand).exists()
