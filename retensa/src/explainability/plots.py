"""Optional SHAP visualizations. Structured JSON output is the source of truth."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.utils.config import PROJECT_ROOT

REPORTS_DIR = PROJECT_ROOT / "reports"


def save_global_importance_plot(
    importance: list[dict],
    output_path: Path | None = None,
) -> Path:
    if not importance:
        raise ValueError("No global importance rows to plot.")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path is not None else REPORTS_DIR / "global_shap_importance.png"
    frame = pd.DataFrame(importance).sort_values("importance", ascending=True)
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.4 * len(frame))))
    ax.barh(frame["feature"], frame["importance"], color="#1f4e79")
    ax.set_xlabel("mean |SHAP| (model output space)")
    ax.set_title("Global SHAP feature importance")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def save_local_explanation_plot(
    contributions: list[dict],
    output_path: Path | None = None,
    top_n: int = 10,
) -> Path:
    if not contributions:
        raise ValueError("No local contributions to plot.")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(output_path) if output_path is not None else REPORTS_DIR / "local_shap_explanation.png"
    frame = pd.DataFrame(contributions).head(top_n).iloc[::-1]
    colors = [
        "#b22222" if row["shap_value"] >= 0 else "#2e8b57" for _, row in frame.iterrows()
    ]
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.4 * len(frame))))
    ax.barh(frame["feature"], frame["shap_value"], color=colors)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel("SHAP value (model output space, not percentage points)")
    ax.set_title("Local SHAP explanation")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
