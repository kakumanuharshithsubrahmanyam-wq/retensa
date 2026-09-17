"""Train the Phase 1 XGBoost churn baseline and save a reusable pipeline."""

from __future__ import annotations

import json

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.data.inspect_data import print_data_quality_report
from src.data.load import load_cleaned_dataset
from src.data.preprocessing import build_preprocessor, split_features_and_target
from src.models.predict import predict_churn
from src.utils.config import MODEL_PATH, RANDOM_SEED, TEST_SIZE


def set_reproducible_seed(seed: int = RANDOM_SEED) -> None:
    np.random.seed(seed)


def build_classifier(scale_pos_weight: float) -> XGBClassifier:
    return XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=1,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        n_jobs=1,
        verbosity=0,
    )


def evaluate_model(pipeline: Pipeline, X_test, y_test) -> dict:
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1])

    metrics = {
        "n_test_samples": int(len(y_test)),
        "n_churn_cases": int((y_test == 1).sum()),
        "n_non_churn_cases": int((y_test == 0).sum()),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_proba)),
        "confusion_matrix": {
            "labels": ["non-churn (0)", "churn (1)"],
            "matrix": cm.tolist(),
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1]),
        },
    }
    return metrics, y_pred, y_proba


def print_evaluation(metrics: dict, y_test, y_pred) -> None:
    print("\n" + "=" * 60)
    print("Test-set evaluation")
    print("=" * 60)
    print(f"test samples: {metrics['n_test_samples']}")
    print(f"churn cases: {metrics['n_churn_cases']}")
    print(f"non-churn cases: {metrics['n_non_churn_cases']}")
    print(f"accuracy:  {metrics['accuracy']:.4f}")
    print(f"precision: {metrics['precision']:.4f}")
    print(f"recall:    {metrics['recall']:.4f}")
    print(f"f1-score:  {metrics['f1']:.4f}")
    print(f"roc-auc:   {metrics['roc_auc']:.4f}")
    cm = metrics["confusion_matrix"]
    print("\nConfusion matrix [rows=true 0/1, cols=pred 0/1]:")
    print(f"TN={cm['true_negative']}  FP={cm['false_positive']}")
    print(f"FN={cm['false_negative']}  TP={cm['true_positive']}")
    print("\nClassification report:")
    print(classification_report(y_test, y_pred, target_names=["non-churn", "churn"], digits=4))


def main() -> None:
    set_reproducible_seed()

    df = load_cleaned_dataset()
    print_data_quality_report(df)

    X, y = split_features_and_target(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        stratify=y,
        random_state=RANDOM_SEED,
    )

    n_neg = int((y_train == 0).sum())
    n_pos = int((y_train == 1).sum())
    scale_pos_weight = n_neg / n_pos if n_pos else 1.0

    print("\n" + "=" * 60)
    print("Train/test split")
    print("=" * 60)
    print(f"train size: {len(X_train)}  test size: {len(X_test)}")
    print(f"train churn: {n_pos} ({n_pos / len(y_train):.2%})  non-churn: {n_neg}")
    print(f"test churn: {(y_test == 1).sum()}  non-churn: {(y_test == 0).sum()}")
    print(f"scale_pos_weight (train only): {scale_pos_weight:.4f}")

    pipeline = Pipeline(
        steps=[
            ("preprocessor", build_preprocessor()),
            ("model", build_classifier(scale_pos_weight=scale_pos_weight)),
        ]
    )
    pipeline.fit(X_train, y_train)

    metrics, y_pred, _y_proba = evaluate_model(pipeline, X_test, y_test)
    print_evaluation(metrics, y_test, y_pred)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODEL_PATH)
    print(f"\nSaved preprocessing + model pipeline to: {MODEL_PATH}")

    sample = X_test.head(5)
    sample_predictions = predict_churn(sample, pipeline=pipeline)
    sample_predictions["actual_churn"] = y_test.loc[sample.index].values
    print("\n" + "=" * 60)
    print("Example predictions (first 5 test customers)")
    print("=" * 60)
    print(sample_predictions.to_string(index=True, float_format=lambda v: f"{v:.4f}"))

    print("\nMetrics JSON:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
