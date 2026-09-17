"""Structured retention action plan from deterministic recommendations."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.recommendations.engine import generate_recommendation


def generate_action_plan(customer_data: pd.DataFrame) -> dict[str, Any]:
    recs = generate_recommendation(customer_data)
    ranked = recs["recommendations"]
    if not ranked:
        return {
            "immediate_action": "Monitor the account; no high-confidence intervention was identified from current model drivers.",
            "intervention": None,
            "model_simulated_impact": None,
            "reason": "No SHAP-linked, attribute-matched retention action was available.",
            "priority": "low",
            "supporting_evidence": {},
            "all_recommendations": [],
            "retention_priority": recs["retention_priority"],
            "customer_probability": recs["customer_probability"],
            "risk_level": recs["risk_level"],
            "primary_driver": recs["primary_driver"],
        }

    top = ranked[0]
    evidence = top["evidence"]
    intervention = None
    if "changes" in evidence:
        feature = top["feature"]
        change = evidence["changes"][feature]
        intervention = {
            "feature": feature,
            "current_value": change["from"],
            "suggested_value": change["to"],
        }
    impact = None
    if "what_if_probability" in evidence:
        impact = {
            "current_probability": float(evidence["original_probability"]),
            "scenario_probability": float(evidence["what_if_probability"]),
            "delta_percentage_points": float(evidence["delta_percentage_points"]),
        }
    return {
        "immediate_action": _immediate_action_text(top, recs["risk_level"]),
        "intervention": intervention,
        "model_simulated_impact": impact,
        "reason": top["reason"],
        "priority": top["priority"],
        "supporting_evidence": evidence,
        "all_recommendations": ranked,
        "retention_priority": recs["retention_priority"],
        "customer_probability": recs["customer_probability"],
        "risk_level": recs["risk_level"],
        "primary_driver": recs["primary_driver"],
    }


def _immediate_action_text(top: dict, risk_level: str) -> str:
    feature = top["feature"]
    if feature == "Contract":
        return "Contact the customer to discuss a longer-term contract option."
    if feature == "tenure":
        return "Schedule an early-tenure check-in and onboarding support outreach."
    if feature == "TechSupport":
        return "Contact the customer to offer or explain technical support assistance."
    if feature == "OnlineSecurity":
        return "Contact the customer to highlight online security options."
    if feature == "PaymentMethod":
        return "Review payment experience and available payment options with the customer."
    return f"Review the {feature} configuration with the customer in light of {risk_level} predicted risk."
