"""Frontend-ready Action Center payload. No FastAPI or React in this phase."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.recommendations.action_plan import generate_action_plan
from src.recommendations.engine import generate_recommendation
from src.recommendations.llm import build_llm_context, generate_retention_plan
from src.risk.root_cause import analyze_root_cause, generate_root_cause_summary
from src.simulator.what_if import compare_scenarios
from src.utils.config import FEATURE_COLUMNS, TARGET_COLUMN


def _customer_snapshot(customer: pd.DataFrame) -> dict[str, Any]:
    row = customer.iloc[0]
    values = {}
    for col in FEATURE_COLUMNS:
        value = row[col]
        values[col] = value.item() if hasattr(value, "item") else value
    return {
        "index": customer.index[0] if isinstance(customer.index[0], (int, str)) else str(customer.index[0]),
        "attributes": values,
    }


def _default_scenarios(customer: pd.DataFrame) -> list[dict]:
    row = customer.iloc[0]
    scenarios = []
    if str(row["Contract"]) == "Month-to-month":
        scenarios.append({"name": "Change Contract", "changes": {"Contract": "One year"}})
    if str(row["TechSupport"]) == "No" and str(row["InternetService"]) != "No":
        scenarios.append({"name": "Add Tech Support", "changes": {"TechSupport": "Yes"}})
    if (
        str(row["Contract"]) == "Month-to-month"
        and str(row["TechSupport"]) == "No"
        and str(row["InternetService"]) != "No"
    ):
        scenarios.append(
            {
                "name": "Contract + Tech Support",
                "changes": {"Contract": "One year", "TechSupport": "Yes"},
            }
        )
    if str(row["OnlineSecurity"]) == "No" and str(row["InternetService"]) != "No":
        scenarios.append({"name": "Add Online Security", "changes": {"OnlineSecurity": "Yes"}})
    return scenarios


def build_action_center(
    customer_data: pd.DataFrame,
    include_llm: bool = True,
) -> dict[str, Any]:
    """Combine prediction, SHAP/root cause, What-If, recommendations, and optional LLM."""
    from src.data.preprocessing import prepare_feature_frame

    customer = prepare_feature_frame(customer_data.drop(columns=[TARGET_COLUMN], errors="ignore"))
    if len(customer) != 1:
        customer = customer.iloc[[0]]

    recommendation = generate_recommendation(customer)
    action_plan = generate_action_plan(customer)
    root_cause = analyze_root_cause(customer)
    scenarios = _default_scenarios(customer)
    what_if = compare_scenarios(customer, scenarios) if scenarios else []
    context = build_llm_context(recommendation, action_plan, what_if)
    if include_llm:
        llm_result = generate_retention_plan(context)
    else:
        from src.recommendations.llm import _deterministic_plan

        llm_result = {
            "llm_status": "skipped",
            "recommendation_source": "deterministic",
            "provider": None,
            "retention_plan": _deterministic_plan(context),
        }

    return {
        "customer": _customer_snapshot(customer),
        "risk": {
            "probability": recommendation["customer_probability"],
            "level": recommendation["risk_level"],
            "retention_priority": recommendation["retention_priority"],
        },
        "root_cause": {
            "primary_driver": root_cause["primary_root_cause"],
            "risk_factors": root_cause["risk_factors"],
            "protective_factors": root_cause["protective_factors"],
            "summary": generate_root_cause_summary(customer),
        },
        "recommended_actions": recommendation["recommendations"],
        "what_if_scenarios": what_if,
        "action_plan": action_plan,
        "llm": llm_result,
        "llm_context": context,
    }


def format_action_center_report(center: dict[str, Any]) -> str:
    risk = center["risk"]
    root = center["root_cause"]
    plan = center["action_plan"]
    llm_plan = center["llm"]["retention_plan"]
    primary = root["primary_driver"]["feature"] if root["primary_driver"] else "None"
    lines = [
        "=" * 40,
        "RETENSA RETENTION ACTION CENTER",
        "=" * 40,
        "",
        "Customer Risk:",
        risk["level"].upper(),
        "",
        "Churn Probability:",
        f"{risk['probability'] * 100:.2f}%",
        "",
        "Primary Model Driver:",
        str(primary),
        "",
        "TOP RISK FACTORS:",
        "",
    ]
    for i, item in enumerate(root["risk_factors"][:5], start=1):
        lines.append(f"{i}. {item['feature']}")
    lines += ["", "RECOMMENDED ACTION:", plan["immediate_action"], "", "WHY:", plan["reason"]]
    impact = plan.get("model_simulated_impact")
    intervention = plan.get("intervention")
    if intervention and impact:
        lines += [
            "",
            "WHAT-IF:",
            f"{intervention['current_value']} → {intervention['suggested_value']}",
            "",
            "Current:",
            f"{impact['current_probability'] * 100:.2f}%",
            "",
            "Scenario:",
            f"{impact['scenario_probability'] * 100:.2f}%",
            "",
            "Model-simulated change:",
            f"{impact['delta_percentage_points']:.2f} percentage points",
        ]
    lines += [
        "",
        "AI RETENTION PLAN:",
        llm_plan.get("summary", ""),
        llm_plan.get("recommended_action", ""),
        llm_plan.get("caution", ""),
        "",
        f"LLM status: {center['llm']['llm_status']} ({center['llm']['recommendation_source']})",
        "IMPORTANT: Values are from the production model. LLM text is grounded in structured evidence.",
        "",
    ]
    return "\n".join(lines)
