import React from "react";
import styles from "./TopicBadge.module.css";

export default function TopicBadge({ topic, variant = "primary", className = "" }) {
  if (!topic) return null;
  const v = variant; // primary | success | warn | amber
  return (
    <span className={[styles.badge, styles[v], className].filter(Boolean).join(" ")}>
      {topic}
    </span>
  );
}

// Quick manual test:
// - Render <TopicBadge topic="Sorting" />

