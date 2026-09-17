"""What-if simulator tests on a real cleaned-Telco customer."""

from __future__ import annotations

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame
from src.models.predict import predict_churn
from src.simulator.what_if import compare_scenarios, simulate_scenario
from src.utils.config import MODEL_PATH, TARGET_COLUMN


def _pick_month_to_month_high_risk(features):
    predictions = predict_churn(features, model_path=MODEL_PATH)
    mask = (
        (features["Contract"] == "Month-to-month")
        & (features["InternetService"] != "No")
        & (features["TechSupport"] == "No")
    )
    ranked = predictions.loc[mask].sort_values("churn_probability", ascending=False)
    if ranked.empty:
        return int(features.index[0])
    return int(ranked.index[0])


def _print_invalid(title: str, result: dict) -> None:
    print(f"\n{title}")
    print(f"valid={result.get('valid')}  error={result.get('error')}")


def main() -> None:
    df = load_cleaned_dataset()
    features = prepare_feature_frame(df.drop(columns=[TARGET_COLUMN], errors="ignore"))
    index = _pick_month_to_month_high_risk(features)
    customer = features.loc[[index]]
    tech_value = "Yes"

    result = simulate_scenario(customer, {"Contract": "One year"})
    if not result.get("valid"):
        raise RuntimeError(f"Expected a valid Contract scenario, got {result}")

    original = result["original"]
    scenario = result["scenario"]
    impact = result["impact"]
    contract_change = scenario["changes"]["Contract"]

    print("=" * 40)
    print("RETENSA WHAT-IF SIMULATOR")
    print("=" * 40)
    print(f"\nCustomer index: {index}")
    print("\nORIGINAL")
    print(f"\nChurn probability: {original['churn_probability'] * 100:.2f}%")
    print(f"Risk level: {original['risk_level']}")
    print("\nSCENARIO")
    print("\nContract:")
    print(f"{contract_change['from']} → {contract_change['to']}")
    print(f"\nNew churn probability: {scenario['churn_probability'] * 100:.2f}%")
    print(f"New risk level: {scenario['risk_level']}")
    print("\nMODEL-SIMULATED CHANGE:")
    print(f"{impact['probability_change_percentage_points']:.2f} percentage points")
    print("\n" + "=" * 40)

    scenarios = [
        {"name": "Change Contract", "changes": {"Contract": "One year"}},
        {"name": "Add Tech Support", "changes": {"TechSupport": tech_value}},
        {
            "name": "Contract + Tech Support",
            "changes": {"Contract": "One year", "TechSupport": tech_value},
        },
    ]
    comparison = compare_scenarios(customer, scenarios)
    print("\nScenario comparison (model-simulated impact, not guaranteed behavior)")
    print(
        f"{'Scenario':<26} {'Old Risk':<10} {'New Risk':<10} "
        f"{'Old P':>8} {'New P':>8} {'Delta':>8}"
    )
    for row in comparison:
        if not row.get("valid"):
            print(f"{row['name']:<26} INVALID: {row.get('error')}")
            continue
        print(
            f"{row['name']:<26} {row['original_risk']:<10} {row['new_risk']:<10} "
            f"{row['original_probability']*100:7.2f}% "
            f"{row['new_probability']*100:7.2f}% "
            f"{row['delta']*100:7.2f}"
        )

    print("\nInvalid input tests")
    _print_invalid("Unknown feature", simulate_scenario(customer, {"FakeFeature": "Yes"}))
    _print_invalid("Invalid Contract", simulate_scenario(customer, {"Contract": "Five Year"}))
    _print_invalid("Invalid tenure", simulate_scenario(customer, {"tenure": "hello"}))
    _print_invalid(
        "Contradictory phone/lines",
        simulate_scenario(customer, {"PhoneService": "No", "MultipleLines": "Yes"}),
    )


if __name__ == "__main__":
    main()
