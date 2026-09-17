"""Pre-churn derived features. Uses only original customer attributes."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

ADDON_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]
SECURITY_SUPPORT_COLUMNS = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
]

ENGINEERED_NUMERIC = [
    "addon_services",
    "security_support_services",
    "charge_per_tenure",
    "month_to_month_tenure",
]
ENGINEERED_CATEGORICAL = [
    "tenure_group",
]


def _yes_count(frame: pd.DataFrame, columns: list[str]) -> pd.Series:
    return sum((frame[col].astype(str) == "Yes").astype(int) for col in columns)


def _tenure_group(tenure: pd.Series) -> pd.Series:
    bins = [-np.inf, 12, 24, 48, np.inf]
    labels = ["0-12", "13-24", "25-48", "49+"]
    return pd.cut(tenure, bins=bins, labels=labels).astype("string")


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """Add a small set of interpretable features from original columns only."""

    def fit(self, X, y=None):
        frame = pd.DataFrame(X)
        self.n_features_in_ = frame.shape[1]
        self.feature_names_in_ = np.asarray(frame.columns)
        return self

    def transform(self, X):
        frame = pd.DataFrame(X).copy()
        tenure = pd.to_numeric(frame["tenure"], errors="coerce")
        monthly = pd.to_numeric(frame["MonthlyCharges"], errors="coerce")
        total = pd.to_numeric(frame["TotalCharges"], errors="coerce")
        frame["addon_services"] = _yes_count(frame, ADDON_COLUMNS)
        frame["security_support_services"] = _yes_count(frame, SECURITY_SUPPORT_COLUMNS)
        frame["charge_per_tenure"] = np.where(tenure > 0, total / tenure, monthly)
        is_month_to_month = frame["Contract"].astype(str).eq("Month-to-month")
        frame["month_to_month_tenure"] = np.where(is_month_to_month, tenure, 0)
        frame["tenure_group"] = _tenure_group(tenure)
        return frame
