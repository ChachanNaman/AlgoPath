import React from "react";
import styles from "./QuizCard.module.css";
import TopicBadge from "./TopicBadge.jsx";

export default function QuizCard({ question, index, total, difficulty, topicTag, children }) {
  return (
    <div className={styles.card}>
      <div className={styles.header}>
        <div className={styles.hTitle}>
          Question {index} of {total}
        </div>
        <div className={styles.meta}>
          {difficulty ? <span className={styles.diff}>{difficulty}</span> : null}
          {topicTag ? <TopicBadge topic={topicTag} /> : null}
        </div>
      </div>
      {question ? <div className={styles.questionText}>{question}</div> : null}
      {children}
    </div>
  );
}

// Quick manual test:
// - Render QuizCard with dummy question and verify layout.

