"""CV-based Phase 1 optimization. Does not overwrite the baseline joblib."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from shutil import copy2

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import split_features_and_target
from src.models.evaluate import classification_metrics
from src.models.selection import oof_positive_probabilities, search_candidates, select_winner
from src.models.threshold import ThresholdedClassifier, select_operating_threshold
from src.utils.config import (
    BASELINE_METRICS_PATH,
    BASELINE_MODEL_PATH,
    FEATURE_COLUMNS,
    METADATA_PATH,
    MODEL_PATH,
    OPTIMIZED_MODEL_PATH,
    RANDOM_SEED,
    TEST_SIZE,
)

FORBIDDEN_COLUMNS = {
    "predicted_churn",
    "churn_probability",
    "risk_level",
    "churn_score",
    "churn_value",
    "churn_reason",
}


def set_reproducible_seed(seed: int = RANDOM_SEED) -> None:
    np.random.seed(seed)


def preserve_baseline() -> None:
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists() and not BASELINE_MODEL_PATH.exists():
        copy2(MODEL_PATH, BASELINE_MODEL_PATH)
        print(f"Copied baseline pipeline to {BASELINE_MODEL_PATH}")
    elif BASELINE_MODEL_PATH.exists():
        print(f"Baseline already preserved at {BASELINE_MODEL_PATH}")
    else:
        raise FileNotFoundError(
            f"No baseline model at {MODEL_PATH}. Run Phase 1 training first."
        )


def load_baseline_metrics() -> dict:
    if BASELINE_METRICS_PATH.exists():
        return json.loads(BASELINE_METRICS_PATH.read_text())
    raise FileNotFoundError(f"Missing baseline metrics at {BASELINE_METRICS_PATH}")


def print_comparison_table(rows: list[dict]) -> None:
    print("\n" + "=" * 60)
    print("CROSS-VALIDATION COMPARISON (training folds only)")
    print("=" * 60)
    header = (
        f"{'Model':<38} {'Acc':>6} {'Prec':>6} {'Rec':>6} {'F1':>6} "
        f"{'AUC':>6} {'Std':>6} {'Gap':>6} {'Risk':>8}"
    )
    print(header)
    print("-" * len(header))
    for row in sorted(rows, key=lambda item: item["selection_score"], reverse=True):
        print(
            f"{row['name']:<38} "
            f"{row['cv_accuracy']:.3f} "
            f"{row['cv_precision']:.3f} "
            f"{row['cv_recall']:.3f} "
            f"{row['cv_f1']:.3f} "
            f"{row['cv_roc_auc']:.3f} "
            f"{row['cv_roc_auc_std']:.3f} "
            f"{row['roc_auc_gap']:.3f} "
            f"{row['overfit_risk']:>8}"
        )


def print_threshold_table(threshold_result: dict) -> None:
    print("\n" + "=" * 60)
    print("THRESHOLD ANALYSIS (OOF training predictions only)")
    print("=" * 60)
    print(f"{'t':>6} {'Acc':>8} {'Prec':>8} {'Rec':>8} {'F1':>8}")
    for row in threshold_result["grid"]:
        marker = " <<" if row["threshold"] == threshold_result["best"]["threshold"] else ""
        print(
            f"{row['threshold']:6.2f} "
            f"{row['accuracy']:8.4f} "
            f"{row['precision']:8.4f} "
            f"{row['recall']:8.4f} "
            f"{row['f1']:8.4f}{marker}"
        )
    best = threshold_result["best"]
    print(
        f"\nSelected threshold={best['threshold']:.2f} "
        f"(OOF F1={best['f1']:.4f}, recall={best['recall']:.4f}, "
        f"min_recall={threshold_result['min_recall']:.2f})"
    )


def build_final_pipeline(winner: dict, threshold: float) -> Pipeline:
    unfitted = clone(winner["search"].best_estimator_)
    inner = unfitted.named_steps["model"]
    unfitted.steps[-1] = (
        "model",
        ThresholdedClassifier(estimator=inner, threshold=threshold),
    )
    return unfitted


def cm_value(cm: dict, short_key: str, long_key: str) -> int:
    return int(cm.get(short_key, cm.get(long_key)))


def print_final_report(
    baseline: dict,
    optimized: dict,
    winner: dict,
    threshold: float,
    train_auc: float,
) -> None:
    opt_cm = optimized["confusion_matrix"]
    base_cm = baseline["confusion_matrix"]
    print("\n" + "=" * 40)
    print("RETENSA MODEL OPTIMIZATION")
    print("=" * 40)
    print("\nBASELINE")
    print(f"Accuracy:  {baseline['accuracy']:.4f}")
    print(f"Precision: {baseline['precision']:.4f}")
    print(f"Recall:    {baseline['recall']:.4f}")
    print(f"F1:        {baseline['f1']:.4f}")
    print(f"ROC-AUC:   {baseline['roc_auc']:.4f}")
    print("\nOPTIMIZED")
    print(f"Accuracy:  {optimized['accuracy']:.4f}")
    print(f"Precision: {optimized['precision']:.4f}")
    print(f"Recall:    {optimized['recall']:.4f}")
    print(f"F1:        {optimized['f1']:.4f}")
    print(f"ROC-AUC:   {optimized['roc_auc']:.4f}")
    print("\nCROSS-VALIDATION")
    print(f"Mean ROC-AUC: {winner['cv_roc_auc']:.4f}")
    print(f"Std ROC-AUC:  {winner['cv_roc_auc_std']:.4f}")
    print(f"Mean F1:      {winner['cv_f1']:.4f}")
    print("\nGENERALIZATION GAP")
    print(f"Train ROC-AUC:      {train_auc:.4f}")
    print(f"CV ROC-AUC:         {winner['cv_roc_auc']:.4f}")
    print(f"Final Test ROC-AUC: {optimized['roc_auc']:.4f}")
    print(f"\nSelected threshold: {threshold:.2f}")
    print("\nConfusion Matrix:")
    print(f"TN: {opt_cm['true_negative']}")
    print(f"FP: {opt_cm['false_positive']}")
    print(f"FN: {opt_cm['false_negative']}")
    print(f"TP: {opt_cm['true_positive']}")
    print("\nSide-by-side (untouched test set)")
    print(f"{'':<14}{'Baseline':>12}{'Optimized':>12}")
    for key, label in (
        ("accuracy", "Accuracy"),
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1"),
        ("roc_auc", "ROC-AUC"),
    ):
        print(f"{label:<14}{baseline[key]*100:11.1f}%{optimized[key]*100:11.1f}%")
    print("=" * 40)
    print(
        "Baseline CM TN/FP/FN/TP = "
        f"{cm_value(base_cm, 'tn', 'true_negative')}/"
        f"{cm_value(base_cm, 'fp', 'false_positive')}/"
        f"{cm_value(base_cm, 'fn', 'false_negative')}/"
        f"{cm_value(base_cm, 'tp', 'true_positive')}"
    )


def conclusion_text(baseline: dict, optimized: dict, winner: dict) -> str:
    improved = []
    declined = []
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        delta = optimized[key] - baseline[key]
        if delta > 0.002:
            improved.append(f"{key} (+{delta:.4f})")
        elif delta < -0.002:
            declined.append(f"{key} ({delta:.4f})")
    cv_test_gap = abs(winner["cv_roc_auc"] - optimized["roc_auc"])
    consistent = cv_test_gap <= 0.03
    replace = (
        winner["overfit_risk"] != "high"
        and consistent
        and optimized["f1"] >= baseline["f1"] - 0.005
        and optimized["roc_auc"] >= baseline["roc_auc"] - 0.005
        and (
            optimized["roc_auc"] > baseline["roc_auc"] + 0.002
            or optimized["f1"] > baseline["f1"] + 0.002
        )
    )
    improved_text = (
        "Yes on: " + ", ".join(improved) if improved else "No metric improved meaningfully."
    )
    decreased_text = f" Decreased: {', '.join(declined)}" if declined else ""
    return "\n".join(
        [
            f"* Did performance improve? {improved_text}{decreased_text}",
            f"* Selected model: {winner['name']}",
            "* Why: highest generalization score (CV ROC-AUC + F1, penalising "
            f"train/CV gap and fold std); overfit risk={winner['overfit_risk']}.",
            f"* Overfitting evidence: train-CV ROC-AUC gap={winner['roc_auc_gap']:.4f} "
            f"(train={winner['train_roc_auc']:.4f}, CV={winner['cv_roc_auc']:.4f}).",
            f"* Final test ROC-AUC {optimized['roc_auc']:.4f} vs CV {winner['cv_roc_auc']:.4f} "
            f"(|gap|={cv_test_gap:.4f}) — "
            + ("consistent with CV." if consistent else "larger than expected; inspect before replacing."),
            "* Production file models/churn_model.joblib was NOT overwritten. "
            + (
                "This candidate is eligible to replace the baseline after review."
                if replace
                else "Keep the baseline as production."
            ),
        ]
    )


def jsonable(value):
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def main() -> None:
    set_reproducible_seed()
    preserve_baseline()
    baseline_metrics = load_baseline_metrics()

    df = load_cleaned_dataset()
    leak_cols = [
        col
        for col in df.columns
        if col.lower().replace(" ", "_") in FORBIDDEN_COLUMNS
    ]
    if leak_cols:
        raise RuntimeError(f"Refusing to train with leakage columns present: {leak_cols}")

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

    print(
        "\nTrain/test split locked: "
        f"train={len(X_train)} test={len(X_test)}. "
        "The test set is unused until the final evaluation."
    )
    print(f"Train-only scale_pos_weight reference: {scale_pos_weight:.4f}")

    cv_results = search_candidates(X_train, y_train, scale_pos_weight=scale_pos_weight)
    print_comparison_table(cv_results)
    winner = select_winner(cv_results)
    print(f"\nLocked model from CV (test unseen): {winner['name']}")
    print(f"Best params: {winner['best_params']}")

    oof_proba = oof_positive_probabilities(winner["search"].best_estimator_, X_train, y_train)
    threshold_result = select_operating_threshold(y_train, oof_proba)
    print_threshold_table(threshold_result)
    threshold = float(threshold_result["best"]["threshold"])

    final_pipeline = build_final_pipeline(winner, threshold=threshold)
    final_pipeline.fit(X_train, y_train)

    train_pred = final_pipeline.predict(X_train)
    train_proba = final_pipeline.predict_proba(X_train)[:, 1]
    train_metrics = classification_metrics(y_train, train_pred, train_proba)

    test_pred = final_pipeline.predict(X_test)
    test_proba = final_pipeline.predict_proba(X_test)[:, 1]
    test_metrics = classification_metrics(y_test, test_pred, test_proba)

    OPTIMIZED_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, OPTIMIZED_MODEL_PATH)

    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "model_name": winner["name"],
        "model_type": type(final_pipeline.named_steps["model"].estimator_).__name__,
        "hyperparameters": winner["best_params"],
        "selected_threshold": threshold,
        "use_engineered_features": winner["use_engineered_features"],
        "feature_list": list(FEATURE_COLUMNS),
        "cv_metrics": {
            "accuracy": winner["cv_accuracy"],
            "precision": winner["cv_precision"],
            "recall": winner["cv_recall"],
            "f1": winner["cv_f1"],
            "roc_auc": winner["cv_roc_auc"],
            "roc_auc_std": winner["cv_roc_auc_std"],
            "overfit_risk": winner["overfit_risk"],
            "train_roc_auc": winner["train_roc_auc"],
            "roc_auc_gap": winner["roc_auc_gap"],
        },
        "train_metrics_after_final_fit": {
            "accuracy": train_metrics["accuracy"],
            "precision": train_metrics["precision"],
            "recall": train_metrics["recall"],
            "f1": train_metrics["f1"],
            "roc_auc": train_metrics["roc_auc"],
        },
        "final_test_metrics": test_metrics,
        "baseline_test_metrics": baseline_metrics,
        "production_model_replaced": False,
        "optimized_model_path": str(OPTIMIZED_MODEL_PATH),
        "baseline_model_path": str(BASELINE_MODEL_PATH),
        "threshold_grid": threshold_result["grid"],
    }
    METADATA_PATH.write_text(json.dumps(jsonable(metadata), indent=2))
    print(f"\nSaved optimized pipeline to {OPTIMIZED_MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")
    print(f"Production baseline left unchanged at {MODEL_PATH}")

    print_final_report(
        baseline_metrics,
        test_metrics,
        winner,
        threshold,
        train_auc=train_metrics["roc_auc"],
    )
    print("\nConclusion")
    print(conclusion_text(baseline_metrics, test_metrics, winner))


if __name__ == "__main__":
    main()
