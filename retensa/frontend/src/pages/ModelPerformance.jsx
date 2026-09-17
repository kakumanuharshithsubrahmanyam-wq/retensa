import { useEffect, useState } from "react";
import { getModelMetrics } from "../services/api";
import StatusBox, { pct } from "../components/ui";

export default function ModelPerformance() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getModelMetrics()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Model Performance</h1>
          <p>Held-out test metrics for the production XGBoost baseline — not the optimized HGB artifact.</p>
        </div>
      </div>
      <StatusBox loading={loading} error={error} loadingText="Loading production model metrics…">
        {data && (
          <>
            <div className="kpi-grid">
              {[
                ["Accuracy", pct(data.accuracy)],
                ["Precision", pct(data.precision)],
                ["Recall", pct(data.recall)],
                ["F1 Score", pct(data.f1)],
                ["ROC-AUC", pct(data.roc_auc)],
              ].map(([label, value]) => (
                <div className="card kpi-card" key={label}>
                  <div className="kpi-value">{value}</div>
                  <div className="kpi-label">{label}</div>
                </div>
              ))}
            </div>

            <div className="grid-2" style={{ marginBottom: 14 }}>
              <div className="card">
                <div className="card-title" style={{ marginBottom: 12 }}>Confusion Matrix</div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th></th>
                        <th>Predicted No</th>
                        <th>Predicted Yes</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Actual No</td>
                        <td className="mono">{data.confusion_matrix.true_negative}</td>
                        <td className="mono">{data.confusion_matrix.false_positive}</td>
                      </tr>
                      <tr>
                        <td>Actual Yes</td>
                        <td className="mono">{data.confusion_matrix.false_negative}</td>
                        <td className="mono">{data.confusion_matrix.true_positive}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="card">
                <div className="card-title" style={{ marginBottom: 12 }}>Dataset &amp; Training</div>
                <ul className="report-list">
                  <li className="report-item">Model: {data.model} ({data.model_file})</li>
                  <li className="report-item">Dataset: {data.dataset_size.toLocaleString()} customers</li>
                  <li className="report-item">Training: {data.train_size.toLocaleString()}</li>
                  <li className="report-item">Testing: {data.test_size.toLocaleString()}</li>
                  <li className="report-item">Split: {data.split}</li>
                  <li className="report-item">Random state: {data.random_state}</li>
                  {data.train_distribution?.churn != null && (
                    <li className="report-item">
                      Train: {data.train_distribution.non_churn.toLocaleString()} non-churn / {data.train_distribution.churn.toLocaleString()} churn
                    </li>
                  )}
                  {data.test_distribution?.churn != null && (
                    <li className="report-item">
                      Test: {data.test_distribution.non_churn.toLocaleString()} non-churn / {data.test_distribution.churn.toLocaleString()} churn
                    </li>
                  )}
                </ul>
                <p className="card-sub" style={{ marginTop: 12 }}>{data.note}</p>
              </div>
            </div>

            <div className="card">
              <div className="card-title" style={{ marginBottom: 12 }}>What these metrics mean</div>
              <div className="driver-list">
                {Object.entries(data.metric_explanations || {}).map(([key, text]) => (
                  <div className="driver-row" key={key}>
                    <div className="driver-row-top">
                      <span className="name">{key.replace("_", "-").toUpperCase()}</span>
                    </div>
                    <p className="text-secondary" style={{ marginTop: 4 }}>{text}</p>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </StatusBox>
    </main>
  );
}
