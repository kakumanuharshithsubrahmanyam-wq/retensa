# RETENSA

## Overview

RETENSA is an AI-powered customer churn prediction and retention platform. It helps teams identify customers at risk of leaving, understand why they are at risk, and take targeted retention actions.

## Product Flow

Predict → Explain → Find Root Cause → Simulate → Recommend → Act

## Planned Features

### Core Requirements

- Customer Data Processing
- Churn Classification
- Churn Probability Prediction
- Customer Risk Segmentation
- Feature Importance Analysis
- Retention Recommendations

### Differentiating Features

- Explainable AI (SHAP-based)
- AI Root-Cause Analysis
- Customer Risk Profile
- What-If Churn Simulator
- Retention Action Center
- AI Retention Campaign Generator
- Customer Segmentation
- Retention Opportunity Score
- Intervention Simulation

### AI / Interaction

- AI Business Assistant
- Natural-Language Customer Risk Queries
- Personalized Customer-Specific Action Plans

## Technology Stack

- Python
- Machine Learning
- XGBoost
- SHAP
- FastAPI
- React
- LLM integration

## Project Structure

- `data/` — Raw and processed customer datasets used for training and evaluation.
- `src/` — Core application modules (data, models, explainability, risk, recommendations, simulator, and utilities).
- `api/` — Backend API layer for serving predictions and product workflows.
- `frontend/` — User-facing interface for dashboards, simulators, and action tools.
- `models/` — Saved trained model artifacts.
- `tests/` — Automated tests for the platform.

## Team Development

This is a collaborative GitHub project. Team members should work on feature branches and open Pull Requests for review before merging into the main branch.

## Phase 1

Phase 1 covers a baseline churn model only: cleaned CSV → preprocessing → train/test split → XGBoost → evaluation → saved pipeline.

### Dataset

- File: `data/raw/Telco_Customer_Churn_Cleaned.csv`
- Cleaned Telco customer churn table (not the original uncleaned file, and not `Customer_Churn_Predictions.csv`)

### Features

`gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`

### Target

- Column: `Churn`
- Encoded as `Yes` → 1, `No` → 0

### Preprocessing approach

- Numeric columns (`SeniorCitizen`, `tenure`, `MonthlyCharges`, `TotalCharges`): median imputation and standard scaling
- Remaining feature columns: most-frequent imputation and `OneHotEncoder(handle_unknown="ignore")`
- Preprocessing and the classifier are saved together as one sklearn `Pipeline`

### Model

- Baseline `XGBClassifier` with `scale_pos_weight` computed from the **training** class counts only
- 80/20 stratified train/test split (`random_state=42`)
- No hyperparameter search in this phase

### Evaluation metrics

Accuracy, precision, recall, F1-score, ROC-AUC, and confusion matrix on the untouched test set.

### Saved model

`models/churn_model.joblib` — full preprocessing + XGBoost pipeline for `predict()` and `predict_proba()`.

### How to run

```bash
PYTHONPATH=. python -m src.data.inspect_data
PYTHONPATH=. python -m src.models.train
PYTHONPATH=. python -m src.models.optimize
```

`train` fits the original baseline pipeline. `optimize` compares regularized models with training-only cross-validation and writes `models/churn_model_optimized.joblib` without replacing `models/churn_model.joblib`.

On Apple Silicon macOS, XGBoost needs OpenMP (`brew install libomp`) if `libxgboost.dylib` fails to load.

## Phase 2 — Explainable AI

Phase 2 adds SHAP on top of the saved Phase 1 pipeline. The XGBoost model is not retrained.

- SHAP is used to explain XGBoost predictions in the transformed feature space the model actually sees.
- Global SHAP identifies which original customer features drive churn across a sample of rows.
- Local SHAP explains why one customer received a particular churn score.
- One-hot encoded columns (for example `Contract_Month-to-month`) are summed back to the original feature (`Contract`) before results are returned.
- Churn probability always comes from the existing pipeline's `predict_proba()`.
- SHAP contribution values are kept separate from probability and are not treated as percentage-point effects. With TreeExplainer on this XGBoost setup they are typically in raw-margin / log-odds space.
- Risk level uses business buckets: Low (< 0.30), Medium (0.30–0.70), High (> 0.70). These buckets do not change the model's classification threshold.
- No LLM is used in Phase 2.

```bash
PYTHONPATH=. python -m src.explainability.test_shap
```

## Phase 3 — Root Cause Analysis & What-If Simulation

Phase 3 builds on the production XGBoost pipeline (`models/churn_model.joblib`) and Phase 2 SHAP. It does not retrain the model and does not generate retention recommendations.

### Root Cause Analysis

Uses local SHAP results to identify:

- the strongest churn-risk driver (primary model driver)
- other risk-increasing factors
- protective factors
- a short customer-level summary

SHAP identifies **model contribution**, not causation. RETENSA does not claim that a feature causes churn.

### What-If Simulator

Allows a user to modify legitimate customer attributes and re-run the **same** production model.

Example: `Contract` Month-to-month → One year, then compare old vs new `predict_proba()` output.

The result is a **model simulation**, not a guaranteed real-world outcome. Probability change is reported in **percentage points**, not as a relative reduction.

```bash
PYTHONPATH=. python -m src.risk.test_root_cause
PYTHONPATH=. python -m src.simulator.test_what_if
```

## Phase 4 — Retention Recommendations & AI Action Center

Phase 4 turns Phase 1–3 evidence into retention actions. The production XGBoost pipeline is unchanged.

### Recommendation Engine

Deterministic rules use:

- churn probability and risk level
- SHAP drivers
- customer attributes
- What-If simulations

Recommendations are prioritized from model drivers. They are phrased as options to consider, not guaranteed outcomes or invented discounts.

### LLM

The LLM is a natural-language layer over structured RETENSA evidence.

It does **not** determine probability, SHAP, root cause, or model predictions. If `OPENAI_API_KEY` (preferred) or `ANTHROPIC_API_KEY` is missing or the call fails, RETENSA falls back to the deterministic plan. Keys live in `.env` and are never hardcoded.

### Action Center

Combines prediction, explanation, root cause, What-If, recommendation, and an AI retention plan into one structured object for a future frontend.

```bash
PYTHONPATH=. python -m src.recommendations.test_recommendations
PYTHONPATH=. python -m src.recommendations.test_action_center
```
