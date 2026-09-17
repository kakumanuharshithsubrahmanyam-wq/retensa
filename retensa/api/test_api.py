"""HTTP tests for the Phase 5 API using a real customer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in {"ok", "degraded"}
    assert body["model"] == "churn_model.joblib"


def test_customer_2203_flow():
    listed = client.get("/api/customers", params={"limit": 5})
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)

    analysis = client.get("/api/customers/2203/analysis")
    assert analysis.status_code == 200
    payload = analysis.json()
    probability = payload["risk"]["probability"]
    assert 0.9 < probability < 1.0
    assert payload["risk"]["level"] == "High"

    what_if = client.post(
        "/api/customers/2203/what-if",
        json={"changes": {"Contract": "One year"}},
    )
    assert what_if.status_code == 200
    delta = what_if.json()["impact"]["percentage_points"]
    assert delta < 0

    rec = client.get("/api/customers/2203/recommendation")
    assert rec.status_code == 200
    assert rec.json()["recommendations"]

    center = client.get("/api/customers/2203/action-center")
    assert center.status_code == 200
    assert "llm" in center.json()


def test_invalid_what_if():
    response = client.post("/api/customers/2203/what-if", json={"changes": {"Contract": "Five Year"}})
    assert response.status_code == 400


def test_missing_customer():
    response = client.get("/api/customers/999999/analysis")
    assert response.status_code == 404


def test_model_metrics():
    response = client.get("/api/model-metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "XGBoost"
    assert body["model_file"] == "churn_model.joblib"
    assert 0.75 < body["accuracy"] < 0.76
    assert body["confusion_matrix"]["true_negative"] == 779


def test_assistant_portfolio_and_customer():
    portfolio = client.post("/api/assistant", json={"message": "Summarize the portfolio."})
    assert portfolio.status_code == 200
    body = portfolio.json()
    assert body["mode"] == "portfolio"
    assert "Customers scored" in body["answer"] or "customers" in body["answer"].lower()

    customer = client.post(
        "/api/assistant",
        json={"message": "Why is this customer at high risk?", "customer_index": 2203},
    )
    assert customer.status_code == 200
    payload = customer.json()
    assert payload["mode"] == "customer"
    assert "97.73%" in payload["answer"] or "0.977" in payload["answer"]


def test_arbitrary_customer_supported():
    """All scored rows must be addressable — 2203 is only a known demo case."""
    listed = client.get("/api/customers", params={"limit": 50})
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) >= 2
    other = next(row for row in rows if row["customer_index"] != 2203)
    analysis = client.get(f"/api/customers/{other['customer_index']}/analysis")
    assert analysis.status_code == 200
    body = analysis.json()
    assert "probability" in body["risk"]
    assert body["root_cause"]["primary_driver"] is not None or body["risk"]["level"] in {"Low", "Medium", "High"}


SAMPLE_HIGH = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 2,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "Yes",
    "StreamingMovies": "Yes",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 89.85,
    "TotalCharges": 179.7,
}

SAMPLE_LOW = {
    "gender": "Male",
    "SeniorCitizen": 0,
    "Partner": "Yes",
    "Dependents": "Yes",
    "tenure": 60,
    "PhoneService": "Yes",
    "MultipleLines": "Yes",
    "InternetService": "DSL",
    "OnlineSecurity": "Yes",
    "OnlineBackup": "Yes",
    "DeviceProtection": "Yes",
    "TechSupport": "Yes",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Two year",
    "PaperlessBilling": "No",
    "PaymentMethod": "Bank transfer (automatic)",
    "MonthlyCharges": 65.0,
    "TotalCharges": 3900.0,
}


def test_analyze_new_customer_high_and_low():
    high = client.post("/api/analyze-new-customer", json=SAMPLE_HIGH)
    assert high.status_code == 200
    high_body = high.json()
    assert high_body["customer"]["is_new"] is True
    assert 0.0 < high_body["prediction"]["churn_probability"] < 1.0
    assert high_body["prediction"]["risk_level"] in {"Low", "Medium", "High"}
    assert high_body["explanation"]["primary_model_driver"]
    assert high_body["root_cause"]["risk_factors"] or high_body["root_cause"]["protective_factors"]
    assert isinstance(high_body["recommendations"], list)

    low = client.post("/api/analyze-new-customer", json=SAMPLE_LOW)
    assert low.status_code == 200
    low_body = low.json()
    assert low_body["prediction"]["churn_probability"] < high_body["prediction"]["churn_probability"]


def test_analyze_new_customer_validation():
    missing = dict(SAMPLE_HIGH)
    del missing["Contract"]
    missing_resp = client.post("/api/analyze-new-customer", json=missing)
    assert missing_resp.status_code in {400, 422}

    bad_cat = dict(SAMPLE_HIGH, Contract="Five Year")
    assert client.post("/api/analyze-new-customer", json=bad_cat).status_code == 400

    bad_num = dict(SAMPLE_HIGH, tenure=-1)
    assert client.post("/api/analyze-new-customer", json=bad_num).status_code == 400

    contradiction = dict(SAMPLE_HIGH, PhoneService="No", MultipleLines="Yes")
    assert client.post("/api/analyze-new-customer", json=contradiction).status_code == 400


def test_new_customer_what_if_and_assistant():
    analysis = client.post("/api/analyze-new-customer", json=SAMPLE_HIGH)
    assert analysis.status_code == 200
    features = analysis.json()["customer"]["features"]

    what_if = client.post(
        "/api/what-if",
        json={"features": features, "changes": {"Contract": "One year"}},
    )
    assert what_if.status_code == 200
    assert "percentage_points" in what_if.json()["impact"]

    assistant = client.post(
        "/api/assistant",
        json={"message": "Why is this customer at high risk?", "features": features},
    )
    assert assistant.status_code == 200
    assert assistant.json()["mode"] == "customer"
    assert assistant.json()["evidence"].get("is_new") is True


if __name__ == "__main__":
    test_health()
    test_customer_2203_flow()
    test_invalid_what_if()
    test_missing_customer()
    test_model_metrics()
    test_assistant_portfolio_and_customer()
    test_arbitrary_customer_supported()
    test_analyze_new_customer_high_and_low()
    test_analyze_new_customer_validation()
    test_new_customer_what_if_and_assistant()
    print("API tests passed.")
