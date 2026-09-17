"""Thin FastAPI layer over existing RETENSA intelligence."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.assistant import answer_assistant
from api.metrics import load_model_metrics
from api.new_customer import NewCustomerValidationError, analyze_new_customer, what_if_for_features
from api.store import get_store
from src.models.predict import predict_churn
from src.recommendations.action_center import build_action_center
from src.recommendations.engine import generate_recommendation
from src.simulator.what_if import simulate_scenario
from src.utils.config import MODEL_PATH, PROJECT_ROOT

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

app = FastAPI(title="RETENSA API", version="0.5.0")

allowed = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
)
origins = [item.strip() for item in allowed.split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class WhatIfRequest(BaseModel):
    changes: Dict[str, Any] = Field(default_factory=dict)


class FeatureWhatIfRequest(BaseModel):
    features: Dict[str, Any]
    changes: Dict[str, Any] = Field(default_factory=dict)


class AssistantRequest(BaseModel):
    message: str = Field(..., min_length=1)
    customer_index: Optional[int] = None
    features: Optional[Dict[str, Any]] = None


class NewCustomerRequest(BaseModel):
    gender: str
    SeniorCitizen: int
    Partner: str
    Dependents: str
    tenure: float
    PhoneService: str
    MultipleLines: str
    InternetService: str
    OnlineSecurity: str
    OnlineBackup: str
    DeviceProtection: str
    TechSupport: str
    StreamingTV: str
    StreamingMovies: str
    Contract: str
    PaperlessBilling: str
    PaymentMethod: str
    MonthlyCharges: float
    TotalCharges: float


def _customer_or_404(customer_index: int):
    store = get_store()
    if customer_index not in store.features.index:
        raise HTTPException(status_code=404, detail=f"Customer {customer_index} was not found.")
    return store


@app.get("/")
def root() -> Dict[str, Any]:
    """Local demo landing — the React UI is at http://localhost:5173."""
    return {
        "service": "RETENSA API",
        "status": "ok",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/api/health",
        "frontend": "http://localhost:5173",
        "message": "Use the React app at :5173. API routes live under /api/.",
    }


@app.get("/api/health")
def health() -> Dict[str, Any]:
    model_ok = MODEL_PATH.exists()
    return {
        "status": "ok" if model_ok else "degraded",
        "model": str(MODEL_PATH.name),
        "model_available": model_ok,
    }


@app.get("/api/schema")
def schema() -> Dict[str, Any]:
    return {"categorical": get_store().schema}


@app.get("/api/dashboard")
def dashboard() -> Dict[str, Any]:
    return get_store().dashboard()


@app.get("/api/customers")
def list_customers(limit: Optional[int] = None, risk: Optional[str] = None) -> List[Dict[str, Any]]:
    rows = get_store().list_customers()
    if risk:
        rows = [row for row in rows if row["risk_level"].lower() == risk.lower()]
    rows.sort(key=lambda row: row["churn_probability"], reverse=True)
    if limit is not None:
        rows = rows[: max(0, limit)]
    return rows


@app.get("/api/customers/{customer_index}/analysis")
def customer_analysis(customer_index: int) -> Dict[str, Any]:
    store = _customer_or_404(customer_index)
    frame = store.row(customer_index)
    center = build_action_center(frame, include_llm=True)
    prediction = predict_churn(frame, pipeline=store.pipeline).iloc[0]
    return {
        "customer": {
            "customer_index": customer_index,
            "attributes": center["customer"]["attributes"],
        },
        "prediction": {
            "predicted_churn": int(prediction["predicted_churn"]),
            "churn_probability": float(prediction["churn_probability"]),
        },
        "risk": center["risk"],
        "root_cause": center["root_cause"],
        "recommendations": center["recommended_actions"],
        "what_if": center["what_if_scenarios"],
        "action_plan": center["action_plan"],
        "ai_plan": center["llm"],
    }


@app.post("/api/customers/{customer_index}/what-if")
def customer_what_if(customer_index: int, body: WhatIfRequest) -> Dict[str, Any]:
    store = _customer_or_404(customer_index)
    result = simulate_scenario(store.row(customer_index), body.changes)
    if not result.get("valid", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid scenario."))
    impact = result["impact"]
    return {
        "valid": True,
        "original": result["original"],
        "scenario": result["scenario"],
        "impact": {
            "probability_delta": impact["probability_delta"],
            "percentage_points": impact["probability_change_percentage_points"],
            "risk_changed": impact["risk_changed"],
        },
        "note": result.get("note"),
    }


@app.post("/api/analyze-new-customer")
def analyze_new(body: NewCustomerRequest) -> Dict[str, Any]:
    payload = body.model_dump() if hasattr(body, "model_dump") else body.dict()
    try:
        return analyze_new_customer(payload, include_llm=True)
    except NewCustomerValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/what-if")
def feature_what_if(body: FeatureWhatIfRequest) -> Dict[str, Any]:
    """What-If for ad-hoc / new-customer feature sets (not dataset row IDs)."""
    try:
        result = what_if_for_features(body.features, body.changes)
    except NewCustomerValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.get("valid", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Invalid scenario."))
    impact = result["impact"]
    return {
        "valid": True,
        "original": result["original"],
        "scenario": result["scenario"],
        "impact": {
            "probability_delta": impact["probability_delta"],
            "percentage_points": impact["probability_change_percentage_points"],
            "risk_changed": impact["risk_changed"],
        },
        "note": result.get("note"),
    }


@app.get("/api/customers/{customer_index}/recommendation")
def customer_recommendation(customer_index: int) -> Dict[str, Any]:
    store = _customer_or_404(customer_index)
    return generate_recommendation(store.row(customer_index))


@app.get("/api/customers/{customer_index}/action-center")
def customer_action_center(customer_index: int) -> Dict[str, Any]:
    store = _customer_or_404(customer_index)
    return build_action_center(store.row(customer_index), include_llm=True)


@app.get("/api/model-metrics")
def model_metrics() -> Dict[str, Any]:
    try:
        store = get_store()
        return load_model_metrics(dataset_size=int(len(store.features)))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/assistant")
def assistant(body: AssistantRequest) -> Dict[str, Any]:
    store = get_store()
    try:
        return answer_assistant(
            body.message,
            store=store,
            customer_index=body.customer_index,
            features=body.features,
        )
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {body.customer_index} was not found.",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
