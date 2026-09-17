"""Business-friendly root-cause view of Phase 2 SHAP explanations.

This module does not compute a second explanation. It wraps
`get_customer_explanation` from the production SHAP layer.
SHAP reports model contribution, not causation.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.explainability.shap_explainer import get_customer_explanation
from src.utils.config import FEATURE_COLUMNS, TARGET_COLUMN

_FEATURE_PHRASES = {
    "Contract": "contract type",
    "tenure": "tenure",
    "TechSupport": "tech support",
    "OnlineSecurity": "online security",
    "OnlineBackup": "online backup",
    "DeviceProtection": "device protection",
    "InternetService": "internet service",
    "PaymentMethod": "payment method",
    "MonthlyCharges": "monthly charges",
    "TotalCharges": "total charges",
    "PaperlessBilling": "paperless billing",
    "Partner": "partner status",
    "Dependents": "dependents",
    "MultipleLines": "multiple lines",
    "PhoneService": "phone service",
    "StreamingTV": "streaming TV",
    "StreamingMovies": "streaming movies",
    "SeniorCitizen": "senior-citizen status",
    "gender": "gender",
}


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


def analyze_root_cause(
    customer_data: pd.DataFrame,
    top_n: int = 5,
) -> dict[str, Any]:
    """Structured root-cause view from existing SHAP + predict_proba output."""
    customer = _single_customer(customer_data)
    explanation = get_customer_explanation(customer, top_n=top_n)
    risk_factors = list(explanation["top_risk_factors"])
    protective_factors = list(explanation["protective_factors"])
    primary = risk_factors[0] if risk_factors else None
    index = customer.index[0]
    return {
        "customer_index": index if isinstance(index, (int, str)) else str(index),
        "churn_probability": float(explanation["churn_probability"]),
        "risk_level": explanation["risk_level"],
        "primary_root_cause": primary,
        "risk_factors": risk_factors,
        "protective_factors": protective_factors,
        "shap_output_space": explanation.get("shap_output_space"),
        "base_value": explanation.get("base_value"),
    }


def _factor_phrase(feature: str, customer: pd.DataFrame) -> str:
    value = customer.iloc[0][feature] if feature in customer.columns else None
    if feature == "Contract" and value is not None:
        return f"the {str(value).lower()} contract"
    if feature == "tenure" and value is not None:
        tenure = float(value)
        if tenure <= 12:
            return "short tenure"
        return "tenure"
    if feature in {"TechSupport", "OnlineSecurity", "OnlineBackup", "DeviceProtection"}:
        if str(value) == "No":
            return f"lack of {_FEATURE_PHRASES.get(feature, feature)}"
        return _FEATURE_PHRASES.get(feature, feature)
    if feature == "PaymentMethod" and value is not None:
        return f"payment method ({value})"
    if feature == "InternetService" and value is not None:
        return f"{value} internet service"
    return _FEATURE_PHRASES.get(feature, feature)


def generate_root_cause_summary(customer_data: pd.DataFrame, top_n: int = 3) -> str:
    """Deterministic template summary. No LLM. No causal claims."""
    customer = _single_customer(customer_data)
    result = analyze_root_cause(customer, top_n=max(top_n, 5))
    probability_pct = result["churn_probability"] * 100
    risk = str(result["risk_level"]).lower()
    drivers = [_factor_phrase(str(item["feature"]), customer) for item in result["risk_factors"][:top_n]]
    if not drivers:
        return (
            f"Customer has a {risk} predicted churn risk of {probability_pct:.0f}%. "
            "The model did not identify features that increase churn relative to its baseline."
        )
    if len(drivers) == 1:
        driver_text = drivers[0]
    elif len(drivers) == 2:
        driver_text = f"{drivers[0]} and {drivers[1]}"
    else:
        driver_text = f"{drivers[0]}, {drivers[1]}, and {drivers[2]}"
    primary = result["primary_root_cause"]
    primary_name = primary["feature"] if primary else "the leading feature"
    return (
        f"Customer has a {risk} predicted churn risk of {probability_pct:.0f}%. "
        f"The strongest model drivers increasing churn are {driver_text}. "
        f"{primary_name} is the primary model driver (largest SHAP contribution among "
        "features that increase the model's churn score). This is model contribution, "
        "not a proven cause of churn."
    )
