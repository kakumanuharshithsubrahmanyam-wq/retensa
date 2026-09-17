"""In-memory customer scoring cache. Predictions only — no SHAP on the full table."""

from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd

from src.data.load import load_cleaned_dataset
from src.data.preprocessing import prepare_feature_frame, split_features_and_target
from src.explainability.shap_explainer import ShapExplainer, get_global_feature_importance
from src.models.predict import load_churn_pipeline, predict_churn
from src.risk.segmentation import risk_level_from_probability
from src.utils.config import CATEGORICAL_FEATURES, MODEL_PATH, TARGET_COLUMN


def visual_band(probability: float) -> str:
    """UI color band. High (>0.70) is split so the original 4-color design still works."""
    if probability > 0.80:
        return "CRITICAL"
    if probability > 0.70:
        return "HIGH"
    if probability >= 0.30:
        return "MEDIUM"
    return "LOW"


class CustomerStore:
    def __init__(self) -> None:
        self.pipeline = load_churn_pipeline(MODEL_PATH)
        raw = load_cleaned_dataset()
        self.features = prepare_feature_frame(raw.drop(columns=[TARGET_COLUMN], errors="ignore"))
        preds = predict_churn(self.features, pipeline=self.pipeline)
        self.features = self.features.copy()
        self.features["churn_probability"] = preds["churn_probability"].to_numpy()
        self.features["predicted_churn"] = preds["predicted_churn"].to_numpy()
        self.features["risk_level"] = [
            risk_level_from_probability(float(p)) for p in self.features["churn_probability"]
        ]
        self.features["visual_band"] = [
            visual_band(float(p)) for p in self.features["churn_probability"]
        ]
        self.schema = {
            col: sorted(str(v) for v in raw[col].dropna().unique())
            for col in CATEGORICAL_FEATURES
            if col in raw.columns
        }
        self._global_drivers = None

    def row(self, customer_index: int) -> pd.DataFrame:
        if customer_index not in self.features.index:
            raise KeyError(customer_index)
        return self.features.loc[[customer_index], [c for c in self.features.columns if c not in {
            "churn_probability", "predicted_churn", "risk_level", "visual_band"
        }]]

    def summary_row(self, customer_index: int) -> dict:
        row = self.features.loc[customer_index]
        return {
            "customer_index": int(customer_index),
            "churn_probability": float(row["churn_probability"]),
            "predicted_churn": int(row["predicted_churn"]),
            "risk_level": str(row["risk_level"]),
            "visual_band": str(row["visual_band"]),
            "tenure": int(row["tenure"]),
            "monthly_charges": float(row["MonthlyCharges"]),
            "contract": str(row["Contract"]),
            "tech_support": str(row["TechSupport"]),
            "internet_service": str(row["InternetService"]),
        }

    def list_customers(self) -> list[dict]:
        return [self.summary_row(idx) for idx in self.features.index]

    def dashboard(self) -> dict:
        probs = self.features["churn_probability"].to_numpy(dtype=float)
        bands = self.features["visual_band"]
        levels = self.features["risk_level"]
        counts = {
            "LOW": int((bands == "LOW").sum()),
            "MEDIUM": int((bands == "MEDIUM").sum()),
            "HIGH": int((bands == "HIGH").sum()),
            "CRITICAL": int((bands == "CRITICAL").sum()),
        }
        retensa_counts = {
            "Low": int((levels == "Low").sum()),
            "Medium": int((levels == "Medium").sum()),
            "High": int((levels == "High").sum()),
        }
        hist = np.histogram(probs, bins=[0, 0.2, 0.4, 0.6, 0.8, 1.01])[0].tolist()
        high_preview = (
            self.features.sort_values("churn_probability", ascending=False)
            .head(8)
            .index.tolist()
        )
        contract_risk = (
            self.features.groupby("Contract")["churn_probability"].mean().sort_values(ascending=False)
        )
        tenure_bins = pd.cut(
            self.features["tenure"],
            bins=[-0.1, 6, 12, 24, 72],
            labels=["0-6 mo", "6-12 mo", "1-2 yr", "2yr+"],
        )
        tenure_risk = self.features.groupby(tenure_bins, observed=False)["churn_probability"].mean()
        charge_bins = pd.cut(
            self.features["MonthlyCharges"],
            bins=[0, 40, 80, 120, 200],
            labels=["$0-40", "$40-80", "$80-120", "$120+"],
        )
        charge_risk = self.features.groupby(charge_bins, observed=False)["churn_probability"].mean()
        return {
            "total_customers": int(len(self.features)),
            "high_risk": retensa_counts["High"],
            "medium_risk": retensa_counts["Medium"],
            "low_risk": retensa_counts["Low"],
            "visual_counts": counts,
            "retensa_counts": retensa_counts,
            "avg_churn_probability": float(np.mean(probs)),
            "retention_opportunities": int((probs > 0.70).sum()),
            "probability_histogram": {
                "labels": ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
                "counts": hist,
            },
            "risk_by_contract": [
                {"label": str(k), "value": round(float(v) * 100, 1)} for k, v in contract_risk.items()
            ],
            "risk_by_tenure": [
                {"label": str(k), "value": round(float(v) * 100, 1)}
                for k, v in tenure_risk.items()
                if pd.notna(v)
            ],
            "risk_by_charges": [
                {"label": str(k), "value": round(float(v) * 100, 1)}
                for k, v in charge_risk.items()
                if pd.notna(v)
            ],
            "top_drivers": self.global_drivers(),
            "high_priority": [self.summary_row(i) for i in high_preview],
        }

    def global_drivers(self) -> list[dict]:
        if self._global_drivers is None:
            explainer = ShapExplainer(MODEL_PATH)
            sample = self.features.drop(
                columns=["churn_probability", "predicted_churn", "risk_level", "visual_band"]
            )
            self._global_drivers = get_global_feature_importance(
                sample, top_n=8, sample_size=400, explainer=explainer
            )
        return self._global_drivers


@lru_cache(maxsize=1)
def get_store() -> CustomerStore:
    return CustomerStore()
