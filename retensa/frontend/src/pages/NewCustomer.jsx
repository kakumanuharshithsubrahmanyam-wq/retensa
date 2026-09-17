import { useEffect, useState } from "react";
import { analyzeNewCustomer, getSchema } from "../services/api";
import ActionCenterView from "../components/ActionCenterView";
import {
  CATEGORICAL_FIELDS,
  EMPTY_FORM,
  NUMERIC_FIELDS,
  SAMPLES,
} from "../data/newCustomerSamples";

const SESSION_KEY = "retensa_new_customer_analysis";

export default function NewCustomer() {
  const [schema, setSchema] = useState({});
  const [form, setForm] = useState({ ...EMPTY_FORM });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [analysis, setAnalysis] = useState(null);

  useEffect(() => {
    getSchema().then((body) => setSchema(body.categorical || {})).catch(() => {});
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) setAnalysis(JSON.parse(saved));
    } catch {
      /* ignore */
    }
  }, []);

  function setField(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        ...form,
        SeniorCitizen: Number(form.SeniorCitizen),
        tenure: Number(form.tenure),
        MonthlyCharges: Number(form.MonthlyCharges),
        TotalCharges: Number(form.TotalCharges),
      };
      const result = await analyzeNewCustomer(payload);
      setAnalysis(result);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(result));
      sessionStorage.setItem("retensa_new_customer_features", JSON.stringify(result.customer.features));
    } catch (err) {
      setAnalysis(null);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Analyze New Customer</h1>
          <p>
            Score a customer who is not in the 7,021-row dataset with the production XGBoost pipeline.
            Nothing is written to training data.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <div className="card-title" style={{ marginBottom: 10 }}>Load sample</div>
        <div className="flex gap-8" style={{ flexWrap: "wrap" }}>
          {SAMPLES.map((sample) => (
            <button
              key={sample.name}
              type="button"
              className="btn btn-sm"
              onClick={() => {
                setForm({ ...sample.data });
                setError("");
              }}
            >
              {sample.name}
            </button>
          ))}
        </div>
      </div>

      <form className="card" onSubmit={onSubmit} style={{ marginBottom: 16 }}>
        <div className="card-title" style={{ marginBottom: 14 }}>Customer features</div>
        <div className="profile-cards" style={{ marginBottom: 16 }}>
          {NUMERIC_FIELDS.map((field) => (
            <div className="card profile-mini" key={field}>
              <label className="lbl" htmlFor={`nc-${field}`}>{field}</label>
              <input
                id={`nc-${field}`}
                className="filter-input"
                type="number"
                step={field === "SeniorCitizen" || field === "tenure" ? 1 : 0.01}
                min={0}
                max={field === "SeniorCitizen" ? 1 : undefined}
                value={form[field]}
                onChange={(e) => setField(field, e.target.value)}
                required
              />
            </div>
          ))}
        </div>
        <div className="profile-cards">
          {CATEGORICAL_FIELDS.map((field) => (
            <div className="card profile-mini" key={field}>
              <label className="lbl" htmlFor={`nc-${field}`}>{field}</label>
              <select
                id={`nc-${field}`}
                className="filter-select"
                value={form[field]}
                onChange={(e) => setField(field, e.target.value)}
                required
              >
                {(schema[field] || [form[field]]).map((option) => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
            </div>
          ))}
        </div>
        <div className="flex gap-8" style={{ marginTop: 16 }}>
          <button className="btn btn-primary" type="submit" disabled={loading}>
            {loading ? "Analyzing…" : "Analyze Customer"}
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => {
              setForm({ ...EMPTY_FORM });
              setAnalysis(null);
              setError("");
              sessionStorage.removeItem(SESSION_KEY);
              sessionStorage.removeItem("retensa_new_customer_features");
            }}
          >
            Clear
          </button>
        </div>
        {error && <div className="page-status error" style={{ marginTop: 12 }}>{error}</div>}
      </form>

      {analysis && (
        <div className="section-block">
          <ActionCenterView
            data={analysis}
            title="New Customer Analysis"
            badgeLabel="Ad-hoc scoring — not stored in the dataset"
            backTo="/new-customer"
            backLabel="Back to form"
            askAiTo="/assistant?mode=new"
            whatIfFeatures
          />
        </div>
      )}
    </main>
  );
}
