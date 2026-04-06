import React, { useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./ReviewPage.module.css";
import TopicBadge from "../components/TopicBadge.jsx";

function daysAgo(iso) {
  try {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    return Math.max(0, Math.floor(diff / (1000 * 60 * 60 * 24)));
  } catch {
    return 0;
  }
}

export default function ReviewPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [payload, setPayload] = useState(null);
  const [idx, setIdx] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [improveMsg, setImproveMsg] = useState("");

  const current = payload?.questions?.[idx] || null;

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!userId) return;
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/api/quiz/due-reviews/${encodeURIComponent(userId)}`);
        if (!mounted) return;
        setPayload(res.data);
        setIdx(0);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.message || "Failed to load review queue.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [userId]);

  const dueCount = payload?.due_count ?? 0;

  const meta = useMemo(() => {
    if (!current) return null;
    const prev = Number(current.previous_score || 0);
    const ago = daysAgo(current.attempted_at);
    return { prev, ago };
  }, [current]);

  const onSubmit = async () => {
    if (!current) return;
    if (answer.trim().length < 2) return;
    setSubmitLoading(true);
    setImproveMsg("");
    try {
      const res = await api.post("/api/quiz/submit", {
        question_id: current._id,
        student_answer: answer,
        language: "en",
      });
      const r = res.data;
      setResult(r);
      const prev = Number(current.previous_score || 0);
      const next = Number(r.final_score || 0);
      if (next > prev) setImproveMsg(`Improved! +${(next - prev).toFixed(0)} points`);
      else if (next < 7) setImproveMsg("Scheduled for review in 1 day");
    } catch (e) {
      setError(e?.response?.data?.message || "Submit failed.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const onNext = () => {
    setAnswer("");
    setResult(null);
    setImproveMsg("");
    setIdx((i) => i + 1);
  };

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.title}>Spaced Repetition Review</div>
        <div className={styles.sub}>Loading due questions…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.title}>Spaced Repetition Review</div>
        <div className={styles.banner}>
          <div className={styles.bannerTitle}>Couldn’t load review queue</div>
          <div className={styles.bannerSub}>{error}</div>
          <div className={styles.actions}>
            <button className={styles.secondaryBtn} type="button" onClick={() => navigate("/dashboard")}>
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className={styles.wrap}>
        <div className={styles.title}>Spaced Repetition Review</div>
        <div className={styles.done}>
          <div className={styles.bannerTitle}>Review Complete!</div>
          <div className={styles.bannerSub}>
            {dueCount ? "You reviewed all due questions." : "No questions are due right now."}
          </div>
          <div className={styles.actions}>
            <button className={styles.primaryBtn} type="button" onClick={() => navigate("/dashboard")}>
              Back to Dashboard →
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.title}>Spaced Repetition Review</div>
      <div className={styles.sub}>📅 Due for Review — lock it in before you forget.</div>

      <div className={styles.banner}>
        <div className={styles.bannerTitle}>
          You have {dueCount} questions due for review
        </div>
        <div className={styles.bannerSub}>
          These are topics where your memory is fading — review now to lock them in.
        </div>
      </div>

      <div className={styles.panel}>
        <div className={styles.metaRow}>
          <div>
            Previous score: <b>{meta?.prev ?? 0}/10</b> — <b>{meta?.ago ?? 0}</b> days ago
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <TopicBadge topic={current.difficulty || "easy"} variant="primary" />
            <TopicBadge topic={current.topic_tag || "General"} variant="primary" />
          </div>
        </div>

        <div className={styles.question}>{current.question_text}</div>

        <textarea
          className={styles.textarea}
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder="Type your answer..."
          disabled={submitLoading || Boolean(result)}
        />

        <div className={styles.actions}>
          {!result ? (
            <button className={styles.primaryBtn} type="button" onClick={onSubmit} disabled={submitLoading}>
              {submitLoading ? "Submitting..." : "Submit Answer"}
            </button>
          ) : (
            <button className={styles.primaryBtn} type="button" onClick={onNext}>
              Next →
            </button>
          )}
        </div>

        {result ? (
          <div className={styles.resultCard}>
            <div className={styles.resultTitle}>Result: {result.final_score}/10</div>
            <div>{improveMsg}</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

