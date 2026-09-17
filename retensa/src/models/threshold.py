"""Decision-threshold wrapper chosen from training-set OOF scores only."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.utils.validation import check_is_fitted


class ThresholdedClassifier(BaseEstimator, ClassifierMixin):
    """Apply a fixed probability cutoff on top of a fitted classifier.

    `predict_proba` is unchanged. `predict` uses `threshold` instead of 0.5.
    """

    def __init__(self, estimator=None, threshold: float = 0.5):
        self.estimator = estimator
        self.threshold = threshold

    def fit(self, X, y):
        if self.estimator is None:
            raise ValueError("ThresholdedClassifier requires an estimator.")
        self.estimator_ = clone(self.estimator)
        self.estimator_.fit(X, y)
        classes = getattr(self.estimator_, "classes_", np.array([0, 1]))
        self.classes_ = np.asarray(classes)
        return self

    def predict_proba(self, X):
        check_is_fitted(self, "estimator_")
        return self.estimator_.predict_proba(X)

    def predict(self, X):
        proba = self.predict_proba(X)
        positive_index = list(self.classes_).index(1) if 1 in self.classes_ else 1
        return (proba[:, positive_index] >= self.threshold).astype(int)


def unwrap_estimator(model):
    """Return the inner classifier when a threshold wrapper is present."""
    if isinstance(model, ThresholdedClassifier):
        if hasattr(model, "estimator_"):
            return model.estimator_
        return model.estimator
    return model


def select_operating_threshold(
    y_true,
    y_proba,
    thresholds: np.ndarray | None = None,
    min_recall: float = 0.50,
) -> dict:
    """Pick a cutoff from training/OOF scores only.

    Maximises F1 among thresholds that keep churn recall at least `min_recall`,
    so a high-precision / near-zero-recall cutoff cannot win.
    """
    y_true = np.asarray(y_true)
    y_proba = np.asarray(y_proba)
    if thresholds is None:
        thresholds = np.round(np.linspace(0.30, 0.70, 9), 2)

    grid = []
    for threshold in thresholds:
        y_pred = (y_proba >= threshold).astype(int)
        row = {
            "threshold": float(threshold),
            "accuracy": float(accuracy_score(y_true, y_pred)),
            "precision": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
            "f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        }
        grid.append(row)

    eligible = [row for row in grid if row["recall"] >= min_recall]
    pool = eligible if eligible else grid
    best = max(pool, key=lambda row: (row["f1"], row["recall"], -abs(row["threshold"] - 0.5)))
    return {"best": best, "grid": grid, "min_recall": min_recall}
