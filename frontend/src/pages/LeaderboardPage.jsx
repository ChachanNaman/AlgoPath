import React, { useContext, useEffect, useState } from "react";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./LeaderboardPage.module.css";

export default function LeaderboardPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [rows, setRows] = useState([]);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/api/leaderboard");
      setRows(res.data || []);
    } catch (e) {
      setError(e?.response?.data?.message || "Failed to load leaderboard.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const myRow = rows.find((r) => r.user_id === userId);
  const myRank = myRow?.rank || null;

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.headerRow}>
          <h2 className={styles.title}>Leaderboard</h2>
          <div className={styles.refreshBtn} />
        </div>
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLine} />
        <div className={styles.skeletonLine} />
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={load}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.headerRow}>
        <div className={styles.heading}>
          <h2 className={styles.title}>Leaderboard</h2>
          {myRank ? <span className={styles.myRank}>Your rank: #{myRank}</span> : null}
        </div>
        <button className={styles.refreshBtn} type="button" onClick={load}>
          Refresh
        </button>
      </div>

      <table className={styles.table}>
        <thead>
          <tr>
            <th>Rank</th>
            <th>Name</th>
            <th>Avg Score</th>
            <th>Questions Attempted</th>
            <th>Strongest Topic</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const isMe = r.user_id === userId;
            const score = Number(r.avg_score || 0);
            const scoreColor = score >= 7 ? styles.badgeGreen : score >= 4 ? styles.badgeAmber : styles.badgeRed;
            const rowRankClass = r.rank === 1 ? styles.rank1 : r.rank === 2 ? styles.rank2 : r.rank === 3 ? styles.rank3 : "";
            const altClass = idx % 2 === 0 ? styles.altA : styles.altB;
            return (
              <tr key={r.user_id} className={[isMe ? styles.currentRow : "", rowRankClass, !isMe ? altClass : ""].filter(Boolean).join(" ")}>
                <td className={styles.cell}>{r.rank}</td>
                <td className={styles.cell}>{r.name}</td>
                <td className={styles.cell}>
                  <span className={[styles.scoreBadge, scoreColor].filter(Boolean).join(" ")}>{score.toFixed(2)}</span>
                </td>
                <td className={styles.cell}>{r.total_attempts}</td>
                <td className={styles.cell}>{r.strongest_topic || "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// Quick manual test:
// - Login -> open `/dashboard/leaderboard`.

