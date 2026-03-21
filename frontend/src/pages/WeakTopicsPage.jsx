import React, { useCallback, useContext, useEffect, useState } from "react";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./WeakTopicsPage.module.css";
import RadarChart from "../components/RadarChart.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import { formatTimestamp, toYouTubeUrl } from "../utils/formatTimestamp.js";
import TopicBadge from "../components/TopicBadge.jsx";
import SkeletonCard from "../components/SkeletonCard.jsx";

function scoreVariant(score) {
  if (score >= 8) return { badge: "success", bar: "success" };
  if (score >= 4) return { badge: "amber", bar: "amber" };
  return { badge: "warn", bar: "warn" };
}

export default function WeakTopicsPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recs, setRecs] = useState([]);
  const [progress, setProgress] = useState(null);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!userId) return;
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const [recRes, progRes] = await Promise.all([
        api.get(`/api/recommendations/${encodeURIComponent(userId)}`),
        api.get(`/api/progress/${encodeURIComponent(userId)}`),
      ]);
      setRecs(recRes.data || []);
      setProgress(progRes.data || null);
    } catch (e) {
      if (!silent) setError(e?.response?.data?.message || "Failed to load weak topics.");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    load({ silent: false });
  }, [load]);

  useEffect(() => {
    const onVis = () => {
      if (document.visibilityState === "visible" && userId) load({ silent: true });
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [userId, load]);

  const empty = !loading && !error && (!recs || recs.length === 0);

  if (loading) {
    return (
      <div className={styles.wrap}>
        <h2 className={styles.title}>Weak Topics</h2>
        <SkeletonCard height={320} />
        <SkeletonCard height={90} />
        <SkeletonCard height={90} />
        <SkeletonCard height={90} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <h2 className={styles.title}>Weak Topics</h2>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={() => window.location.reload()}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (empty) {
    return (
      <div className={styles.wrap}>
        <h2 className={styles.title}>Weak Topics</h2>
        <div className={styles.emptyState}>
          <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true">
            <path d="M22 12h20l10 20-10 20H22L12 32z" fill="rgba(108,99,255,0.15)" stroke="rgba(108,99,255,0.7)" strokeWidth="2" />
          </svg>
          <div className={styles.emptyText}>Take a quiz to unlock your weak-topic recommendations.</div>
          <button className={styles.primaryBtn} type="button" onClick={() => (window.location.href = "/dashboard/playlist")}>
            Start your first quiz →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Weak Topics</h2>

      <div className={styles.chartWrap}>
        <RadarChart scores={progress?.topic_scores || {}} />
      </div>

      <div className={styles.list}>
        {recs.map((r) => {
          const score = Number(r.avg_score || 0);
          const v = scoreVariant(score);
          return (
            <div key={r.topic} className={styles.row}>
              <div className={styles.topicName}>{r.topic}</div>
              <TopicBadge topic={`${score.toFixed(1)}/10`} variant={v.badge} />
              <div className={styles.barWrap}>
                <ProgressBar value={score} max={10} color={v.bar} />
              </div>
              <button
                className={styles.revisitBtn}
                type="button"
                onClick={() => {
                  const url = toYouTubeUrl(r.recommended_video_id, r.recommended_timestamp);
                  window.open(url, "_blank", "noopener,noreferrer");
                }}
              >
                Revisit @ {formatTimestamp(Number(r.recommended_timestamp || 0))}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Quick manual test:
// - `/dashboard/weak-topics` should show radar + weak list.

