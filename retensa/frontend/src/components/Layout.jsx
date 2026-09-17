import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { getHealth } from "../services/api";

const NAV = [
  { to: "/", label: "Overview", end: true },
  { to: "/customers", label: "Customers" },
  { to: "/new-customer", label: "Analyze New Customer" },
  { to: "/risk-intelligence", label: "Risk Intelligence" },
  { to: "/simulator", label: "What-If Simulator" },
  { to: "/retention", label: "Retention Center" },
  { to: "/model-performance", label: "Model Performance" },
  { to: "/assistant", label: "AI Assistant" },
  { to: "/reports", label: "Reports" },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [engine, setEngine] = useState("checking");
  const navigate = useNavigate();

  useEffect(() => {
    getHealth()
      .then((body) => setEngine(body.status === "ok" ? "online" : "degraded"))
      .catch(() => setEngine("offline"));
  }, []);

  function submitSearch(event) {
    event.preventDefault();
    const value = search.trim();
    if (/^\d+$/.test(value)) navigate(`/customers/${value}`);
    else navigate(`/customers?q=${encodeURIComponent(value)}`);
  }

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-brand">
          <div className="brand-mark">R</div>
          <div className="brand-text">
            <div className="brand-name">RETENSA</div>
            <div className="brand-sub">AI Retention Intelligence</div>
          </div>
          <button className="sidebar-toggle" onClick={() => setCollapsed((v) => !v)} aria-label="Collapse sidebar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 18l-6-6 6-6"/></svg>
          </button>
        </div>
        <nav className="nav-group">
          <div className="nav-label">Workspace</div>
          <ul className="nav-list">
            {NAV.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                  onClick={() => setMobileOpen(false)}
                >
                  <span>{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot" />
            <span>{engine === "online" ? "System operational" : engine === "offline" ? "Backend offline" : "Checking…"}</span>
          </div>
        </div>
      </aside>
      <div className="sidebar-scrim" onClick={() => setMobileOpen(false)} style={{ display: mobileOpen ? "block" : "none" }} />
      <div className="app-main">
        <header className="topbar">
          <button className="mobile-menu-btn" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
          </button>
          <form className="search-field" onSubmit={submitSearch}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search customer index..."
              aria-label="Search customers"
            />
          </form>
          <div className="topbar-right">
            <div className="engine-status">
              <span className="status-dot" />
              <span>{engine === "online" ? "AI Engine Online" : "Engine offline"}</span>
            </div>
            <div className="profile-chip">
              <div className="profile-avatar">RT</div>
              <span className="profile-name">RETENSA</span>
            </div>
          </div>
        </header>
        <Outlet />
      </div>
    </div>
  );
}
