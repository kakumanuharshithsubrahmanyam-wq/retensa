"""Root-cause test on a real cleaned-Telco customer."""

from __future__ import annotations

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame
from src.models.predict import predict_churn
from src.risk.root_cause import analyze_root_cause, generate_root_cause_summary
from src.utils.config import MODEL_PATH, TARGET_COLUMN


def main() -> None:
    df = load_cleaned_dataset()
    features = prepare_feature_frame(df.drop(columns=[TARGET_COLUMN], errors="ignore"))
    predictions = predict_churn(features, model_path=MODEL_PATH)
    high = predictions.index[predictions["churn_probability"] > 0.70]
    index = int(high[0]) if len(high) else int(features.index[0])
    customer = features.loc[[index]]

    result = analyze_root_cause(customer, top_n=5)
    summary = generate_root_cause_summary(customer, top_n=3)

    print("=" * 40)
    print("RETENSA ROOT CAUSE TEST")
    print("=" * 40)
    print(f"\nCustomer index: {result['customer_index']}")
    print(f"\nChurn probability: {result['churn_probability'] * 100:.2f}%")
    print(f"Risk level: {result['risk_level']}")
    primary = result["primary_root_cause"]
    print("\nPrimary model driver:")
    print(primary["feature"] if primary else "None")
    print("\nRisk factors:\n")
    for i, item in enumerate(result["risk_factors"], start=1):
        print(f"{i}. {item['feature']}")
    print("\nProtective factors:\n")
    if not result["protective_factors"]:
        print("None")
    else:
        for i, item in enumerate(result["protective_factors"], start=1):
            print(f"{i}. {item['feature']}")
    print("\nRoot cause summary:")
    print(summary)
    print()


if __name__ == "__main__":
    main()
