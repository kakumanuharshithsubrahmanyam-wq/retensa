"""Action Center test on a real Telco customer."""

from __future__ import annotations

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame
from src.models.predict import predict_churn
from src.recommendations.action_center import build_action_center, format_action_center_report
from src.utils.config import MODEL_PATH, TARGET_COLUMN


def main() -> None:
    df = load_cleaned_dataset()
    features = prepare_feature_frame(df.drop(columns=[TARGET_COLUMN], errors="ignore"))
    predictions = predict_churn(features, model_path=MODEL_PATH)
    mask = (
        (features["Contract"] == "Month-to-month")
        & (features["InternetService"] != "No")
        & (features["TechSupport"] == "No")
    )
    ranked = predictions.loc[mask].sort_values("churn_probability", ascending=False)
    index = int(ranked.index[0])
    customer = features.loc[[index]]
    center = build_action_center(customer, include_llm=True)
    print(format_action_center_report(center))
    context = center["llm_context"]
    print("\nLLM context keys:", sorted(context.keys()))
    assert "churn_probability" in context
    assert context["churn_probability"] == center["risk"]["probability"]
    print(f"\nAction Center assembled for customer {index}.")


if __name__ == "__main__":
    main()
