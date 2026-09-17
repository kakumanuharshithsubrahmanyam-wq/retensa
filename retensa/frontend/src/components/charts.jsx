import { Chart as ChartJS, ArcElement, BarElement, CategoryScale, Legend, LinearScale, Tooltip } from "chart.js";
import { Bar, Doughnut } from "react-chartjs-2";

ChartJS.register(ArcElement, BarElement, CategoryScale, LinearScale, Legend, Tooltip);
ChartJS.defaults.font.family = "Inter, sans-serif";
ChartJS.defaults.color = "#97a1b5";

const COLORS = { low: "#34c98a", medium: "#e8b339", high: "#f0873f", critical: "#ef5a6f", accent: "#4f6bff" };

export function RiskDonut({ counts }) {
  return (
    <Doughnut
      data={{
        labels: ["Low", "Medium", "High", "Critical"],
        datasets: [{
          data: [counts.LOW || 0, counts.MEDIUM || 0, counts.HIGH || 0, counts.CRITICAL || 0],
          backgroundColor: [COLORS.low, COLORS.medium, COLORS.high, COLORS.critical],
          borderWidth: 0,
        }],
      }}
      options={{ cutout: "68%", plugins: { legend: { position: "bottom" } } }}
    />
  );
}

export function HorizontalBars({ labels, values, color = COLORS.accent }) {
  return (
    <Bar
      data={{
        labels,
        datasets: [{ data: values, backgroundColor: color, borderRadius: 5, maxBarThickness: 22 }],
      }}
      options={{
        indexAxis: "y",
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: "rgba(255,255,255,0.06)" }, ticks: { callback: (v) => `${v}%` } },
          y: { grid: { display: false } },
        },
      }}
    />
  );
}

export function VerticalBars({ labels, values, colors }) {
  return (
    <Bar
      data={{
        labels,
        datasets: [{ data: values, backgroundColor: colors || COLORS.accent, borderRadius: 5, maxBarThickness: 34 }],
      }}
      options={{
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: "rgba(255,255,255,0.06)" } },
        },
      }}
    />
  );
}
