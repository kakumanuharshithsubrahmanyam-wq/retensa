"""Train-only model comparison and hyperparameter search."""

from __future__ import annotations

import numpy as np
from scipy.stats import loguniform, randint, uniform
from sklearn.base import clone
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from src.data.preprocessing import build_preprocessor
from src.utils.config import RANDOM_SEED

N_CV_SPLITS = 5
N_ITER_LINEAR = 12
N_ITER_TREES = 18


def make_cv(random_state: int = RANDOM_SEED) -> StratifiedKFold:
    return StratifiedKFold(n_splits=N_CV_SPLITS, shuffle=True, random_state=random_state)


def _pipeline(estimator, use_engineered_features: bool) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocessor", build_preprocessor(use_engineered_features=use_engineered_features)),
            ("model", estimator),
        ]
    )


def candidate_specs(scale_pos_weight: float) -> list[dict]:
    """Search spaces. Scoring uses training folds only."""
    xgb_params = {
        "model__n_estimators": randint(80, 351),
        "model__max_depth": randint(3, 7),
        "model__learning_rate": loguniform(0.03, 0.15),
        "model__subsample": uniform(0.6, 0.3),
        "model__colsample_bytree": uniform(0.6, 0.3),
        "model__min_child_weight": randint(1, 9),
        "model__gamma": uniform(0.0, 3.0),
        "model__reg_lambda": loguniform(0.5, 10.0),
        "model__reg_alpha": loguniform(1e-4, 1.0),
        "model__scale_pos_weight": [
            1.0,
            float(np.sqrt(scale_pos_weight)),
            float(scale_pos_weight),
        ],
    }
    return [
        {
            "name": "logreg_balanced_engineered",
            "use_engineered_features": True,
            "estimator": LogisticRegression(
                class_weight="balanced",
                max_iter=2000,
                solver="lbfgs",
                random_state=RANDOM_SEED,
            ),
            "n_iter": N_ITER_LINEAR,
            "param_distributions": {"model__C": loguniform(1e-3, 10)},
        },
        {
            "name": "random_forest_balanced_engineered",
            "use_engineered_features": True,
            "estimator": RandomForestClassifier(
                class_weight="balanced",
                random_state=RANDOM_SEED,
                n_jobs=1,
            ),
            "n_iter": N_ITER_TREES,
            "param_distributions": {
                "model__n_estimators": randint(150, 351),
                "model__max_depth": [6, 8, 10, 12],
                "model__min_samples_leaf": randint(2, 16),
                "model__max_features": ["sqrt", "log2"],
            },
        },
        {
            "name": "hist_gradient_boosting_engineered",
            "use_engineered_features": True,
            "estimator": HistGradientBoostingClassifier(
                class_weight="balanced",
                random_state=RANDOM_SEED,
            ),
            "n_iter": N_ITER_TREES,
            "param_distributions": {
                "model__max_depth": [3, 4, 5, 6],
                "model__learning_rate": loguniform(0.03, 0.15),
                "model__max_iter": randint(120, 301),
                "model__l2_regularization": loguniform(1e-2, 10),
                "model__min_samples_leaf": randint(15, 51),
            },
        },
        {
            "name": "xgboost_weighted_original",
            "use_engineered_features": False,
            "estimator": XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                scale_pos_weight=scale_pos_weight,
                random_state=RANDOM_SEED,
                n_jobs=1,
                verbosity=0,
            ),
            "n_iter": N_ITER_TREES,
            "param_distributions": xgb_params,
        },
        {
            "name": "xgboost_weighted_engineered",
            "use_engineered_features": True,
            "estimator": XGBClassifier(
                objective="binary:logistic",
                eval_metric="logloss",
                scale_pos_weight=scale_pos_weight,
                random_state=RANDOM_SEED,
                n_jobs=1,
                verbosity=0,
            ),
            "n_iter": N_ITER_TREES,
            "param_distributions": xgb_params,
        },
    ]


def _in_sample_metrics(estimator, X, y) -> dict:
    proba = estimator.predict_proba(X)[:, 1]
    pred = estimator.predict(X)
    return {
        "train_accuracy": float(accuracy_score(y, pred)),
        "train_precision": float(precision_score(y, pred, pos_label=1, zero_division=0)),
        "train_recall": float(recall_score(y, pred, pos_label=1, zero_division=0)),
        "train_f1": float(f1_score(y, pred, pos_label=1, zero_division=0)),
        "train_roc_auc": float(roc_auc_score(y, proba)),
    }


def _overfit_risk(train_auc: float, cv_auc: float, cv_std: float) -> str:
    gap = train_auc - cv_auc
    if gap >= 0.08 or cv_std >= 0.03:
        return "high"
    if gap >= 0.04 or cv_std >= 0.02:
        return "medium"
    return "low"


def _selection_score(row: dict) -> float:
    gap = max(0.0, row["train_roc_auc"] - row["cv_roc_auc"] - 0.03)
    return (
        row["cv_roc_auc"]
        + 0.35 * row["cv_f1"]
        - 0.75 * gap
        - 0.5 * row["cv_roc_auc_std"]
    )


def search_candidates(X_train, y_train, scale_pos_weight: float) -> list[dict]:
    cv = make_cv()
    scoring = {
        "roc_auc": "roc_auc",
        "accuracy": "accuracy",
        "precision": "precision",
        "recall": "recall",
        "f1": "f1",
    }
    results = []
    for spec in candidate_specs(scale_pos_weight):
        pipeline = _pipeline(spec["estimator"], spec["use_engineered_features"])
        search = RandomizedSearchCV(
            estimator=pipeline,
            param_distributions=spec["param_distributions"],
            n_iter=spec["n_iter"],
            scoring=scoring,
            refit="roc_auc",
            cv=cv,
            random_state=RANDOM_SEED,
            n_jobs=-1,
            verbose=1,
        )
        search.fit(X_train, y_train)
        idx = search.best_index_
        cv_roc_auc = float(search.cv_results_["mean_test_roc_auc"][idx])
        cv_roc_std = float(search.cv_results_["std_test_roc_auc"][idx])
        train_metrics = _in_sample_metrics(search.best_estimator_, X_train, y_train)
        row = {
            "name": spec["name"],
            "search": search,
            "use_engineered_features": spec["use_engineered_features"],
            "cv_accuracy": float(search.cv_results_["mean_test_accuracy"][idx]),
            "cv_precision": float(search.cv_results_["mean_test_precision"][idx]),
            "cv_recall": float(search.cv_results_["mean_test_recall"][idx]),
            "cv_f1": float(search.cv_results_["mean_test_f1"][idx]),
            "cv_roc_auc": cv_roc_auc,
            "cv_roc_auc_std": cv_roc_std,
            "cv_f1_std": float(search.cv_results_["std_test_f1"][idx]),
            "best_params": _jsonable(search.best_params_),
            **train_metrics,
        }
        row["roc_auc_gap"] = row["train_roc_auc"] - row["cv_roc_auc"]
        row["overfit_risk"] = _overfit_risk(row["train_roc_auc"], cv_roc_auc, cv_roc_std)
        row["selection_score"] = _selection_score(row)
        results.append(row)
        print(
            f"{spec['name']}: CV ROC-AUC={cv_roc_auc:.4f}±{cv_roc_std:.4f}  "
            f"CV F1={row['cv_f1']:.4f}  train AUC={row['train_roc_auc']:.4f}  "
            f"gap={row['roc_auc_gap']:.4f}  risk={row['overfit_risk']}"
        )
    return results


def select_winner(results: list[dict]) -> dict:
    if not results:
        raise ValueError("No candidate results to select from.")
    preferred = [row for row in results if row["overfit_risk"] != "high"]
    pool = preferred if preferred else results
    return max(pool, key=lambda row: row["selection_score"])


def oof_positive_probabilities(estimator, X_train, y_train) -> np.ndarray:
    cv = make_cv()
    proba = cross_val_predict(
        clone(estimator),
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=-1,
    )
    return proba[:, 1]


def _jsonable(value):
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    return value
