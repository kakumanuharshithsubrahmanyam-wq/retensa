import { useEffect, useState } from "react";
import { getDashboard } from "../services/api";
import { HorizontalBars, VerticalBars } from "../components/charts";
import StatusBox from "../components/ui";

const BAND_COLORS = ["#34c98a", "#e8b339", "#f0873f", "#ef5a6f"];

export default function RiskIntelligence() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    getDashboard().then(setData).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);
  return (
    <main className="page">
      <div className="page-head">
        <div>
          <h1>Risk Intelligence</h1>
          <p>Portfolio-level view of where predicted churn risk concentrates.</p>
        </div>
      </div>
      <StatusBox loading={loading} error={error}>
        {data && (
          <div className="chart-grid">
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Risk Distribution</div>
              <VerticalBars
                labels={["Low", "Medium", "High", "Critical"]}
                values={["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((k) => data.visual_counts[k])}
                colors={BAND_COLORS}
              />
            </div>
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Probability Histogram</div>
              <VerticalBars labels={data.probability_histogram.labels} values={data.probability_histogram.counts} />
            </div>
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Top Churn Drivers (mean |SHAP|)</div>
              <HorizontalBars
                labels={data.top_drivers.map((d) => d.feature)}
                values={data.top_drivers.map((d) => Number((d.importance * 100).toFixed(2)))}
              />
            </div>
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Avg predicted risk by Contract</div>
              <HorizontalBars labels={data.risk_by_contract.map((d) => d.label)} values={data.risk_by_contract.map((d) => d.value)} />
            </div>
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Avg predicted risk by Tenure</div>
              <HorizontalBars labels={data.risk_by_tenure.map((d) => d.label)} values={data.risk_by_tenure.map((d) => d.value)} />
            </div>
            <div className="card chart-card">
              <div className="card-title" style={{ marginBottom: 10 }}>Avg predicted risk by Monthly Charges</div>
              <HorizontalBars labels={data.risk_by_charges.map((d) => d.label)} values={data.risk_by_charges.map((d) => d.value)} />
            </div>
          </div>
        )}
      </StatusBox>
    </main>
  );
}
