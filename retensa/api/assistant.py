"""Grounded RETENSA AI Assistant — language over deterministic evidence only."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Optional

from src.recommendations.action_center import build_action_center
from src.recommendations.llm import llm_provider_name


def _pct(value: float) -> str:
    return f"{float(value) * 100:.2f}%"


def _intent(message: str) -> str:
    text = message.lower().strip()
    if any(k in text for k in ("what if", "what-if", "simulate", "scenario")):
        return "what_if"
    if any(k in text for k in ("change the contract", "change contract", "if we change")):
        return "what_if"
    if any(k in text for k in ("retain", "recommend", "action", "should we do", "intervention", "plan")):
        return "recommend"
    if any(k in text for k in ("highest", "top risk", "priority customer", "who is at risk")):
        return "high_customers"
    if any(k in text for k in ("average", "avg", "mean probability")):
        return "avg"
    if any(
        k in text
        for k in (
            "most important model driver",
            "important model driver",
            "top churn driver",
            "global feature",
            "top model driver",
        )
    ):
        return "drivers"
    if any(k in text for k in ("how many", "segment", "distribution", "portfolio", "summary", "overview")):
        return "portfolio"
    if any(k in text for k in ("high risk", "medium risk", "low risk")) and "customer" not in text:
        return "portfolio"
    if any(k in text for k in ("why", "shap", "factor", "explain", "at risk", "influencing")):
        return "why"
    if "driver" in text:
        return "why"
    return "general"


def _customer_reply(intent: str, center: dict[str, Any], customer_label: Any) -> dict[str, Any]:
    risk = center["risk"]
    root = center["root_cause"]
    primary = root.get("primary_driver") or {}
    primary_name = primary.get("feature") if isinstance(primary, dict) else primary
    recs = center.get("recommended_actions") or []
    what_if = [row for row in (center.get("what_if_scenarios") or []) if row.get("valid")]
    plan = (center.get("llm") or {}).get("retention_plan") or {}
    is_new = isinstance(customer_label, str) and customer_label.lower().startswith("new")
    display = customer_label if is_new else f"#{customer_label}"

    evidence = {
        "customer_index": None if is_new else customer_label,
        "customer_label": display,
        "is_new": is_new,
        "probability": risk["probability"],
        "risk_level": risk["level"],
        "primary_driver": primary_name,
        "risk_factors": [
            {"feature": f["feature"], "shap_value": f["shap_value"]}
            for f in (root.get("risk_factors") or [])[:5]
        ],
        "recommendations": [
            {"action": r["action"], "priority": r["priority"], "feature": r.get("feature")}
            for r in recs[:3]
        ],
        "what_if": [
            {
                "name": row.get("name"),
                "original": row.get("original_probability"),
                "scenario": row.get("new_probability"),
                "delta_pp": row.get("delta", 0) * 100.0,
            }
            for row in what_if[:3]
        ],
    }

    if intent == "why":
        factors = evidence["risk_factors"]
        lines = [
            f"Customer {display} has a model-predicted churn probability of "
            f"{_pct(risk['probability'])} ({risk['level']} risk).",
            f"Primary model driver: {primary_name or 'unavailable'}.",
            "Factors influencing the prediction (SHAP model explanation, not proven causes):",
        ]
        for item in factors[:4]:
            direction = "increasing" if item["shap_value"] > 0 else "decreasing"
            lines.append(
                f"- {item['feature']}: SHAP contribution {item['shap_value']:.4f} ({direction} predicted risk)"
            )
        answer = "\n".join(lines)
    elif intent == "what_if":
        if not what_if:
            answer = (
                "I don't have a valid model-simulated What-If scenario for this customer "
                "in the current RETENSA data."
            )
        else:
            rows = []
            for row in what_if[:3]:
                rows.append(
                    f"- {row.get('name')}: {_pct(row['original_probability'])} → "
                    f"{_pct(row['new_probability'])} "
                    f"({row['delta'] * 100:.2f} percentage points). "
                    f"Risk {row.get('original_risk')} → {row.get('new_risk')}."
                )
            answer = (
                f"Model-simulated scenarios for customer {display} "
                f"(not guaranteed outcomes):\n" + "\n".join(rows)
            )
    elif intent == "recommend":
        if plan.get("summary"):
            answer = (
                f"{plan.get('summary')}\n"
                f"Recommended action: {plan.get('recommended_action')}\n"
                f"Reason: {plan.get('action_reason')}\n"
                f"{plan.get('scenario_context')}\n"
                f"{plan.get('caution')}"
            )
        elif recs:
            top = recs[0]
            answer = (
                f"Retention priority: {risk.get('retention_priority', risk['level'])}.\n"
                f"Action: {top['action']}\n"
                f"Priority: {str(top['priority']).upper()}\n"
                f"Evidence: {top.get('reason')}\n"
                "Model-simulated impact is not a guaranteed retention outcome."
            )
        else:
            answer = "No SHAP-linked retention intervention was identified for this customer."
    else:
        answer = (
            f"Customer {display}: model-predicted churn probability "
            f"{_pct(risk['probability'])} ({risk['level']} risk). "
            f"Primary model driver: {primary_name or 'n/a'}. "
            "Ask why they are at risk, what to do, or about a What-If scenario."
        )

    return {
        "mode": "customer",
        "answer": answer,
        "evidence": evidence,
        "source": "deterministic",
    }


def _portfolio_reply(intent: str, dashboard: dict[str, Any]) -> dict[str, Any]:
    evidence = {
        "total_customers": dashboard["total_customers"],
        "high_risk": dashboard["high_risk"],
        "medium_risk": dashboard["medium_risk"],
        "low_risk": dashboard["low_risk"],
        "avg_churn_probability": dashboard["avg_churn_probability"],
        "top_drivers": dashboard.get("top_drivers", [])[:5],
        "high_priority": [
            {
                "customer_index": row["customer_index"],
                "churn_probability": row["churn_probability"],
                "risk_level": row["risk_level"],
            }
            for row in dashboard.get("high_priority", [])[:5]
        ],
    }

    if intent == "avg":
        answer = (
            f"Average model-predicted churn probability across "
            f"{dashboard['total_customers']:,} customers is "
            f"{_pct(dashboard['avg_churn_probability'])}."
        )
    elif intent == "drivers":
        drivers = evidence["top_drivers"]
        lines = ["Top model drivers (mean |SHAP| on a customer sample):"]
        for item in drivers:
            lines.append(f"- {item['feature']}: importance {float(item['importance']):.4f}")
        answer = "\n".join(lines) if drivers else "Global driver sample is unavailable."
    elif intent == "high_customers":
        lines = ["Highest model-predicted risk customers (preview):"]
        for row in evidence["high_priority"]:
            lines.append(
                f"- #{row['customer_index']}: {_pct(row['churn_probability'])} ({row['risk_level']})"
            )
        answer = "\n".join(lines)
    else:
        answer = (
            f"Portfolio summary from the production model:\n"
            f"- Customers scored: {dashboard['total_customers']:,}\n"
            f"- High risk: {dashboard['high_risk']:,}\n"
            f"- Medium risk: {dashboard['medium_risk']:,}\n"
            f"- Low risk: {dashboard['low_risk']:,}\n"
            f"- Average model-predicted probability: {_pct(dashboard['avg_churn_probability'])}\n"
            f"- Top model driver (sample): "
            f"{(dashboard.get('top_drivers') or [{}])[0].get('feature', 'n/a')}"
        )

    return {
        "mode": "portfolio",
        "answer": answer,
        "evidence": evidence,
        "source": "deterministic",
    }


def _maybe_llm_polish(message: str, grounded: dict[str, Any]) -> dict[str, Any]:
    """Optional LLM phrasing only — numbers must stay from grounded evidence."""
    provider = llm_provider_name()
    if provider is None:
        grounded["llm_status"] = "unavailable"
        return grounded

    system = (
        "You are RETENSA's retention assistant. Rephrase the provided grounded answer "
        "in clear business language. Do NOT invent numbers, customers, SHAP values, "
        "discounts, or guarantees. Copy all numeric values exactly from the evidence. "
        "Return plain text only."
    )
    payload = {
        "user_message": message,
        "grounded_answer": grounded["answer"],
        "evidence": grounded["evidence"],
    }
    try:
        if provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=20.0)
            completion = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, default=str)},
                ],
            )
            text = (completion.choices[0].message.content or "").strip()
        else:
            import anthropic

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=20.0)
            message_out = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
                max_tokens=700,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": json.dumps(payload, default=str)}],
            )
            text = "".join(
                block.text for block in message_out.content if getattr(block, "text", None)
            ).strip()
        if text:
            grounded = dict(grounded)
            grounded["answer"] = text
            grounded["source"] = "llm_language"
            grounded["llm_status"] = "ok"
            grounded["provider"] = provider
            return grounded
    except Exception as exc:
        grounded = dict(grounded)
        grounded["llm_status"] = "unavailable"
        grounded["llm_error"] = str(exc)
        return grounded

    grounded["llm_status"] = "unavailable"
    return grounded


def answer_assistant(
    message: str,
    *,
    store,
    customer_index: Optional[int] = None,
    features: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    cleaned = (message or "").strip()
    if not cleaned:
        raise ValueError("message is required.")

    # Allow "customer 2203" style questions without explicit index.
    if customer_index is None and not features:
        match = re.search(r"(?:customer\s*#?\s*|#)(\d{1,5})\b", cleaned, re.I)
        if match:
            customer_index = int(match.group(1))

    intent = _intent(cleaned)

    if features:
        from api.new_customer import NewCustomerValidationError, validate_and_build_frame

        try:
            frame = validate_and_build_frame(features)
        except NewCustomerValidationError as exc:
            raise ValueError(str(exc)) from exc
        center = build_action_center(frame, include_llm=True)
        grounded = _customer_reply(
            intent if intent in {"why", "what_if", "recommend"} else "general",
            center,
            "New Customer",
        )
        return _maybe_llm_polish(cleaned, grounded)

    if customer_index is not None:
        if customer_index not in store.features.index:
            raise KeyError(customer_index)
        center = build_action_center(store.row(customer_index), include_llm=True)
        grounded = _customer_reply(
            intent if intent in {"why", "what_if", "recommend"} else "general",
            center,
            customer_index,
        )
        return _maybe_llm_polish(cleaned, grounded)

    if intent in {"why", "what_if", "recommend"}:
        return {
            "mode": "portfolio",
            "answer": (
                "I don't have enough information in the current RETENSA data to answer that "
                "without a selected customer. Open a dataset customer, analyze a new customer, "
                "or include a customer index."
            ),
            "evidence": {},
            "source": "deterministic",
            "llm_status": "skipped",
        }

    dashboard = store.dashboard()
    grounded = _portfolio_reply(intent, dashboard)
    return _maybe_llm_polish(cleaned, grounded)
