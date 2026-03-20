import React from "react";
import styles from "./VideoCard.module.css";
import TopicBadge from "./TopicBadge.jsx";

export default function VideoCard({
  video,
  onStartQuiz,
  onClick,
  topics = [],
  variant = "default",
}) {
  const {
    thumbnailUrl,
    title,
    processed = false,
    topics: videoTopics = [],
    video_id,
    processing_error,
  } = video || {};

  const visibleTopics = (videoTopics || topics || []).slice(0, 3);
  const extra = (videoTopics || topics || []).length - visibleTopics.length;
  const clickable = Boolean(processed);

  return (
    <div
      className={[styles.card, variant === "compact" ? styles.cardCompact : ""].filter(Boolean).join(" ")}
      onClick={clickable ? onClick : undefined}
      role={clickable ? "button" : "group"}
      tabIndex={clickable ? 0 : -1}
      style={{ cursor: clickable ? "pointer" : "default" }}
    >
      <div className={styles.thumbWrap}>
        <img className={styles.thumb} src={thumbnailUrl} alt={title || "video"} />
      </div>

      <div className={styles.body}>
        <div className={styles.title} title={title}>
          {title || "Untitled"}
        </div>

        <div className={styles.topics}>
          {visibleTopics.map((t) => (
            <TopicBadge key={t} topic={t} />
          ))}
          {extra > 0 ? <span className={styles.more}>+{extra} more</span> : null}
        </div>

        <div className={styles.footer}>
          {processed ? (
            <button
              className={styles.primaryBtn}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onStartQuiz?.(video_id);
              }}
            >
              Start Quiz
            </button>
          ) : (
            <div
              className={[styles.processingBadge, processing_error ? styles.failedBadge : ""].filter(Boolean).join(" ")}
              title={processing_error ? String(processing_error).slice(0, 200) : undefined}
            >
              {processing_error ? `Failed: ${String(processing_error).slice(0, 28)}…` : "Processing..."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Quick manual test:
// - Render VideoCard with processed=true/false and verify badge/button.

