import React from "react";
import { Radar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const axisLabels = [
  "Sorting",
  "Graphs",
  "Dynamic Programming",
  "Greedy",
  "Divide & Conquer",
  "Trees",
  "Hashing",
  "Backtracking",
  "Asymptotic Analysis",
];

export default function RadarChart({ scores = {} }) {
  const data = axisLabels.map((k) => (typeof scores[k] === "number" ? scores[k] : 0));

  const chartData = {
    labels: axisLabels,
    datasets: [
      {
        label: "Your score",
        data,
        backgroundColor: "rgba(108,99,255,0.15)",
        borderColor: "#6C63FF",
        pointBackgroundColor: "#00D9B5",
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      r: {
        min: 0,
        max: 10,
        ticks: { color: "#8A8FA8", stepSize: 2 },
        grid: { color: "rgba(255,255,255,0.08)" },
        angleLines: { color: "rgba(255,255,255,0.08)" },
        pointLabels: { color: "#8A8FA8", font: { size: 10 } },
      },
    },
  };

  return (
    <div style={{ width: "100%", height: 280 }}>
      <Radar data={chartData} options={options} />
    </div>
  );
}

// Quick manual test:
// - <RadarChart scores={{ Sorting: 3.2, Graphs: 7.8 }} />

