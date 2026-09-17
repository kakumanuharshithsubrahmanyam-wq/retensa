"""Run Phase 2 SHAP checks on real customers from the cleaned Telco CSV."""

from __future__ import annotations

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame
from src.explainability.plots import save_global_importance_plot, save_local_explanation_plot
from src.explainability.shap_explainer import (
    SHAP_SAMPLE_SIZE,
    ShapExplainer,
    explain_customer,
    get_customer_explanation,
    get_global_feature_importance,
)
from src.models.predict import predict_churn
from src.utils.config import RANDOM_SEED, TARGET_COLUMN


def _print_local_report(index: int, explanation: dict) -> None:
    probability = explanation["churn_probability"]
    print("=" * 50)
    print("RETENSA PHASE 2 — SHAP TEST")
    print("=" * 50)
    print(f"\nCustomer index: {index}")
    print(f"\nChurn probability: {probability * 100:.2f}%")
    print(f"Risk level: {explanation['risk_level']}")
    print(f"SHAP base value: {explanation['base_value']:.4f}")
    print(f"SHAP output space: {explanation['shap_output_space']}")
    print(
        "\nNote: SHAP values are contributions in the model output space; "
        "they are not probability percentage points."
    )

    print("\nTop factors increasing churn:\n")
    risk_factors = explanation["top_risk_factors"]
    if not risk_factors:
        print("None")
    else:
        for i, item in enumerate(risk_factors, start=1):
            print(f"{i}. {item['feature']:<20} {item['shap_value']:+.4f}")

    print("\nTop factors decreasing churn:\n")
    protective = explanation["protective_factors"]
    if not protective:
        print("None")
    else:
        for i, item in enumerate(protective, start=1):
            print(f"{i}. {item['feature']:<20} {item['shap_value']:+.4f}")
    print("\n" + "=" * 50)


def main() -> None:
    df = load_cleaned_dataset()
    features = prepare_feature_frame(df.drop(columns=[TARGET_COLUMN], errors="ignore"))
    explainer = ShapExplainer()

    predictions = predict_churn(features, pipeline=explainer.pipeline)
    if TARGET_COLUMN in predictions.columns or "Churn Probability" in features.columns:
        raise RuntimeError("Leakage check failed: prediction columns appeared in features.")

    sample_indexes = []
    for label, mask in (
        ("high", predictions["churn_probability"] > 0.70),
        ("medium", predictions["churn_probability"].between(0.30, 0.70)),
        ("low", predictions["churn_probability"] < 0.30),
    ):
        matches = predictions.index[mask]
        if len(matches) == 0:
            print(f"No {label}-risk customers found in the dataset.")
            continue
        sample_indexes.append(int(matches[0]))

    if not sample_indexes:
        sample_indexes = [int(features.index[0])]

    print("\nPhase 1 prediction check (first sampled customer):")
    first = features.loc[[sample_indexes[0]]]
    print(predict_churn(first, pipeline=explainer.pipeline).to_string(index=True))

    for index in sample_indexes:
        customer = features.loc[[index]]
        explanation = get_customer_explanation(customer, top_n=5, explainer=explainer)
        _print_local_report(index, explanation)
        contributions = explain_customer(customer, explainer=explainer)
        assert contributions, "Local SHAP explanation returned no factors."

    importance = get_global_feature_importance(
        features,
        top_n=10,
        sample_size=SHAP_SAMPLE_SIZE,
        random_state=RANDOM_SEED,
        explainer=explainer,
    )
    print("\n" + "=" * 50)
    print("GLOBAL SHAP IMPORTANCE")
    print("=" * 50)
    print(f"\nSample size: {min(SHAP_SAMPLE_SIZE, len(features))}  random_state={RANDOM_SEED}\n")
    for i, row in enumerate(importance, start=1):
        print(f"{i}. {row['feature']:<20} {row['importance']:.4f}")
    print("\n" + "=" * 50)

    try:
        global_plot = save_global_importance_plot(importance)
        local_plot = save_local_explanation_plot(
            explain_customer(features.loc[[sample_indexes[0]]], explainer=explainer)
        )
        print(f"\nSaved plots:\n- {global_plot}\n- {local_plot}")
    except Exception as exc:
        print(f"\nPlot generation skipped: {exc}")


if __name__ == "__main__":
    main()
