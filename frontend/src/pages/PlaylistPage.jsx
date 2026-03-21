import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api.js";
import styles from "./PlaylistPage.module.css";
import VideoCard from "../components/VideoCard.jsx";
import SkeletonCard from "../components/SkeletonCard.jsx";

function EmptyState({ onIngest }) {
  return (
    <div className={styles.emptyState}>
      <svg width="64" height="64" viewBox="0 0 64 64" aria-hidden="true">
        <rect x="20" y="16" width="24" height="32" rx="6" fill="rgba(108,99,255,0.2)" stroke="rgba(108,99,255,0.6)" />
        <path d="M24 30h16" stroke="rgba(0,217,181,0.8)" strokeWidth="3" strokeLinecap="round" />
      </svg>
      <div className={styles.emptyText}>No videos loaded yet. Ingest the playlist to start learning.</div>
      <button className={styles.primaryBtn} type="button" onClick={onIngest}>
        Load Playlist →
      </button>
    </div>
  );
}

export default function PlaylistPage() {
  const navigate = useNavigate();
  const [videos, setVideos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");

  const loadVideos = async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const res = await api.get("/api/playlist/videos");
      setVideos(res.data || []);
    } catch (e) {
      if (!silent) setError(e?.response?.data?.message || "Failed to load playlist.");
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    loadVideos();
  }, []);

  useEffect(() => {
    // Poll while processing so user doesn't have to refresh manually.
    if (!videos?.length) return;
    const hasUnprocessed = videos.some((v) => !v.processed);
    if (!hasUnprocessed) return;

    const id = setInterval(() => {
      loadVideos({ silent: true });
    }, 5000);
    return () => clearInterval(id);
  }, [videos]);

  const onIngest = async () => {
    setIngesting(true);
    setError("");
    try {
      await api.post("/api/playlist/ingest", {});
      // Reload to pick up the inserted documents; processed will update via Celery.
      await loadVideos();
    } catch (e) {
      setError(e?.response?.data?.message || "Ingest failed.");
    } finally {
      setIngesting(false);
    }
  };

  /** Re-run Celery for every video so quiz questions match the latest generator (e.g. after a code fix). */
  const onRegenerateQuizzes = async () => {
    if (
      !window.confirm(
        "Regenerate quiz questions for ALL playlist videos? This re-runs processing in the background and may take several minutes."
      )
    ) {
      return;
    }
    setIngesting(true);
    setError("");
    try {
      await api.post("/api/playlist/ingest", { reprocess_all: true });
      await loadVideos();
    } catch (e) {
      setError(e?.response?.data?.message || "Regenerate failed.");
    } finally {
      setIngesting(false);
    }
  };

  const videoCount = videos?.length || 0;

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.headerRow}>
          <h2 className={styles.title}>DAA Playlist</h2>
          <div className={styles.badge}>{videoCount}</div>
        </div>
        <div className={styles.grid}>
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} height={260} />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.headerRow}>
          <h2 className={styles.title}>DAA Playlist</h2>
          <div className={styles.badge}>{videoCount}</div>
        </div>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={loadVideos}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!videos?.length) {
    return (
      <div className={styles.wrap}>
        <div className={styles.headerRow}>
          <h2 className={styles.title}>DAA Playlist</h2>
          <div className={styles.badge}>{videoCount}</div>
        </div>
        <EmptyState onIngest={onIngest} />
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.headerRow}>
        <h2 className={styles.title}>
          DAA Playlist <span className={styles.titleBadge}>{videoCount} videos</span>
        </h2>
        {videos?.length ? (
          <div className={styles.headerActions}>
            {videos.some((v) => !v.processed) ? (
              <button className={styles.primaryBtn} type="button" onClick={onIngest} disabled={ingesting}>
                {ingesting ? "Processing..." : "Load / Retry"}
              </button>
            ) : null}
            <button
              className={styles.secondaryBtn}
              type="button"
              onClick={onRegenerateQuizzes}
              disabled={ingesting}
              title="Use after updating quiz generation — rebuilds questions from transcripts for every video"
            >
              {ingesting ? "…" : "Regenerate quizzes"}
            </button>
          </div>
        ) : null}
      </div>

      <div className={styles.grid}>
        {videos.map((v) => (
          <VideoCard
            key={v.video_id}
            video={{
              ...v,
              thumbnailUrl: v.thumbnail_url,
              video_id: v.video_id,
              topics: v.topics || [],
            }}
            onClick={() => navigate(`/dashboard/quiz/${v.video_id}`)}
          />
        ))}
      </div>
    </div>
  );
}

// Quick manual test:
// - Go to `/dashboard/playlist`
// - Click "Ingest Playlist"
// - Refresh and confirm `/api/playlist/videos` shows inserted rows

