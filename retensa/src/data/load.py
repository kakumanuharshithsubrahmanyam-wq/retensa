"""Load the cleaned Telco churn dataset without transforming it."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.utils.config import DATA_PATH


def load_cleaned_dataset(path: Path | None = None) -> pd.DataFrame:
    """Load the cleaned CSV as-is. Does not impute, drop, or encode values."""
    csv_path = Path(path) if path is not None else DATA_PATH
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {csv_path}. "
            "Place Telco_Customer_Churn_Cleaned.csv in data/raw/."
        )
    return pd.read_csv(csv_path)
