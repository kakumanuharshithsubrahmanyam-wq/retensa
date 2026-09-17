"""Business risk buckets for RETENSA explanations.

These thresholds are independent of the XGBoost classification cutoff.
"""

from __future__ import annotations

LOW_RISK_MAX = 0.30
HIGH_RISK_MIN = 0.70


def risk_level_from_probability(churn_probability: float) -> str:
    """Map a churn probability in [0, 1] to Low / Medium / High."""
    if churn_probability < 0.0 or churn_probability > 1.0:
        raise ValueError(
            f"churn_probability must be in [0, 1], got {churn_probability}."
        )
    if churn_probability < LOW_RISK_MAX:
        return "Low"
    if churn_probability <= HIGH_RISK_MIN:
        return "Medium"
    return "High"
