import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { getCustomers } from "../services/api";
import StatusBox, { pct, riskBadge } from "../components/ui";

export default function Customers() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [risk, setRisk] = useState("");
  const [minProb, setMinProb] = useState("");
  const [page, setPage] = useState(1);
  const [params] = useSearchParams();
  const [search, setSearch] = useState(params.get("q") || "");

  useEffect(() => {
    getCustomers()
      .then(setRows)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let list = rows;
    if (search) list = list.filter((r) => String(r.customer_index).includes(search.trim()));
    if (risk) list = list.filter((r) => r.risk_level.toLowerCase() === risk.toLowerCase());
    if (minProb) list = list.filter((r) => r.churn_probability * 100 >= Number(minProb));
    return list;
  }, [rows, search, risk, minProb]);

  const pageSize = 12;
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const pageRows = filtered.slice((page - 1) * pageSize, page * pageSize);

  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Customer Risk Explorer</h1>
          <p>Find the customers who need attention before they leave. IDs are dataset row indexes.</p>
        </div>
      </div>
      <div className="toolbar">
        <div className="search-field" style={{ flex: "0 0 240px" }}>
          <input value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} placeholder="Search customer index..." />
        </div>
        <select className="filter-select" value={risk} onChange={(e) => { setRisk(e.target.value); setPage(1); }}>
          <option value="">All risk levels</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>
        <select className="filter-select" value={minProb} onChange={(e) => { setMinProb(e.target.value); setPage(1); }}>
          <option value="">Any probability</option>
          <option value="80">80%+</option>
          <option value="60">60%+</option>
          <option value="35">35%+</option>
        </select>
      </div>
      <StatusBox loading={loading} error={error} loadingText="Loading customers from the RETENSA model…">
        <div className="card">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Customer</th><th>Probability</th><th>Risk</th><th>Tenure</th><th>Monthly Charges</th><th>Contract</th><th></th>
                </tr>
              </thead>
              <tbody>
                {pageRows.map((row) => (
                  <tr key={row.customer_index}>
                    <td className="cust-id">#{row.customer_index}</td>
                    <td className="mono">{pct(row.churn_probability)}</td>
                    <td>{riskBadge(row.risk_level)}</td>
                    <td className="mono">{row.tenure} mo</td>
                    <td className="mono">${row.monthly_charges.toFixed(2)}</td>
                    <td>{row.contract}</td>
                    <td><Link className="btn btn-sm" to={`/customers/${row.customer_index}`}>View</Link></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>Page {page} of {totalPages} · {filtered.length} customers</span>
            <button className="page-btn" disabled={page <= 1} onClick={() => setPage(page - 1)}>‹</button>
            <button className="page-btn" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>›</button>
          </div>
        </div>
      </StatusBox>
    </main>
  );
}
