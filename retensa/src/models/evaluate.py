"""Shared classification metrics for Phase 1 training and optimization."""

from __future__ import annotations

from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(y_true, y_pred, y_proba) -> dict:
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "n_samples": int(len(y_true)),
        "n_churn_cases": int((y_true == 1).sum()),
        "n_non_churn_cases": int((y_true == 0).sum()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "confusion_matrix": {
            "labels": ["non-churn (0)", "churn (1)"],
            "matrix": cm.tolist(),
            "true_negative": int(cm[0, 0]),
            "false_positive": int(cm[0, 1]),
            "false_negative": int(cm[1, 0]),
            "true_positive": int(cm[1, 1]),
        },
    }


def evaluate_model(pipeline, X, y) -> tuple[dict, object, object]:
    y_pred = pipeline.predict(X)
    y_proba = pipeline.predict_proba(X)[:, 1]
    return classification_metrics(y, y_pred, y_proba), y_pred, y_proba


def print_evaluation(title: str, metrics: dict, y_true=None, y_pred=None) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    if "n_samples" in metrics:
        print(f"samples: {metrics['n_samples']}")
    if "n_churn_cases" in metrics:
        print(f"churn cases: {metrics['n_churn_cases']}")
        print(f"non-churn cases: {metrics['n_non_churn_cases']}")
    print(f"accuracy:  {metrics['accuracy']:.4f}")
    print(f"precision: {metrics['precision']:.4f}")
    print(f"recall:    {metrics['recall']:.4f}")
    print(f"f1-score:  {metrics['f1']:.4f}")
    print(f"roc-auc:   {metrics['roc_auc']:.4f}")
    cm = metrics.get("confusion_matrix")
    if cm:
        print("\nConfusion matrix [rows=true 0/1, cols=pred 0/1]:")
        print(f"TN={cm['true_negative']}  FP={cm['false_positive']}")
        print(f"FN={cm['false_negative']}  TP={cm['true_positive']}")
    if y_true is not None and y_pred is not None:
        print("\nClassification report:")
        print(classification_report(y_true, y_pred, target_names=["non-churn", "churn"], digits=4))
