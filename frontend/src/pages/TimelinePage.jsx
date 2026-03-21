import React, { useCallback, useContext, useEffect, useState } from "react";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./TimelinePage.module.css";
import TimestampRedirectCard from "../components/TimestampRedirectCard.jsx";
import SkeletonCard from "../components/SkeletonCard.jsx";

export default function TimelinePage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recs, setRecs] = useState([]);
  const [videos, setVideos] = useState([]);

  const load = useCallback(async ({ silent = false } = {}) => {
    if (!userId) return;
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const [recRes, vidsRes] = await Promise.all([
        api.get(`/api/recommendations/${encodeURIComponent(userId)}`),
        api.get(`/api/playlist/videos`),
      ]);
      setRecs(recRes.data || []);
      setVideos(vidsRes.data || []);
    } catch (e) {
      if (!silent) setError(e?.response?.data?.message || "Failed to load timeline.");
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

  if (loading) {
    return (
      <div className={styles.wrap}>
        <h2 className={styles.title}>Smart Timeline Redirects</h2>
        <div className={styles.sub}>Exact lecture moments to revisit based on your quiz performance.</div>
        <SkeletonCard height={110} />
        <SkeletonCard height={110} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <h2 className={styles.title}>Smart Timeline Redirects</h2>
        <div className={styles.sub}>Exact lecture moments to revisit based on your quiz performance.</div>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={() => window.location.reload()}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <h2 className={styles.title}>Smart Timeline Redirects</h2>
      <div className={styles.sub}>Exact lecture moments to revisit based on your quiz performance.</div>

      <div className={styles.list}>
        {recs.length ? (
          recs.map((r) => {
            const v = videos.find((x) => x.video_id === r.recommended_video_id);
            return (
              <TimestampRedirectCard
                key={`${r.topic}-${r.recommended_video_id}-${r.recommended_timestamp}`}
                thumbnailUrl={v?.thumbnail_url || ""}
                videoTitle={r.video_title}
                weakTopic={r.topic}
                score={r.avg_score}
                timestampStart={r.recommended_timestamp}
                videoId={r.recommended_video_id}
                onWatchFromHere={({ videoId, seconds }) => {
                  const url = `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds)}`;
                  window.open(url, "_blank", "noopener,noreferrer");
                }}
              />
            );
          })
        ) : (
          <div className={styles.emptyState}>No timeline entries yet. Take a quiz to generate recommendations.</div>
        )}
      </div>
    </div>
  );
}

// Quick manual test:
// - After quizzes, `/dashboard/timeline` should show timestamp redirect cards.

