import React, { useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./DashboardHome.module.css";
import SkeletonCard from "../components/SkeletonCard.jsx";
import VideoCard from "../components/VideoCard.jsx";
import TimestampRedirectCard from "../components/TimestampRedirectCard.jsx";
import TopicBadge from "../components/TopicBadge.jsx";

function greetingForNow() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export default function DashboardHome() {
  const navigate = useNavigate();
  const { user } = useContext(AuthContext);

  const [progress, setProgress] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [videos, setVideos] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const userId = user?.email;

  const weakestTopicName = useMemo(() => {
    if (!progress) return null;
    const wt = progress.weakest_topic;
    return wt || null;
  }, [progress]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const [progRes, recRes, vidsRes] = await Promise.all([
          api.get(`/api/progress/${encodeURIComponent(userId)}`),
          api.get(`/api/recommendations/${encodeURIComponent(userId)}`),
          api.get(`/api/playlist/videos`),
        ]);
        if (!mounted) return;
        setProgress(progRes.data);
        setRecommendations(recRes.data || []);
        setVideos(vidsRes.data || []);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.message || "Failed to load dashboard data.");
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
        <div className={styles.sectionTitle}>Dashboard</div>
        <div className={styles.statsGrid}>
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} height={110} />
          ))}
        </div>
        <div className={styles.splitGrid}>
          <SkeletonCard height={220} />
          <SkeletonCard height={220} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  const overallAvg = progress?.overall_avg_score ?? 0;
  const totalAttempted = progress?.total_questions_attempted ?? 0;
  const streakDays = progress?.streak_days ?? 0;

  const processedVideos = (videos || []).filter((v) => v.processed).slice(0, 3);
  const revisitList = (recommendations || []).slice(0, 3);

  return (
    <div className={styles.wrap}>
      <div className={styles.sectionTitle}>
        {greetingForNow()}, <span className={styles.name}>{user?.name || "User"}</span>
      </div>

      <div className={styles.statsGrid}>
        <div className={`${styles.statCard} ${styles.statPrimary}`}>
          <div className={styles.statLabel}>Overall Score</div>
          <div className={styles.statValue}>{overallAvg.toFixed(1)} / 10</div>
          <div className={styles.statSub}>Your average performance</div>
        </div>
        <div className={`${styles.statCard} ${styles.statSecondary}`}>
          <div className={styles.statLabel}>Questions Attempted</div>
          <div className={styles.statValue}>{totalAttempted}</div>
          <div className={styles.statSub}>Total quiz submissions</div>
        </div>
        <div className={`${styles.statCard} ${styles.statAmber}`}>
          <div className={styles.statLabel}>Day Streak</div>
          <div className={styles.statValue}>{streakDays}</div>
          <div className={styles.statSub}>Consistency matters</div>
        </div>
        <div className={`${styles.statCard} ${styles.statWarn}`}>
          <div className={styles.statLabel}>Weakest Topic</div>
          <div className={styles.statValue}>{weakestTopicName || "—"}</div>
          <div className={styles.statSub}>Needs more practice</div>
        </div>
      </div>

      <div className={styles.splitGrid}>
        <div className={styles.panel}>
          <div className={styles.panelTitle}>Continue Learning</div>
          <div className={styles.cardGrid}>
            {processedVideos.length ? (
              processedVideos.map((v) => (
                <div key={v.video_id} className={styles.compactWrap}>
                  <VideoCard
                    variant="compact"
                    video={{
                      ...v,
                      thumbnailUrl: v.thumbnail_url,
                      video_id: v.video_id,
                      topics: v.topics || [],
                      processed: v.processed,
                    }}
                    onClick={() => navigate(`/dashboard/quiz/${v.video_id}`)}
                    onStartQuiz={(id) => navigate(`/dashboard/quiz/${id}`)}
                  />
                </div>
              ))
            ) : (
              <div className={styles.emptyInner}>
                <div>No processed videos yet. Ingest the playlist.</div>
              </div>
            )}
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelTitle}>Revisit These</div>
          <div className={styles.redirectList}>
            {revisitList.length ? (
              revisitList.map((r) => (
                <TimestampRedirectCard
                  key={r.recommended_video_id + r.recommended_timestamp}
                  thumbnailUrl={videos?.find((v) => v.video_id === r.recommended_video_id)?.thumbnail_url || ""}
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
              ))
            ) : (
              <div className={styles.emptyInner}>
                No weak topics yet. Take a quiz to see recommendations.
              </div>
            )}
          </div>
        </div>
      </div>

      {recommendations?.length ? null : (
        <div className={styles.bottomSpacer} />
      )}
    </div>
  );
}

// Quick manual test:
// - After login, `/dashboard` should show stats and recommendations cards.


