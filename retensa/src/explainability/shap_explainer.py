"""SHAP explanations for the saved Phase 1 churn pipeline.

Explains the fitted XGBoost model in transformed feature space, then aggregates
one-hot SHAP values back to the original customer-level columns.

Churn probability always comes from Pipeline.predict_proba().
SHAP values are kept separate and are not treated as percentage-point effects.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import shap

from src.data.preprocessing import prepare_feature_frame
from src.models.predict import load_churn_pipeline, predict_churn
from src.risk.segmentation import risk_level_from_probability
from src.utils.config import FEATURE_COLUMNS, MODEL_PATH, RANDOM_SEED, TARGET_COLUMN

SHAP_SAMPLE_SIZE = 1000
PREPROCESSOR_PREFIXES = (
    "numeric__",
    "categorical__",
    "num__",
    "cat__",
    "transform__",
    "prepare__",
)


class ShapExplainer:
    """TreeExplainer wrapper around the existing preprocessor + XGBoost pipeline."""

    def __init__(self, model_path: Path | None = None) -> None:
        path = Path(model_path) if model_path is not None else MODEL_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"Trained pipeline not found at {path}. Run Phase 1 training first."
            )

        self.pipeline = load_churn_pipeline(path)
        self._validate_pipeline()
        self.preprocessor = self.pipeline.named_steps["preprocessor"]
        self.model = self.pipeline.named_steps["model"]
        self.transformed_feature_names = self._transformed_feature_names()
        self.original_feature_map = {
            name: map_transformed_feature_to_original(name)
            for name in self.transformed_feature_names
        }
        self.explainer = shap.TreeExplainer(self.model)
        self.shap_output_space = infer_shap_output_space(self.explainer)

    def _validate_pipeline(self) -> None:
        steps = getattr(self.pipeline, "named_steps", None)
        if steps is None or "preprocessor" not in steps or "model" not in steps:
            raise ValueError(
                "Incompatible model file: expected a sklearn Pipeline with "
                "'preprocessor' and 'model' steps."
            )

    def _transformed_feature_names(self) -> list[str]:
        preprocessor = self.preprocessor
        column_transformer = None
        if hasattr(preprocessor, "named_steps") and "transform" in preprocessor.named_steps:
            column_transformer = preprocessor.named_steps["transform"]

        names = None
        if column_transformer is not None and hasattr(column_transformer, "get_feature_names_out"):
            names = column_transformer.get_feature_names_out()
        elif hasattr(preprocessor, "get_feature_names_out"):
            try:
                names = preprocessor.get_feature_names_out()
            except Exception as exc:
                raise ValueError(
                    "Could not recover transformed feature names from the preprocessor."
                ) from exc
        if names is None:
            raise ValueError(
                "Preprocessor does not expose get_feature_names_out(); "
                "cannot map SHAP values onto original features."
            )
        return [str(name) for name in names]

    def transform(self, X: pd.DataFrame) -> np.ndarray:
        features = prepare_feature_frame(X)
        transformed = self.preprocessor.transform(features)
        array = np.asarray(transformed)
        if array.ndim != 2:
            raise ValueError(f"Expected 2D transformed features, got shape {array.shape}.")
        n_expected = len(self.transformed_feature_names)
        if array.shape[1] != n_expected:
            raise ValueError(
                f"Transformed data has {array.shape[1]} columns but the model "
                f"expects {n_expected}. The saved preprocessor may be incompatible."
            )
        model_features = getattr(self.model, "n_features_in_", None)
        if model_features is not None and array.shape[1] != int(model_features):
            raise ValueError(
                f"Transformed data has {array.shape[1]} columns but XGBoost "
                f"expects {model_features}."
            )
        return array

    def shap_values(self, X: pd.DataFrame) -> tuple[np.ndarray, float]:
        transformed = self.transform(X)
        try:
            raw_values = self.explainer.shap_values(transformed)
        except Exception as exc:
            raise RuntimeError(f"SHAP computation failed: {exc}") from exc
        values = extract_positive_class_shap(raw_values, n_samples=transformed.shape[0])
        if values.shape != transformed.shape:
            raise RuntimeError(
                f"SHAP value shape {values.shape} does not match transformed "
                f"data shape {transformed.shape}."
            )
        base_value = extract_base_value(self.explainer, raw_values)
        return values, base_value

    def aggregate_shap(self, shap_values: np.ndarray) -> pd.DataFrame:
        """Sum one-hot SHAP columns that belong to the same original feature."""
        frame = pd.DataFrame(shap_values, columns=self.transformed_feature_names)
        aggregated: dict[str, pd.Series] = {}
        for original in FEATURE_COLUMNS:
            columns = [
                name
                for name, mapped in self.original_feature_map.items()
                if mapped == original
            ]
            if not columns:
                continue
            aggregated[original] = frame[columns].sum(axis=1)
        extra = sorted(
            {
                mapped
                for mapped in self.original_feature_map.values()
                if mapped not in aggregated
            }
        )
        for original in extra:
            columns = [
                name
                for name, mapped in self.original_feature_map.items()
                if mapped == original
            ]
            aggregated[original] = frame[columns].sum(axis=1)
        return pd.DataFrame(aggregated)


def map_transformed_feature_to_original(transformed_name: str) -> str:
    """Map a transformed column name to an original customer feature."""
    name = strip_preprocessor_prefix(transformed_name)
    if name in FEATURE_COLUMNS:
        return name
    matches = [
        feature
        for feature in FEATURE_COLUMNS
        if name == feature or name.startswith(f"{feature}_")
    ]
    if not matches:
        raise ValueError(
            f"Cannot map transformed feature '{transformed_name}' to an original column."
        )
    return max(matches, key=len)


def strip_preprocessor_prefix(name: str) -> str:
    stripped = name
    for prefix in PREPROCESSOR_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break
    return stripped


def infer_shap_output_space(explainer: Any) -> str:
    """Describe the space TreeExplainer is using for the current SHAP version."""
    model_output = getattr(explainer, "model_output", None)
    if model_output in {"probability", "prob", "predict_proba"}:
        return "probability"
    if model_output in {None, "raw", "raw_margin", "margin", "log_loss"}:
        return "raw_margin"
    return str(model_output)


def extract_positive_class_shap(shap_output: Any, n_samples: int) -> np.ndarray:
    """Normalize SHAP return types to shape (n_samples, n_transformed_features)."""
    values = shap_output
    if hasattr(shap_output, "values"):
        values = shap_output.values

    if isinstance(values, list):
        if not values:
            raise RuntimeError("TreeExplainer returned an empty SHAP value list.")
        values = values[-1]

    array = np.asarray(values, dtype=float)
    if array.ndim == 3:
        if array.shape[-1] == 2:
            array = array[:, :, 1]
        elif array.shape[0] == 2:
            array = array[1]
        elif array.shape[1] == 2 and array.shape[0] == n_samples:
            array = array[:, 1, :]
        else:
            raise RuntimeError(f"Unsupported 3D SHAP value shape: {array.shape}")

    if array.ndim == 1:
        array = array.reshape(1, -1)
    if array.ndim != 2:
        raise RuntimeError(f"Unsupported SHAP value shape: {array.shape}")
    if array.shape[0] != n_samples and array.shape[1] == n_samples:
        array = array.T
    return array


def extract_base_value(explainer: Any, shap_output: Any = None) -> float:
    """Return a scalar expected/base value for the positive (churn) class."""
    candidate = None
    if shap_output is not None and hasattr(shap_output, "base_values"):
        candidate = shap_output.base_values
    if candidate is None:
        candidate = getattr(explainer, "expected_value", None)
    if candidate is None:
        raise RuntimeError("Could not recover a SHAP base/expected value.")

    array = np.asarray(candidate, dtype=float).reshape(-1)
    if array.size == 0:
        raise RuntimeError("SHAP base value array is empty.")
    if array.size == 1:
        return float(array[0])
    return float(array[-1])


_DEFAULT_EXPLAINER: ShapExplainer | None = None


def get_explainer(model_path: Path | None = None) -> ShapExplainer:
    global _DEFAULT_EXPLAINER
    if model_path is not None:
        return ShapExplainer(model_path=model_path)
    if _DEFAULT_EXPLAINER is None:
        _DEFAULT_EXPLAINER = ShapExplainer()
    return _DEFAULT_EXPLAINER


def get_global_feature_importance(
    X: pd.DataFrame,
    top_n: int = 10,
    sample_size: int = SHAP_SAMPLE_SIZE,
    random_state: int = RANDOM_SEED,
    explainer: ShapExplainer | None = None,
) -> list[dict[str, float | str]]:
    """Mean |SHAP| by original feature, sorted descending."""
    if top_n < 1:
        raise ValueError("top_n must be >= 1.")
    engine = explainer or get_explainer()
    sample = _sample_rows(X, sample_size=sample_size, random_state=random_state)
    shap_values, _base = engine.shap_values(sample)
    aggregated = engine.aggregate_shap(shap_values)
    importance = aggregated.abs().mean(axis=0).sort_values(ascending=False)
    rows = [
        {"feature": str(feature), "importance": float(score)}
        for feature, score in importance.head(top_n).items()
    ]
    return rows


def explain_customer(
    customer_data: pd.DataFrame,
    explainer: ShapExplainer | None = None,
) -> list[dict[str, float | str]]:
    """Local original-feature SHAP contributions for a single customer."""
    customer = _require_single_customer(customer_data)
    engine = explainer or get_explainer()
    shap_values, _base = engine.shap_values(customer)
    aggregated = engine.aggregate_shap(shap_values).iloc[0]
    ordered = aggregated.reindex(aggregated.abs().sort_values(ascending=False).index)
    results: list[dict[str, float | str]] = []
    for feature, value in ordered.items():
        shap_value = float(value)
        results.append(
            {
                "feature": str(feature),
                "shap_value": shap_value,
                "impact": float(abs(shap_value)),
                "direction": "increases_churn" if shap_value >= 0 else "decreases_churn",
            }
        )
    return results


def get_customer_explanation(
    customer_data: pd.DataFrame,
    top_n: int = 5,
    explainer: ShapExplainer | None = None,
) -> dict[str, Any]:
    """Frontend-ready local explanation with probability, risk, and SHAP factors."""
    if top_n < 1:
        raise ValueError("top_n must be >= 1.")
    customer = _require_single_customer(customer_data)
    engine = explainer or get_explainer()
    prediction = predict_churn(customer, pipeline=engine.pipeline).iloc[0]
    probability = float(prediction["churn_probability"])
    shap_values, base_value = engine.shap_values(customer)
    aggregated = engine.aggregate_shap(shap_values).iloc[0]
    ordered = aggregated.reindex(aggregated.abs().sort_values(ascending=False).index)
    contributions: list[dict[str, float | str]] = []
    for feature, value in ordered.items():
        shap_value = float(value)
        contributions.append(
            {
                "feature": str(feature),
                "shap_value": shap_value,
                "impact": float(abs(shap_value)),
                "direction": "increases_churn" if shap_value >= 0 else "decreases_churn",
            }
        )

    risk_factors = [
        {
            "feature": item["feature"],
            "direction": item["direction"],
            "shap_value": item["shap_value"],
        }
        for item in contributions
        if item["direction"] == "increases_churn"
    ][:top_n]
    protective_factors = [
        {
            "feature": item["feature"],
            "direction": item["direction"],
            "shap_value": item["shap_value"],
        }
        for item in contributions
        if item["direction"] == "decreases_churn"
    ][:top_n]

    return {
        "churn_probability": probability,
        "risk_level": risk_level_from_probability(probability),
        "base_value": float(base_value),
        "shap_output_space": engine.shap_output_space,
        "top_risk_factors": risk_factors,
        "protective_factors": protective_factors,
        "contributions": contributions,
    }


def _require_single_customer(customer_data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(customer_data, pd.DataFrame):
        raise TypeError("customer_data must be a pandas DataFrame.")
    if customer_data.empty:
        raise ValueError("customer_data is empty.")
    if len(customer_data) != 1:
        raise ValueError(
            f"explain_customer expects exactly one row, got {len(customer_data)}."
        )
    return customer_data.copy()


def _sample_rows(X: pd.DataFrame, sample_size: int, random_state: int) -> pd.DataFrame:
    if X.empty:
        raise ValueError("Cannot compute global SHAP importance on an empty DataFrame.")
    features = X.drop(columns=[TARGET_COLUMN], errors="ignore")
    n = len(features)
    if sample_size < 1:
        raise ValueError("sample_size must be >= 1.")
    if n <= sample_size:
        return features
    return features.sample(n=sample_size, random_state=random_state)
