import React from "react";
import styles from "./TimestampRedirectCard.module.css";
import TopicBadge from "./TopicBadge.jsx";
import { formatTimestamp } from "../utils/formatTimestamp.js";

export default function TimestampRedirectCard({
  thumbnailUrl,
  videoTitle,
  weakTopic,
  score,
  timestampStart,
  videoId,
  onWatchFromHere,
}) {
  const onClick = () => onWatchFromHere?.({ videoId, seconds: timestampStart });

  return (
    <div className={styles.card}>
      <img className={styles.thumb} src={thumbnailUrl} alt={videoTitle || "video"} />

      <div className={styles.mid}>
        <div className={styles.videoTitle} title={videoTitle}>
          {videoTitle}
        </div>
        <div className={styles.weakRow}>
          <TopicBadge topic={weakTopic} variant="warn" />
          <div className={styles.scoreText}>You scored {score}/10 here</div>
        </div>
      </div>

      <div className={styles.right}>
        <div className={styles.time}>{formatTimestamp(timestampStart)}</div>
        <button className={styles.btn} type="button" onClick={onClick}>
          Watch from here
        </button>
      </div>
    </div>
  );
}

// Quick manual test:
// - Render with thumbnailUrl + timestampStart to verify formatting + button.

