"""Production XGBoost baseline metrics for the Model Performance page."""

from __future__ import annotations

import json
from typing import Any, Optional

from src.utils.config import BASELINE_METRICS_PATH, MODEL_PATH, RANDOM_SEED, TEST_SIZE


def load_model_metrics(dataset_size: Optional[int] = None) -> dict[str, Any]:
    if not BASELINE_METRICS_PATH.exists():
        raise FileNotFoundError(f"Missing baseline metrics file: {BASELINE_METRICS_PATH}")

    raw = json.loads(BASELINE_METRICS_PATH.read_text())
    matrix = raw.get("confusion_matrix") or {}
    n = int(dataset_size) if dataset_size is not None else 7021
    test_size = int(round(n * TEST_SIZE))
    # Stratified 80/20 on 7021 rows yields 1405 test / 5616 train.
    if n == 7021:
        test_size = 1405
        train_size = 5616
        train_churn = 1485
        train_non_churn = 4131
        test_churn = 372
        test_non_churn = 1033
    else:
        train_size = n - test_size
        train_churn = train_non_churn = test_churn = test_non_churn = None

    return {
        "model": "XGBoost",
        "model_file": MODEL_PATH.name,
        "accuracy": float(raw["accuracy"]),
        "precision": float(raw["precision"]),
        "recall": float(raw["recall"]),
        "f1": float(raw["f1"]),
        "roc_auc": float(raw["roc_auc"]),
        "confusion_matrix": {
            "true_negative": int(matrix.get("tn", matrix.get("true_negative", 0))),
            "false_positive": int(matrix.get("fp", matrix.get("false_positive", 0))),
            "false_negative": int(matrix.get("fn", matrix.get("false_negative", 0))),
            "true_positive": int(matrix.get("tp", matrix.get("true_positive", 0))),
        },
        "dataset_size": n,
        "train_size": train_size,
        "test_size": test_size,
        "split": "80/20 stratified",
        "random_state": RANDOM_SEED,
        "train_distribution": {
            "non_churn": train_non_churn,
            "churn": train_churn,
        },
        "test_distribution": {
            "non_churn": test_non_churn,
            "churn": test_churn,
        },
        "metric_explanations": {
            "accuracy": "The proportion of test predictions that were correct.",
            "precision": "Among customers predicted as churners, the proportion that actually churned.",
            "recall": "Among actual churners, the proportion correctly identified.",
            "f1": "The balance between precision and recall.",
            "roc_auc": "Measures how well the model separates churners from non-churners across classification thresholds.",
        },
        "note": (
            "These are held-out test metrics for the production XGBoost baseline "
            f"({MODEL_PATH.name}). Optimized/HGB artifacts are not production."
        ),
    }
