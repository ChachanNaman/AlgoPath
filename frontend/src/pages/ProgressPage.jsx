import React, { useContext, useEffect, useMemo, useState } from "react";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./ProgressPage.module.css";
import ProgressBar from "../components/ProgressBar.jsx";
import SkeletonCard from "../components/SkeletonCard.jsx";
import TopicBadge from "../components/TopicBadge.jsx";

import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Filler,
  Tooltip,
  Legend,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(LineElement, PointElement, LinearScale, CategoryScale, Filler, Tooltip, Legend);

function targetLinePlugin(targetY = 7) {
  return {
    id: "targetLine",
    afterDraw: (chart) => {
      const yScale = chart.scales?.y;
      if (!yScale) return;
      const { ctx, chartArea } = chart;
      const y = yScale.getPixelForValue(targetY);
      ctx.save();
      ctx.strokeStyle = "rgba(108,99,255,0.55)";
      ctx.setLineDash([6, 6]);
      ctx.beginPath();
      ctx.moveTo(chartArea.left, y);
      ctx.lineTo(chartArea.right, y);
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = "#8A8FA8";
      ctx.font = "12px sans-serif";
      ctx.fillText("Target", chartArea.left + 8, y - 6);
      ctx.restore();
    },
  };
}

function masteryFor(score) {
  if (score >= 8) return { label: "Mastered", variant: "success" };
  if (score >= 5) return { label: "Learning", variant: "amber" };
  return { label: "Needs Work", variant: "warn" };
}

export default function ProgressPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [progress, setProgress] = useState(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/api/progress/${encodeURIComponent(userId)}`);
        if (!mounted) return;
        setProgress(res.data);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.message || "Failed to load progress.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    if (userId) load();
    return () => {
      mounted = false;
    };
  }, [userId]);

  if (loading) {
    return (
      <div className={styles.wrap}>
        <SkeletonCard height={120} />
        <SkeletonCard height={320} />
        <SkeletonCard height={140} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={() => window.location.reload()}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  const overallAvg = progress?.overall_avg_score ?? 0;
  const topicScores = progress?.topic_scores || {};
  const daily = progress?.daily_scores || [];

  const labels = daily.map((d) => (d.date ? d.date.slice(5) : ""));
  const dataPoints = daily.map((d) => Number(d.avg_score || 0));

  const chartData = {
    labels,
    datasets: [
      {
        label: "Score trend",
        data: dataPoints,
        borderColor: "#6C63FF",
        backgroundColor: "rgba(108,99,255,0.08)",
        fill: true,
        tension: 0.3,
        pointRadius: 3,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: "#8A8FA8" }, grid: { display: false } },
      y: {
        min: 0,
        max: 10,
        ticks: { stepSize: 2, color: "#8A8FA8" },
        grid: { color: "rgba(255,255,255,0.08)" },
      },
    },
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.topGrid}>
        <div className={styles.leftPanel}>
          <div className={styles.overallScore}>
            <span className={styles.gradientText}>{overallAvg.toFixed(1)}</span>
            <span className={styles.overallSub}> / 10</span>
          </div>

          <div className={styles.statsGrid}>
            <div className={styles.statItem}>
              <div className={styles.statLabel}>Total Questions</div>
              <div className={styles.statValue}>{progress?.total_questions_attempted ?? 0}</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statLabel}>Streak</div>
              <div className={styles.statValue}>{progress?.streak_days ?? 0} days</div>
            </div>
            <div className={styles.statItem}>
              <div className={styles.statLabel}>Strongest Topic</div>
              <TopicBadge topic={progress?.strongest_topic || "—"} variant="success" />
            </div>
            <div className={styles.statItem}>
              <div className={styles.statLabel}>Weakest Topic</div>
              <TopicBadge topic={progress?.weakest_topic || "—"} variant="warn" />
            </div>
          </div>
        </div>

        <div className={styles.chartPanel}>
          <div className={styles.chartTitle}>Score Trend (Last 14 Days)</div>
          <div className={styles.chartWrap}>
            <Line data={chartData} options={chartOptions} plugins={[targetLinePlugin(7)]} />
          </div>
        </div>
      </div>

      <div className={styles.sectionTitle}>Topic Mastery</div>
      <div className={styles.topicGrid}>
        {Object.entries(topicScores).length ? (
          Object.entries(topicScores).map(([topic, score]) => {
            const mastery = masteryFor(Number(score || 0));
            const pct = Math.round((Number(score || 0) / 10) * 100);
            return (
              <div key={topic} className={styles.topicCard}>
                <div className={styles.topicHeader}>
                  <div className={styles.topicName}>{topic}</div>
                  <TopicBadge topic={mastery.label} variant={mastery.variant} />
                </div>
                <div className={styles.progressRow}>
                  <ProgressBar value={Number(score || 0)} max={10} color={mastery.variant === "success" ? "success" : mastery.variant === "amber" ? "amber" : "warn"} />
                </div>
                <div className={styles.scorePct}>{pct}%</div>
              </div>
            );
          })
        ) : (
          <div className={styles.emptyState}>No progress yet. Submit a quiz to generate mastery.</div>
        )}
      </div>
    </div>
  );
}

// Quick manual test:
// - `/dashboard/progress` should show stats + chart and topic cards.

