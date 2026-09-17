"""Deterministic retention recommendations from Phase 1–3 evidence.

The LLM is not used here. Numbers come from predict_proba, SHAP, and What-If.
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.risk.root_cause import analyze_root_cause
from src.simulator.what_if import simulate_scenario
from src.utils.config import FEATURE_COLUMNS, TARGET_COLUMN

MEANINGFUL_DELTA = -0.03
STRONG_DELTA = -0.08


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


def _shap_lookup(risk_factors: list[dict]) -> dict[str, dict]:
    return {str(item["feature"]): item for item in risk_factors}


def _shap_rank(risk_factors: list[dict], feature: str) -> int | None:
    for index, item in enumerate(risk_factors):
        if item["feature"] == feature:
            return index
    return None


def _priority(rank: int | None, delta: float | None) -> str:
    strong_sim = delta is not None and delta <= STRONG_DELTA
    medium_sim = delta is not None and delta <= MEANINGFUL_DELTA
    if rank == 0 or strong_sim:
        return "high"
    if rank is not None and rank <= 2 or medium_sim:
        return "medium"
    return "low"


def _what_if_evidence(customer: pd.DataFrame, changes: dict) -> dict | None:
    result = simulate_scenario(customer, changes)
    if not result.get("valid"):
        return None
    delta = float(result["impact"]["probability_delta"])
    if delta >= 0:
        return None
    change_items = result["scenario"]["changes"]
    return {
        "what_if_probability": float(result["scenario"]["churn_probability"]),
        "probability_delta": delta,
        "delta_percentage_points": float(result["impact"]["probability_change_percentage_points"]),
        "original_probability": float(result["original"]["churn_probability"]),
        "original_risk": result["original"]["risk_level"],
        "scenario_risk": result["scenario"]["risk_level"],
        "changes": change_items,
    }


def generate_recommendation(customer_data: pd.DataFrame) -> dict[str, Any]:
    """Build prioritized retention actions from SHAP, attributes, and What-If."""
    customer = _single_customer(customer_data)
    row = customer.iloc[0]
    root = analyze_root_cause(customer, top_n=8)
    risk_factors = root["risk_factors"]
    lookup = _shap_lookup(risk_factors)
    primary = root["primary_root_cause"]
    recommendations: list[dict[str, Any]] = []

    def add_recommendation(
        feature: str,
        action: str,
        reason: str,
        changes: dict | None = None,
    ) -> None:
        rank = _shap_rank(risk_factors, feature)
        if rank is None:
            return
        shap_item = lookup[feature]
        evidence: dict[str, Any] = {
            "shap_value": float(shap_item["shap_value"]),
            "shap_direction": shap_item["direction"],
            "current_value": _scalar(row[feature]),
        }
        if changes:
            simulation = _what_if_evidence(customer, changes)
            if simulation:
                evidence.update(simulation)
        priority = _priority(rank, evidence.get("probability_delta"))
        recommendations.append(
            {
                "feature": feature,
                "action": action,
                "reason": reason,
                "priority": priority,
                "evidence": evidence,
            }
        )

    if str(row["Contract"]) == "Month-to-month" and "Contract" in lookup:
        add_recommendation(
            "Contract",
            "Consider offering a longer-term contract option.",
            "Customer is currently on a month-to-month contract and Contract is a model risk driver.",
            changes={"Contract": "One year"},
        )
    tenure = float(row["tenure"])
    if tenure <= 12 and "tenure" in lookup:
        add_recommendation(
            "tenure",
            "Consider an early-tenure retention intervention such as onboarding support or a service check-in.",
            "Tenure is low and is a model risk driver. Tenure itself is not treated as a switchable lever.",
        )
    if str(row["TechSupport"]) == "No" and str(row["InternetService"]) != "No" and "TechSupport" in lookup:
        add_recommendation(
            "TechSupport",
            "Consider offering or promoting technical support assistance.",
            "Tech support is currently not active and is a model risk driver.",
            changes={"TechSupport": "Yes"},
        )
    if str(row["OnlineSecurity"]) == "No" and str(row["InternetService"]) != "No" and "OnlineSecurity" in lookup:
        add_recommendation(
            "OnlineSecurity",
            "Consider offering or highlighting online security services.",
            "Online security is currently not active and is a model risk driver.",
            changes={"OnlineSecurity": "Yes"},
        )
    if str(row["PaymentMethod"]) == "Electronic check" and "PaymentMethod" in lookup:
        add_recommendation(
            "PaymentMethod",
            "Consider reviewing payment experience and options with the customer.",
            "Payment method is associated with elevated model risk for this customer. This is not a claim that the method causes churn.",
            changes={"PaymentMethod": "Credit card (automatic)"},
        )
    if "MonthlyCharges" in lookup:
        add_recommendation(
            "MonthlyCharges",
            "Review the customer's current service configuration and pricing context.",
            "Monthly charges are a model risk driver. No discount is assumed or promised.",
        )
    if "InternetService" in lookup:
        add_recommendation(
            "InternetService",
            "Review the customer's internet service configuration and support experience.",
            "Internet service is a model risk driver. No service-plan change is assumed.",
        )

    order = {"high": 0, "medium": 1, "low": 2}
    recommendations.sort(
        key=lambda item: (
            order[item["priority"]],
            -abs(float(item["evidence"].get("probability_delta", 0.0) or 0.0)),
            -abs(float(item["evidence"]["shap_value"])),
        )
    )
    return {
        "customer_probability": float(root["churn_probability"]),
        "risk_level": root["risk_level"],
        "primary_driver": primary["feature"] if primary else None,
        "retention_priority": _retention_priority(root["risk_level"], recommendations),
        "recommendations": recommendations,
        "risk_factors": risk_factors,
        "protective_factors": root["protective_factors"],
        "customer_index": root["customer_index"],
        "source": "deterministic",
    }


def _retention_priority(risk_level: str, recommendations: list[dict]) -> str:
    high_actions = [item for item in recommendations if item["priority"] == "high"]
    if risk_level == "High" and high_actions:
        return "HIGH"
    if risk_level in {"High", "Medium"} and recommendations:
        return "MEDIUM"
    return "LOW"


def _scalar(value: Any):
    if hasattr(value, "item"):
        return value.item()
    return value
