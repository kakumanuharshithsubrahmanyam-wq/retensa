import { useNavigate } from "react-router-dom";
import { useState } from "react";

export default function SimulatorPage() {
  const [value, setValue] = useState("");
  const navigate = useNavigate();
  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>What-If Churn Simulator</h1>
          <p>Open any customer by dataset row index to run model simulations on the production pipeline.</p>
        </div>
      </div>
      <div className="card">
        <p className="card-sub" style={{ marginBottom: 12 }}>
          Enter a customer index from the scored dataset, then continue to the Action Center simulator.
        </p>
        <div className="flex gap-8">
          <input
            className="filter-input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="Customer index"
          />
          <button
            className="btn btn-primary"
            disabled={!/^\d+$/.test(value.trim())}
            onClick={() => navigate(`/customers/${value.trim()}`)}
          >
            Open customer
          </button>
        </div>
      </div>
    </main>
  );
}
