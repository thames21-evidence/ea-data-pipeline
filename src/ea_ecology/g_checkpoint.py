# g - CHECKPOINTING

from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from .b_utils import _safe_name
from .a_config import OUT_DIR, TMP_DIR


def checkpoint_path(wb_name: str, group: str) -> Path:
    """
    Build the path to the checkpoint CSV for a given waterbody + group.
    """
    safe_wb = _safe_name(wb_name)
    safe_group = _safe_name(group)
    return TMP_DIR / f"{safe_wb}__{safe_group}__checkpoint.csv"


def load_checkpoint(wb_name: str, group: str) -> Optional[pd.DataFrame]:
    """
    Load an existing checkpoint if it exists.
    Returns a DataFrame or None.
    """
    path = checkpoint_path(wb_name, group)
    if path.exists():
        try:
            return pd.read_csv(path)
        except Exception as e:
            print(f"Error loading checkpoint {path}: {e}")
            return None
    return None


def save_checkpoint(wb_name: str, group: str, rows: List[Dict[str, Any]]) -> None:
    """
    Save raw observation rows to a checkpoint CSV.
    """
    if not rows:
        return

    df = pd.DataFrame(rows)
    path = checkpoint_path(wb_name, group)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        df.to_csv(path, index=False)
    except Exception as e:
        print(f"Error saving checkpoint {path}: {e}")


def checkpoint_exists(wb_name: str, group: str) -> bool:
    """
    Check whether a checkpoint already exists.
    """
    return checkpoint_path(wb_name, group).exists()