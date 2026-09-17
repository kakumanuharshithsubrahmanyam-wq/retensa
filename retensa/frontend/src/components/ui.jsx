export default function StatusBox({ loading, error, children, loadingText = "Loading…" }) {
  if (loading) return <div className="page-status">{loadingText}</div>;
  if (error) return <div className="page-status error">{error}</div>;
  return children;
}

export function riskBadge(level) {
  const key = String(level || "MEDIUM").toUpperCase();
  const cls = key.includes("CRIT") ? "critical" : key.includes("HIGH") ? "high" : key.includes("LOW") ? "low" : "medium";
  return <span className={`badge badge-${cls}`}>{key}</span>;
}

export function pct(value) {
  return `${(Number(value) * 100).toFixed(2)}%`;
}
