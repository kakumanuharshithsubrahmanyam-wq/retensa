import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCustomers } from "../services/api";
import StatusBox, { pct, riskBadge } from "../components/ui";

export default function RetentionCenter() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    getCustomers({ risk: "High", limit: 20 })
      .then(setRows)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);
  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Retention Action Center</h1>
          <p>High-risk accounts ranked by model-predicted churn probability.</p>
        </div>
      </div>
      <StatusBox loading={loading} error={error}>
        <div className="summary-cards">
          <div className="card summary-card"><div className="num">{rows.length}</div><div className="lbl">High-risk listed</div></div>
        </div>
        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr><th>Customer</th><th>Risk</th><th>Probability</th><th>Contract</th><th></th></tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.customer_index}>
                    <td className="cust-id">#{row.customer_index}</td>
                    <td>{riskBadge(row.risk_level)}</td>
                    <td className="mono">{pct(row.churn_probability)}</td>
                    <td>{row.contract}</td>
                    <td><Link className="btn btn-sm" to={`/customers/${row.customer_index}`}>Open action center</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </StatusBox>
    </main>
  );
}
