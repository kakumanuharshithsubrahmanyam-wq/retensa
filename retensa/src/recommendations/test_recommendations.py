"""Deterministic recommendation tests on a real Telco customer."""

from __future__ import annotations

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame
from src.models.predict import predict_churn
from src.recommendations.engine import generate_recommendation
from src.recommendations.llm import build_llm_context, generate_retention_plan, llm_provider_name
from src.recommendations.action_plan import generate_action_plan
from src.simulator.what_if import compare_scenarios
from src.utils.config import MODEL_PATH, TARGET_COLUMN


def _pick_customer(features):
    predictions = predict_churn(features, model_path=MODEL_PATH)
    mask = (
        (features["Contract"] == "Month-to-month")
        & (features["InternetService"] != "No")
        & (features["TechSupport"] == "No")
    )
    ranked = predictions.loc[mask].sort_values("churn_probability", ascending=False)
    return int(ranked.index[0])


def main() -> None:
    df = load_cleaned_dataset()
    features = prepare_feature_frame(df.drop(columns=[TARGET_COLUMN], errors="ignore"))
    index = _pick_customer(features)
    customer = features.loc[[index]]
    recs = generate_recommendation(customer)
    plan = generate_action_plan(customer)

    print("=" * 40)
    print("RETENSA RECOMMENDATION TEST")
    print("=" * 40)
    print(f"\nCustomer index: {index}")
    print(f"Churn probability: {recs['customer_probability'] * 100:.2f}%")
    print(f"Risk level: {recs['risk_level']}")
    print(f"Primary model driver: {recs['primary_driver']}")
    print(f"Retention priority: {recs['retention_priority']}")
    print("\nRecommendations:")
    for item in recs["recommendations"]:
        evidence = item["evidence"]
        delta = evidence.get("delta_percentage_points")
        delta_text = f"  what-if {delta:.2f} pp" if delta is not None else ""
        print(
            f"- [{item['priority']}] {item['action']} "
            f"(driver={item['feature']}, SHAP={evidence['shap_value']:.4f}){delta_text}"
        )
    print("\nImmediate action:")
    print(plan["immediate_action"])
    if plan["model_simulated_impact"]:
        impact = plan["model_simulated_impact"]
        print(
            "\nTop intervention model-simulated impact: "
            f"{impact['current_probability']*100:.2f}% → {impact['scenario_probability']*100:.2f}% "
            f"({impact['delta_percentage_points']:.2f} percentage points)"
        )

    scenarios = compare_scenarios(
        customer,
        [
            {"name": "Change Contract", "changes": {"Contract": "One year"}},
            {"name": "Add Tech Support", "changes": {"TechSupport": "Yes"}},
        ],
    )
    context = build_llm_context(recs, plan, scenarios)
    forbidden = {"Churn", "name", "email", "phone", "address", "CustomerID"}
    assert forbidden.isdisjoint(set(context.keys()))
    assert "churn_probability" in context
    assert context["churn_probability"] == recs["customer_probability"]

    provider = llm_provider_name()
    llm_result = generate_retention_plan(context)
    if provider is None:
        print("\nLLM enabled: no")
        print("Deterministic fallback: yes")
        assert llm_result["recommendation_source"] == "deterministic"
    else:
        print(f"\nLLM enabled: yes ({provider})")
        print(f"LLM status: {llm_result['llm_status']}")
        print(f"Source: {llm_result['recommendation_source']}")
    print("\nRetention plan summary:")
    print(llm_result["retention_plan"]["summary"])
    print(llm_result["retention_plan"]["caution"])


if __name__ == "__main__":
    main()
