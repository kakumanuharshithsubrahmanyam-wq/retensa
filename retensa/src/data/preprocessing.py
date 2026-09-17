"""Reusable preprocessing for training, prediction, and later simulation."""

from __future__ import annotations

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.data.features import ENGINEERED_CATEGORICAL, ENGINEERED_NUMERIC, FeatureEngineer
from src.utils.config import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    TARGET_MAP,
)


def encode_target(series: pd.Series) -> pd.Series:
    """Map Churn labels Yes/No to 1/0. Unknown labels become missing."""
    mapped = series.map(TARGET_MAP)
    if mapped.isna().any():
        unknown = sorted(series[mapped.isna()].astype(str).unique().tolist())
        raise ValueError(f"Unexpected Churn labels: {unknown}. Expected Yes/No.")
    return mapped.astype(int)


def prepare_feature_frame(X: pd.DataFrame) -> pd.DataFrame:
    """Select model features and coerce numeric columns. Does not encode the target."""
    if not isinstance(X, pd.DataFrame):
        X = pd.DataFrame(X)

    missing = [col for col in FEATURE_COLUMNS if col not in X.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")

    features = X[FEATURE_COLUMNS].copy()
    for col in NUMERIC_FEATURES:
        features[col] = pd.to_numeric(features[col], errors="coerce")
    for col in CATEGORICAL_FEATURES:
        features[col] = features[col].astype("string")
    return features


def split_features_and_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    if TARGET_COLUMN not in df.columns:
        raise ValueError(f"Dataset must contain '{TARGET_COLUMN}' for training.")
    y = encode_target(df[TARGET_COLUMN])
    X = prepare_feature_frame(df)
    return X, y


class FeaturePreparer(BaseEstimator, TransformerMixin):
    """Keep feature selection and numeric coercion inside the saved pipeline."""

    def fit(self, X, y=None):
        prepared = prepare_feature_frame(X)
        self.n_features_in_ = prepared.shape[1]
        self.feature_names_in_ = prepared.columns.to_numpy()
        return self

    def transform(self, X):
        return prepare_feature_frame(X)


def build_preprocessor(use_engineered_features: bool = False) -> Pipeline:
    """sklearn pipeline: feature selection/coercion → scale numerics → one-hot categoricals.

    Default arguments preserve the Phase 1 baseline preprocessor.
    """
    numeric_features = list(NUMERIC_FEATURES)
    categorical_features = list(CATEGORICAL_FEATURES)
    steps: list[tuple] = [("prepare", FeaturePreparer())]
    if use_engineered_features:
        steps.append(("engineer", FeatureEngineer()))
        numeric_features = numeric_features + ENGINEERED_NUMERIC
        categorical_features = categorical_features + ENGINEERED_CATEGORICAL

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "encoder",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    column_transformer = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
        verbose_feature_names_out=False,
    )
    steps.append(("transform", column_transformer))
    return Pipeline(steps=steps)
