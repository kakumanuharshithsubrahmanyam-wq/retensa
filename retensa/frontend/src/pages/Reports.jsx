import { useEffect, useState } from "react";
import { getDashboard } from "../services/api";

export default function Reports() {
  const [stats, setStats] = useState(null);
  useEffect(() => { getDashboard().then(setStats).catch(() => {}); }, []);
  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Retention Intelligence Report</h1>
          <p>Snapshot from the production model, not illustrative mock counts.</p>
        </div>
      </div>
      <div className="card">
        <ul className="report-list">
          <li className="report-item">Customers scored: {stats ? stats.total_customers.toLocaleString() : "…"}</li>
          <li className="report-item">High risk: {stats ? stats.high_risk : "…"} · Medium: {stats ? stats.medium_risk : "…"} · Low: {stats ? stats.low_risk : "…"}</li>
          <li className="report-item">Top driver: {stats?.top_drivers?.[0]?.feature || "…"}</li>
        </ul>
      </div>
    </main>
  );
}
