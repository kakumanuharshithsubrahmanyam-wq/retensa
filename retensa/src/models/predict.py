"""Load the saved churn pipeline and score customer records."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from src.utils.config import MODEL_PATH


def load_churn_pipeline(model_path: Path | None = None):
    path = Path(model_path) if model_path is not None else MODEL_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"Trained pipeline not found at {path}. Run: python -m src.models.train"
        )
    return joblib.load(path)


def predict_churn(
    customers: pd.DataFrame,
    pipeline=None,
    model_path: Path | None = None,
) -> pd.DataFrame:
    """Return predicted churn (0/1) and churn probability in [0, 1]."""
    if customers.empty:
        return pd.DataFrame(columns=["predicted_churn", "churn_probability"])

    model = pipeline if pipeline is not None else load_churn_pipeline(model_path)
    predicted = model.predict(customers)
    probabilities = model.predict_proba(customers)[:, 1]

    return pd.DataFrame(
        {
            "predicted_churn": predicted.astype(int),
            "churn_probability": probabilities.astype(float),
        },
        index=customers.index,
    )
