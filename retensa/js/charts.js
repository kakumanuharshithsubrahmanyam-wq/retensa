/* ============================================================
   RETENSA — Chart Builders (Chart.js)
   ============================================================ */

const CHART_COLORS = {
  low: "#34c98a",
  medium: "#e8b339",
  high: "#f0873f",
  critical: "#ef5a6f",
  accent: "#4f6bff",
  accentSoft: "rgba(79,107,255,0.18)",
  grid: "rgba(255,255,255,0.06)",
  text: "#97a1b5",
};

Chart.defaults.font.family = "Inter, sans-serif";
Chart.defaults.font.size = 11.5;
Chart.defaults.color = CHART_COLORS.text;

const chartRegistry = {};

function destroyChart(id) {
  if (chartRegistry[id]) {
    chartRegistry[id].destroy();
    delete chartRegistry[id];
  }
}

function renderDonut(canvasId) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  chartRegistry[canvasId] = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Low", "Medium", "High", "Critical"],
      datasets: [{
        data: [RISK_SUMMARY.LOW, RISK_SUMMARY.MEDIUM, RISK_SUMMARY.HIGH, RISK_SUMMARY.CRITICAL],
        backgroundColor: [CHART_COLORS.low, CHART_COLORS.medium, CHART_COLORS.high, CHART_COLORS.critical],
        borderWidth: 0,
        hoverOffset: 4,
      }],
    },
    options: {
      cutout: "68%",
      plugins: {
        legend: {
          position: "bottom",
          labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, padding: 16 },
        },
        tooltip: { backgroundColor: "#151c2c", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1, padding: 10 },
      },
    },
  });
}

function renderTrendLine(canvasId, range) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const series = CHURN_TREND[range] || CHURN_TREND["30D"];
  const labels = series.map((p) =>
    p.date.toLocaleDateString(undefined, { month: "short", day: "numeric" })
  );
  chartRegistry[canvasId] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        data: series.map((p) => p.value),
        borderColor: CHART_COLORS.accent,
        backgroundColor: CHART_COLORS.accentSoft,
        fill: true,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 2,
      }],
    },
    options: {
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#151c2c", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1, padding: 10 } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 8 } },
        y: { grid: { color: CHART_COLORS.grid }, ticks: { callback: (v) => v + "%" } },
      },
    },
  });
}

function renderHorizontalBar(canvasId, labels, values, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  chartRegistry[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: color || CHART_COLORS.accent, borderRadius: 5, maxBarThickness: 22 }],
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#151c2c", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1 } },
      scales: {
        x: { grid: { color: CHART_COLORS.grid }, ticks: { callback: (v) => v + "%" } },
        y: { grid: { display: false } },
      },
    },
  });
}

function renderVerticalBar(canvasId, labels, values, color) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  chartRegistry[canvasId] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: color || CHART_COLORS.accent, borderRadius: 5, maxBarThickness: 34 }],
    },
    options: {
      plugins: { legend: { display: false }, tooltip: { backgroundColor: "#151c2c", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1 } },
      scales: {
        x: { grid: { display: false } },
        y: { grid: { color: CHART_COLORS.grid }, ticks: { callback: (v) => v + "%" } },
      },
    },
  });
}

function renderProbDistribution(canvasId) {
  const buckets = [0, 0, 0, 0, 0];
  CUSTOMERS.forEach((c) => {
    const idx = Math.min(4, Math.floor(c.probability / 20));
    buckets[idx]++;
  });
  renderVerticalBar(canvasId, ["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"], buckets, CHART_COLORS.accent);
}

function renderRiskDistBar(canvasId) {
  renderVerticalBar(
    canvasId,
    ["Low", "Medium", "High", "Critical"],
    [RISK_SUMMARY.LOW, RISK_SUMMARY.MEDIUM, RISK_SUMMARY.HIGH, RISK_SUMMARY.CRITICAL],
    [CHART_COLORS.low, CHART_COLORS.medium, CHART_COLORS.high, CHART_COLORS.critical]
  );
}
