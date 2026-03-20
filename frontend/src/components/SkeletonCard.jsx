import React from "react";
import styles from "./SkeletonCard.module.css";

export default function SkeletonCard({ width = "100%", height = 120 }) {
  return (
    <div className={styles.skeleton} style={{ width, height }} aria-hidden="true">
      <div className="shimmer" style={{ width: "100%", height: "100%", borderRadius: 12 }} />
    </div>
  );
}

// Quick manual test:
// - Render <SkeletonCard height={80} />

