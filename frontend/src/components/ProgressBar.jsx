import React from "react";
import styles from "./ProgressBar.module.css";

export default function ProgressBar({ value, max = 10, color = "primary" }) {
  const pct = max > 0 ? Math.max(0, Math.min(1, value / max)) * 100 : 0;
  return (
    <div className={styles.outer} aria-label={`progress ${pct.toFixed(1)}%`}>
      <div className={[styles.inner, styles[color]].filter(Boolean).join(" ")} style={{ width: `${pct}%` }} />
    </div>
  );
}

// Quick manual test:
// - <ProgressBar value={7} color="primary" />

