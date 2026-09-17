"""What-if simulation on the production RETENSA pipeline.

Modifies legitimate input features and scores the same saved XGBoost pipeline.
Results are model-simulated probabilities, not guaranteed real-world outcomes.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.data.load import load_cleaned_dataset
from src.models.predict import load_churn_pipeline, predict_churn
from src.risk.segmentation import risk_level_from_probability
from src.utils.config import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    MODEL_PATH,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)

LEAKAGE_COLUMNS = {
    "Churn",
    "Predicted_Churn",
    "Churn_Probability",
    "Risk_Level",
    "Predicted Churn",
    "Churn Probability",
    "Risk Level",
}

INTERNET_DEPENDENT = [
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
]

_VOCAB_CACHE: dict[str, set[str]] | None = None


def _single_customer(customer_data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(customer_data, pd.DataFrame):
        raise TypeError("customer_data must be a pandas DataFrame.")
    if customer_data.empty:
        raise ValueError("customer_data is empty.")
    if len(customer_data) != 1:
        raise ValueError(f"Expected exactly one customer row, got {len(customer_data)}.")
    frame = customer_data.drop(columns=[TARGET_COLUMN], errors="ignore")
    missing = [col for col in FEATURE_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"Missing required feature columns: {missing}")
    return frame[FEATURE_COLUMNS].copy()


def _category_vocabulary() -> dict[str, set[str]]:
    global _VOCAB_CACHE
    if _VOCAB_CACHE is not None:
        return _VOCAB_CACHE
    df = load_cleaned_dataset()
    vocab = {
        col: {str(value) for value in df[col].dropna().unique()}
        for col in CATEGORICAL_FEATURES
        if col in df.columns
    }
    _VOCAB_CACHE = vocab
    return vocab


def _invalid_result(message: str) -> dict[str, Any]:
    return {"valid": False, "error": message}


def _validate_changes(changes: dict, original: pd.DataFrame) -> str | None:
    if not isinstance(changes, dict) or not changes:
        return "changes must be a non-empty dictionary of feature_name -> new_value."
    for feature, new_value in changes.items():
        if feature in LEAKAGE_COLUMNS or feature == TARGET_COLUMN:
            return f"Cannot modify '{feature}'. Target and post-prediction fields are not allowed."
        if feature not in FEATURE_COLUMNS:
            return f"Unknown feature '{feature}'. Allowed features: {FEATURE_COLUMNS}."
        if feature in NUMERIC_FEATURES:
            error = _validate_numeric(feature, new_value)
            if error:
                return error
        elif feature in CATEGORICAL_FEATURES:
            error = _validate_categorical(feature, new_value)
            if error:
                return error
        current = original.iloc[0][feature]
        if pd.isna(new_value):
            return f"New value for '{feature}' cannot be missing."
        if str(current) == str(new_value):
            continue
    return None


def _validate_numeric(feature: str, value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return f"'{feature}' must be numeric, got {value!r}."
    if isinstance(value, str):
        return f"'{feature}' must be numeric, got {value!r}."
    try:
        number = float(value)
    except (TypeError, ValueError):
        return f"'{feature}' must be numeric, got {value!r}."
    if not np.isfinite(number):
        return f"'{feature}' must be a finite number, got {value!r}."
    if feature == "SeniorCitizen" and number not in {0.0, 1.0}:
        return "SeniorCitizen must be 0 or 1."
    if feature == "tenure" and (number < 0 or number > 72):
        return "tenure must be between 0 and 72."
    if feature == "MonthlyCharges" and (number < 0 or number > 200):
        return "MonthlyCharges must be between 0 and 200."
    if feature == "TotalCharges" and (number < 0 or number > 10000):
        return "TotalCharges must be between 0 and 10000."
    return None


def _validate_categorical(feature: str, value: Any) -> str | None:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return f"'{feature}' cannot be missing."
    allowed = _category_vocabulary().get(feature, set())
    if allowed and str(value) not in allowed:
        options = ", ".join(sorted(allowed))
        return f"Invalid value {value!r} for '{feature}'. Allowed: {options}."
    return None


def _consistency_error(row: pd.Series) -> str | None:
    phone = str(row["PhoneService"])
    lines = str(row["MultipleLines"])
    if phone == "No" and lines != "No phone service":
        return (
            "Invalid customer state: PhoneService='No' requires "
            "MultipleLines='No phone service'."
        )
    if phone == "Yes" and lines == "No phone service":
        return (
            "Invalid customer state: PhoneService='Yes' cannot be combined with "
            "MultipleLines='No phone service'."
        )
    internet = str(row["InternetService"])
    if internet == "No":
        for col in INTERNET_DEPENDENT:
            if str(row[col]) != "No internet service":
                return (
                    f"Invalid customer state: InternetService='No' requires "
                    f"{col}='No internet service'."
                )
    if internet in {"DSL", "Fiber optic"}:
        for col in INTERNET_DEPENDENT:
            if str(row[col]) == "No internet service":
                return (
                    f"Invalid customer state: InternetService='{internet}' cannot be "
                    f"combined with {col}='No internet service'."
                )
    return None


def simulate_scenario(customer_data: pd.DataFrame, changes: dict) -> dict[str, Any]:
    """Score original vs modified features with the production pipeline only."""
    customer = _single_customer(customer_data)
    change_error = _validate_changes(changes, customer)
    if change_error:
        return _invalid_result(change_error)

    scenario = customer.copy()
    feature_changes = {}
    for feature, new_value in changes.items():
        old_value = customer.iloc[0][feature]
        if feature in NUMERIC_FEATURES:
            new_value = float(new_value)
            if feature == "SeniorCitizen":
                new_value = int(new_value)
            elif feature == "tenure" and float(new_value).is_integer():
                new_value = int(new_value)
        scenario.iloc[0, scenario.columns.get_loc(feature)] = new_value
        feature_changes[feature] = {"from": _json_value(old_value), "to": _json_value(new_value)}

    consistency = _consistency_error(scenario.iloc[0])
    if consistency:
        return _invalid_result(consistency)

    pipeline = load_churn_pipeline(MODEL_PATH)
    original_pred = predict_churn(customer, pipeline=pipeline).iloc[0]
    scenario_pred = predict_churn(scenario, pipeline=pipeline).iloc[0]
    original_p = float(original_pred["churn_probability"])
    scenario_p = float(scenario_pred["churn_probability"])
    delta = scenario_p - original_p
    original_risk = risk_level_from_probability(original_p)
    scenario_risk = risk_level_from_probability(scenario_p)
    return {
        "valid": True,
        "original": {
            "churn_probability": original_p,
            "risk_level": original_risk,
        },
        "scenario": {
            "changes": feature_changes,
            "churn_probability": scenario_p,
            "risk_level": scenario_risk,
        },
        "impact": {
            "probability_delta": delta,
            "probability_change_percentage_points": delta * 100.0,
            "risk_changed": original_risk != scenario_risk,
        },
        "note": (
            "Values are model-simulated churn probabilities from the production "
            "pipeline, not guaranteed real-world outcomes."
        ),
    }


def compare_scenarios(customer_data: pd.DataFrame, scenarios: list[dict]) -> list[dict[str, Any]]:
    """Compare several model-simulated scenarios for one customer."""
    if not scenarios:
        raise ValueError("scenarios must be a non-empty list.")
    results = []
    for spec in scenarios:
        name = spec.get("name", "unnamed")
        changes = spec.get("changes", {})
        simulation = simulate_scenario(customer_data, changes)
        if not simulation.get("valid", False):
            results.append(
                {
                    "name": name,
                    "valid": False,
                    "error": simulation.get("error"),
                }
            )
            continue
        original_p = simulation["original"]["churn_probability"]
        new_p = simulation["scenario"]["churn_probability"]
        results.append(
            {
                "name": name,
                "valid": True,
                "original_probability": original_p,
                "new_probability": new_p,
                "delta": new_p - original_p,
                "original_risk": simulation["original"]["risk_level"],
                "new_risk": simulation["scenario"]["risk_level"],
                "changes": simulation["scenario"]["changes"],
                "note": "Model-simulated impact, not guaranteed customer behavior.",
            }
        )
    valid_rows = [row for row in results if row.get("valid")]
    invalid_rows = [row for row in results if not row.get("valid")]
    valid_rows.sort(key=lambda row: abs(row["delta"]), reverse=True)
    return valid_rows + invalid_rows


def _json_value(value: Any):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if pd.isna(value):
        return None
    return value
