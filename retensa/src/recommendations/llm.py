"""LLM language layer over structured RETENSA evidence.

The LLM does not compute probabilities, SHAP, root cause, or What-If results.
"""

from __future__ import annotations

import json
import os
from typing import Any

from src.utils.config import PROJECT_ROOT

SYSTEM_PROMPT = """You are a customer-retention planning assistant for RETENSA.

Use ONLY the structured evidence provided by RETENSA.
Do not invent customer attributes.
Do not invent churn probabilities.
Do not invent SHAP values.
Do not invent what-if results.
Do not claim causality.
Do not claim that an intervention guarantees retention.
Do not create unsupported discounts or pricing promises.
Do not override the deterministic recommendation engine.
Do not invent names, emails, phone numbers, addresses, or CustomerIDs.
Convert the provided evidence into a concise, professional retention action plan.

Return JSON with keys:
summary, why_at_risk (array of strings), recommended_action, action_reason,
scenario_context, caution.

The caution field must state that impact is model-simulated and not guaranteed.
Copy numerical values from the evidence. Do not calculate new numbers.
"""


def _load_dotenv() -> None:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(env_path)


def llm_provider_name() -> str | None:
    _load_dotenv()
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def build_llm_context(recommendation: dict, action_plan: dict, what_if_rows: list[dict]) -> dict[str, Any]:
    """Minimum structured evidence for the language layer. No raw dataset dump."""
    recs = []
    for item in recommendation.get("recommendations", [])[:5]:
        recs.append(
            {
                "action": item["action"],
                "priority": item["priority"],
                "feature": item["feature"],
                "reason": item["reason"],
            }
        )
    risk_factors = []
    for item in recommendation.get("risk_factors", [])[:5]:
        evidence_match = next(
            (
                rec["evidence"]
                for rec in recommendation.get("recommendations", [])
                if rec["feature"] == item["feature"]
            ),
            {},
        )
        risk_factors.append(
            {
                "feature": item["feature"],
                "shap_value": item["shap_value"],
                "value": evidence_match.get("current_value"),
            }
        )
    what_if_results = []
    for row in what_if_rows:
        if not row.get("valid"):
            continue
        change_text = ", ".join(
            f"{name} → {change['to']}" for name, change in row.get("changes", {}).items()
        )
        what_if_results.append(
            {
                "change": change_text,
                "current_probability": row["original_probability"],
                "scenario_probability": row["new_probability"],
                "delta_percentage_points": row["delta"] * 100.0,
            }
        )
    impact = action_plan.get("model_simulated_impact")
    return {
        "churn_probability": recommendation["customer_probability"],
        "risk_level": recommendation["risk_level"],
        "primary_driver": recommendation["primary_driver"],
        "retention_priority": recommendation["retention_priority"],
        "risk_factors": risk_factors,
        "recommended_actions": recs,
        "what_if_results": what_if_results,
        "immediate_action": action_plan.get("immediate_action"),
        "model_simulated_impact": impact,
        "caution": "Model-simulated impact; not a guaranteed outcome.",
    }


def _deterministic_plan(context: dict[str, Any]) -> dict[str, Any]:
    why = [
        f"{item['feature']} is a model risk driver (SHAP {item['shap_value']:.4f})."
        for item in context.get("risk_factors", [])[:3]
    ]
    recs = context.get("recommended_actions") or []
    recommended = recs[0]["action"] if recs else "Monitor the account."
    reason = recs[0]["reason"] if recs else "No high-confidence intervention was identified."
    impact = context.get("model_simulated_impact")
    if impact:
        scenario = (
            f"Under this scenario the model-predicted probability moves from "
            f"{impact['current_probability']*100:.2f}% to "
            f"{impact['scenario_probability']*100:.2f}% "
            f"({impact['delta_percentage_points']:.2f} percentage points)."
        )
    elif context.get("what_if_results"):
        row = context["what_if_results"][0]
        scenario = (
            f"{row['change']}: model-predicted probability "
            f"{row['current_probability']*100:.2f}% → {row['scenario_probability']*100:.2f}% "
            f"({row['delta_percentage_points']:.2f} percentage points)."
        )
    else:
        scenario = "No valid What-If scenario was available for the top action."
    return {
        "summary": (
            f"Predicted churn probability is {context['churn_probability']*100:.2f}% "
            f"({context['risk_level']} risk). Primary model driver: {context['primary_driver']}."
        ),
        "why_at_risk": why,
        "recommended_action": recommended,
        "action_reason": reason,
        "scenario_context": scenario,
        "caution": context["caution"],
    }


def _call_openai(context: dict[str, Any]) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20.0)
    completion = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(context, default=str),
            },
        ],
    )
    content = completion.choices[0].message.content or "{}"
    return json.loads(content)


def _call_anthropic(context: dict[str, Any]) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=20.0)
    message = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        max_tokens=800,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(context, default=str)}],
    )
    text = "".join(block.text for block in message.content if getattr(block, "text", None))
    return json.loads(text)


def generate_retention_plan(structured_context: dict[str, Any]) -> dict[str, Any]:
    """Return an LLM plan when configured; otherwise a deterministic plan."""
    fallback = _deterministic_plan(structured_context)
    provider = llm_provider_name()
    if provider is None:
        return {
            "llm_status": "unavailable",
            "recommendation_source": "deterministic",
            "provider": None,
            "retention_plan": fallback,
        }
    try:
        if provider == "openai":
            plan = _call_openai(structured_context)
        else:
            plan = _call_anthropic(structured_context)
        if not isinstance(plan, dict):
            raise ValueError("LLM did not return a JSON object.")
        grounded = _deterministic_plan(structured_context)
        plan["caution"] = grounded["caution"]
        plan.setdefault("summary", grounded["summary"])
        plan.setdefault("recommended_action", grounded["recommended_action"])
        plan.setdefault("action_reason", grounded["action_reason"])
        plan.setdefault("scenario_context", grounded["scenario_context"])
        plan.setdefault("why_at_risk", grounded["why_at_risk"])
        return {
            "llm_status": "ok",
            "recommendation_source": "llm",
            "provider": provider,
            "retention_plan": plan,
        }
    except Exception as exc:
        return {
            "llm_status": "unavailable",
            "recommendation_source": "deterministic",
            "provider": provider,
            "error": str(exc),
            "retention_plan": fallback,
        }
