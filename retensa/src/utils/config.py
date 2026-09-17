"""Shared Phase 1 configuration for RETENSA."""

from pathlib import Path

RANDOM_SEED = 42
TEST_SIZE = 0.20

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "Telco_Customer_Churn_Cleaned.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "churn_model.joblib"
BASELINE_MODEL_PATH = PROJECT_ROOT / "models" / "churn_model_baseline.joblib"
OPTIMIZED_MODEL_PATH = PROJECT_ROOT / "models" / "churn_model_optimized.joblib"
METADATA_PATH = PROJECT_ROOT / "models" / "model_metadata.json"
BASELINE_METRICS_PATH = PROJECT_ROOT / "models" / "baseline_metrics.json"

TARGET_COLUMN = "Churn"
POSITIVE_LABEL = "Yes"
NEGATIVE_LABEL = "No"

NUMERIC_FEATURES = [
    "SeniorCitizen",
    "tenure",
    "MonthlyCharges",
    "TotalCharges",
]

CATEGORICAL_FEATURES = [
    "gender",
    "Partner",
    "Dependents",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "OnlineBackup",
    "DeviceProtection",
    "TechSupport",
    "StreamingTV",
    "StreamingMovies",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
]

FEATURE_COLUMNS = NUMERIC_FEATURES + CATEGORICAL_FEATURES

TARGET_MAP = {
    NEGATIVE_LABEL: 0,
    POSITIVE_LABEL: 1,
}
