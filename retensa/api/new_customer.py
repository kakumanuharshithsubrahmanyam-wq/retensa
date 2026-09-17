"""Validate and analyze ad-hoc customers with the production pipeline.

New customers are never written to the training dataset.
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd

from src.models.predict import predict_churn
from src.recommendations.action_center import build_action_center
from src.simulator.what_if import (
    _category_vocabulary,
    _consistency_error,
    _validate_categorical,
    _validate_numeric,
)
from src.utils.config import CATEGORICAL_FEATURES, FEATURE_COLUMNS, NUMERIC_FEATURES


class NewCustomerValidationError(ValueError):
    """Raised when submitted features fail schema or consistency checks."""


def validate_and_build_frame(payload: Dict[str, Any]) -> pd.DataFrame:
    """Validate feature payload and return a one-row DataFrame for the production model."""
    if not isinstance(payload, dict):
        raise NewCustomerValidationError("Request body must be a JSON object of customer features.")

    missing = [col for col in FEATURE_COLUMNS if col not in payload]
    if missing:
        raise NewCustomerValidationError(f"Missing required fields: {', '.join(missing)}")

    unknown = [key for key in payload.keys() if key not in FEATURE_COLUMNS]
    if unknown:
        raise NewCustomerValidationError(f"Unknown fields are not allowed: {', '.join(sorted(unknown))}")

    # Ensure vocabulary is loaded before categorical checks.
    _category_vocabulary()

    values: Dict[str, Any] = {}
    for col in FEATURE_COLUMNS:
        raw = payload[col]
        if col in NUMERIC_FEATURES:
            # Accept numeric strings for form posts.
            if isinstance(raw, str) and raw.strip() != "":
                try:
                    raw = float(raw) if col != "SeniorCitizen" else int(float(raw))
                except ValueError as exc:
                    raise NewCustomerValidationError(f"'{col}' must be numeric, got {raw!r}.") from exc
            error = _validate_numeric(col, raw)
            if error:
                # Align with product rules: tenure/charges only need >= 0 (what_if also caps ranges).
                raise NewCustomerValidationError(error)
            if col == "SeniorCitizen":
                values[col] = int(raw)
            elif col == "tenure":
                values[col] = int(raw) if float(raw).is_integer() else float(raw)
            else:
                values[col] = float(raw)
        else:
            error = _validate_categorical(col, raw)
            if error:
                raise NewCustomerValidationError(error)
            values[col] = str(raw)

    frame = pd.DataFrame([values], columns=FEATURE_COLUMNS)
    consistency = _consistency_error(frame.iloc[0])
    if consistency:
        raise NewCustomerValidationError(consistency)
    return frame


def analyze_new_customer(payload: Dict[str, Any], *, include_llm: bool = True) -> Dict[str, Any]:
    """Score a brand-new customer with Phase 1–4 intelligence (no dataset write)."""
    frame = validate_and_build_frame(payload)
    center = build_action_center(frame, include_llm=include_llm)
    prediction = predict_churn(frame).iloc[0]
    primary = center["root_cause"].get("primary_driver") or {}
    primary_name = primary.get("feature") if isinstance(primary, dict) else primary

    return {
        "customer": {
            "is_new": True,
            "label": "New Customer",
            "features": center["customer"]["attributes"],
            "attributes": center["customer"]["attributes"],
        },
        "prediction": {
            "churn_probability": float(prediction["churn_probability"]),
            "predicted_churn": int(prediction["predicted_churn"]),
            "risk_level": center["risk"]["level"],
        },
        "risk": center["risk"],
        "explanation": {
            "primary_model_driver": primary_name,
            "risk_factors": center["root_cause"].get("risk_factors") or [],
            "protective_factors": center["root_cause"].get("protective_factors") or [],
        },
        "root_cause": center["root_cause"],
        "recommendations": center["recommended_actions"],
        "what_if": center["what_if_scenarios"],
        "action_plan": center["action_plan"],
        "action_center": center,
        "ai_plan": center["llm"],
    }


def what_if_for_features(features: Dict[str, Any], changes: Dict[str, Any]) -> Dict[str, Any]:
    """Run Phase 3 What-If on an ad-hoc feature set (not a dataset row)."""
    from src.simulator.what_if import simulate_scenario

    frame = validate_and_build_frame(features)
    return simulate_scenario(frame, changes)
