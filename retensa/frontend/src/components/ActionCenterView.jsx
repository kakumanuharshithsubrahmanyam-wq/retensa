import { Link } from "react-router-dom";
import WhatIfSimulator from "./WhatIfSimulator";
import AIPlan from "./AIPlan";
import { pct, riskBadge } from "./ui";

function ContribList({ items, positive }) {
  const list = items || [];
  const max = Math.max(...list.map((i) => Math.abs(i.shap_value)), 0.01);
  return list.map((item) => (
    <div className="contrib-row" key={item.feature}>
      <span className="contrib-name">{item.feature}</span>
      <div className="contrib-bar-track">
        <div
          className={`contrib-bar-fill ${positive ? "pos" : "neg"}`}
          style={{ width: `${Math.min(100, (Math.abs(item.shap_value) / max) * 100)}%` }}
        />
      </div>
      <span className="contrib-val">{item.shap_value >= 0 ? "+" : ""}{Number(item.shap_value).toFixed(3)}</span>
    </div>
  ));
}

export default function ActionCenterView({
  data,
  title,
  badgeLabel,
  backTo = "/customers",
  backLabel = "Back to customers",
  askAiTo,
  whatIfFeatures = false,
}) {
  if (!data) return null;
  const attrs = data.customer?.attributes || data.customer?.features || {};
  const recs = data.recommendations || [];
  const top = recs[0];
  const impact = data.action_plan?.model_simulated_impact;
  const primary = data.root_cause?.primary_driver;
  const predicted = data.prediction?.predicted_churn;

  return (
    <>
      <Link className="back-link" to={backTo}>{backLabel}</Link>
      <div className="ci-header">
        <div>
          <h1>{title}</h1>
          {badgeLabel && <div className="card-sub" style={{ marginTop: 4 }}>{badgeLabel}</div>}
        </div>
        <div className="flex gap-8" style={{ alignItems: "center" }}>
          {riskBadge(data.risk.level)}
          {askAiTo && <Link className="btn btn-sm" to={askAiTo}>Ask AI</Link>}
        </div>
      </div>

      <div className="ci-top-grid">
        <div className="card prob-ring-card">
          <div className="prob-ring-value" style={{ position: "relative" }}>
            <span className="num">{pct(data.risk.probability)}</span>
            <span className="lbl">CHURN RISK</span>
          </div>
          <div className="prob-caption">
            Predicted Churn Probability
            {predicted != null && <> · Predicted class: {predicted === 1 ? "Churn" : "Stay"}</>}
          </div>
        </div>
        <div className="profile-cards">
          {[
            ["Tenure", `${attrs.tenure} months`],
            ["Monthly Charges", `$${Number(attrs.MonthlyCharges || 0).toFixed(2)}`],
            ["Contract", attrs.Contract],
            ["Tech Support", attrs.TechSupport],
            ["Internet", attrs.InternetService],
            ["Payment", attrs.PaymentMethod],
            ["Primary driver", primary?.feature || data.explanation?.primary_model_driver || "—"],
            ["Retention priority", data.risk.retention_priority],
          ].map(([lbl, val]) => (
            <div className="card profile-mini" key={lbl}>
              <div className="lbl">{lbl}</div>
              <div className="val">{val}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="section-block">
        <div className="card">
          <span className="xai-badge">Explainable model output</span>
          <h2 className="section-heading">Why is this customer at risk?</h2>
          <p className="section-desc">Factors increasing predicted churn risk (SHAP model drivers, not proven causes).</p>
          <div className="contrib-grid">
            <div>
              <div className="contrib-col-label">Risk-increasing factors</div>
              <ContribList items={data.root_cause?.risk_factors || []} positive />
            </div>
            <div>
              <div className="contrib-col-label">Protective factors</div>
              <ContribList items={data.root_cause?.protective_factors || []} positive={false} />
            </div>
          </div>
        </div>
      </div>

      <div className="section-block">
        <div className="card">
          <div className="card-title">PRIMARY MODEL DRIVER</div>
          <div className="kpi-value">{primary?.feature || data.explanation?.primary_model_driver || "—"}</div>
          <p className="card-sub">Strongest model driver increasing predicted churn risk.</p>
          {primary && (
            <p className="text-secondary">
              SHAP contribution: {Number(primary.shap_value).toFixed(4)} (model output space, not percentage points)
            </p>
          )}
          <p className="explain-footer">{data.root_cause?.summary}</p>
        </div>
      </div>

      <div className="section-block">
        <WhatIfSimulator
          customerIndex={whatIfFeatures ? null : data.customer?.customer_index}
          attributes={attrs}
          features={whatIfFeatures ? attrs : null}
        />
      </div>

      <div className="section-block">
        <div className="card">
          <div className="card-title" style={{ marginBottom: 10 }}>Retention Action</div>
          {top ? (
            <>
              <p className="val">{top.action}</p>
              <p className="card-sub">Priority: {String(top.priority).toUpperCase()}</p>
              <p className="text-secondary">{top.reason}</p>
              {impact && (
                <div className="insight-box" style={{ marginTop: 12 }}>
                  <b>Model-simulated impact —</b> current {pct(impact.current_probability)} → scenario {pct(impact.scenario_probability)} ({impact.delta_percentage_points.toFixed(2)} percentage points). Not a guaranteed reduction.
                </div>
              )}
            </>
          ) : (
            <p>No SHAP-linked intervention was identified.</p>
          )}
        </div>
      </div>

      <div className="section-block">
        <AIPlan llm={data.ai_plan} />
      </div>
    </>
  );
}
