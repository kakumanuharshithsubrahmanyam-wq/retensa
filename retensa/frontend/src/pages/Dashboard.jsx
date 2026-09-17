import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getDashboard } from "../services/api";
import { HorizontalBars, RiskDonut } from "../components/charts";
import StatusBox, { pct, riskBadge } from "../components/ui";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Retention Command Center</h1>
          <p>Identify customers at risk. Understand why. Take action before they leave.</p>
        </div>
        <Link className="btn btn-primary" to="/customers">View all customers</Link>
      </div>
      <StatusBox loading={loading} error={error} loadingText="Loading dashboard…">
        {data && (
          <>
            <div className="kpi-grid">
              {[
                ["TOTAL CUSTOMERS", data.total_customers.toLocaleString()],
                ["HIGH RISK", data.high_risk.toLocaleString()],
                ["MEDIUM RISK", data.medium_risk.toLocaleString()],
                ["LOW RISK", data.low_risk.toLocaleString()],
                ["AVG CHURN PROBABILITY", pct(data.avg_churn_probability)],
              ].map(([label, value]) => (
                <div className="card kpi-card" key={label}>
                  <div className="kpi-value">{value}</div>
                  <div className="kpi-label">{label}</div>
                </div>
              ))}
            </div>
            <div className="grid-2" style={{ marginBottom: 14 }}>
              <div className="card">
                <div className="card-head">
                  <div>
                    <div className="card-title">Customer Risk Distribution</div>
                    <div className="card-sub">Visual bands of predicted risk (Critical is High &gt; 80%)</div>
                  </div>
                </div>
                <RiskDonut counts={data.visual_counts} />
              </div>
              <div className="card">
                <div className="card-title">Risk Summary</div>
                <div className="risk-summary-list">
                  {["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((band) => (
                    <div className="risk-row" key={band}>
                      <span className={`risk-dot dot-${band.toLowerCase()}`} />
                      <span className="risk-name">{band}</span>
                      <span className="risk-count">{data.visual_counts[band].toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="grid-2" style={{ marginBottom: 14 }}>
              <div className="card">
                <div className="card-title">Top Churn Drivers</div>
                <div className="card-sub">Mean |SHAP| on a sample of customers (model contribution)</div>
                <div className="driver-list" style={{ marginTop: 12 }}>
                  {data.top_drivers.map((d) => (
                    <div className="driver-row" key={d.feature}>
                      <div className="driver-row-top">
                        <span className="name">{d.feature}</span>
                        <span className="pct">{Number(d.importance).toFixed(3)}</span>
                      </div>
                      <div className="driver-track">
                        <div className="driver-fill" style={{ width: `${Math.min(100, Number(d.importance) * 80)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card">
                <div className="card-title">High Priority Customers</div>
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr><th>Customer</th><th>Probability</th><th>Risk</th><th></th></tr>
                    </thead>
                    <tbody>
                      {data.high_priority.map((row) => (
                        <tr key={row.customer_index}>
                          <td className="cust-id">#{row.customer_index}</td>
                          <td className="mono">{pct(row.churn_probability)}</td>
                          <td>{riskBadge(row.risk_level)}</td>
                          <td><Link className="btn btn-sm" to={`/customers/${row.customer_index}`}>View</Link></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </StatusBox>
    </main>
  );
}
