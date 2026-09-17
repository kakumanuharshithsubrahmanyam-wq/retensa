import { useEffect, useState } from "react";
import { getSchema, simulateWhatIf, simulateWhatIfFeatures } from "../services/api";
import { pct, riskBadge } from "./ui";

const FIELDS = [
  "Contract",
  "TechSupport",
  "OnlineSecurity",
  "OnlineBackup",
  "DeviceProtection",
  "PaymentMethod",
];

export default function WhatIfSimulator({ customerIndex, attributes, features = null }) {
  const [schema, setSchema] = useState({});
  const [draft, setDraft] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const baseline = features || attributes;

  useEffect(() => {
    getSchema().then((body) => setSchema(body.categorical || {})).catch(() => {});
  }, []);

  useEffect(() => {
    const next = {};
    FIELDS.forEach((field) => {
      if (baseline?.[field] != null) next[field] = String(baseline[field]);
    });
    setDraft(next);
    setResult(null);
    setError("");
  }, [customerIndex, baseline]);

  async function run() {
    const changes = {};
    FIELDS.forEach((field) => {
      if (draft[field] != null && String(draft[field]) !== String(baseline?.[field])) {
        changes[field] = draft[field];
      }
    });
    if (!Object.keys(changes).length) {
      setError("Change at least one attribute before simulating.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      if (features) {
        setResult(await simulateWhatIfFeatures(features, changes));
      } else {
        setResult(await simulateWhatIf(customerIndex, changes));
      }
    } catch (err) {
      setResult(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="sim-grid">
      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>What-If controls</div>
        {FIELDS.map((field) => (
          <div className="control-group" key={field}>
            <label>{field} <span className="control-val">{draft[field] || "—"}</span></label>
            <div className="toggle-row">
              {(schema[field] || []).map((value) => (
                <button
                  key={value}
                  className={`toggle-pill ${draft[field] === value ? "active" : ""}`}
                  onClick={() => setDraft((prev) => ({ ...prev, [field]: value }))}
                  type="button"
                >
                  {value}
                </button>
              ))}
            </div>
          </div>
        ))}
        <div className="flex gap-8">
          <button className="btn btn-primary" onClick={run} disabled={loading}>{loading ? "Simulating…" : "Simulate Scenario"}</button>
          <button className="btn" type="button" onClick={() => {
            const next = {};
            FIELDS.forEach((field) => { next[field] = String(baseline?.[field] ?? ""); });
            setDraft(next);
            setResult(null);
            setError("");
          }}>Reset</button>
        </div>
        {error && <div className="page-status error" style={{ marginTop: 12 }}>{error}</div>}
      </div>
      <div className="card compare-panel">
        <div className="card-title">Risk comparison</div>
        {result ? (
          <>
            <div className="compare-rings">
              <div className="compare-ring-block">
                <span className="cap">Current</span>
                <div className="kpi-value">{pct(result.original.churn_probability)}</div>
                {riskBadge(result.original.risk_level)}
              </div>
              <div className="compare-arrow">→</div>
              <div className="compare-ring-block">
                <span className="cap">Scenario</span>
                <div className="kpi-value">{pct(result.scenario.churn_probability)}</div>
                {riskBadge(result.scenario.risk_level)}
              </div>
            </div>
            <div className={`risk-change-banner ${result.impact.percentage_points > 0 ? "negative" : ""}`}>
              Model-simulated change: {result.impact.percentage_points.toFixed(2)} percentage points
            </div>
            <div className="insight-box">
              <b>Model-simulated impact —</b> this is the production model’s predicted probability under the edited attributes, not a guaranteed real-world outcome.
            </div>
          </>
        ) : (
          <div className="insight-box">Adjust valid attributes and simulate. The new probability is computed by the backend XGBoost pipeline.</div>
        )}
      </div>
    </div>
  );
}
