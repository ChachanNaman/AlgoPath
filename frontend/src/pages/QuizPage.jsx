import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../services/api.js";
import styles from "./QuizPage.module.css";
import TopicBadge from "../components/TopicBadge.jsx";
import useYouTubePlayer from "../hooks/useYouTubePlayer.js";

const LANGS = [
  { code: "en", label: "EN" },
  { code: "hi", label: "HI" },
  { code: "ta", label: "TA" },
  { code: "te", label: "TE" },
];

function ScoreCircle({ score }) {
  const pct = Math.max(0, Math.min(10, score)) / 10;
  const fillDeg = Math.round(pct * 360);
  const strokeColor = score >= 7 ? "#4CAF82" : score >= 4 ? "#F5A623" : "#FF6B6B";
  return (
    <div
      className={styles.scoreCircle}
      style={{
        background: `conic-gradient(${strokeColor} 0 ${fillDeg}deg, rgba(255,255,255,0.12) ${fillDeg}deg 360deg)`,
      }}
    >
      <div className={styles.scoreInner}>{score}/10</div>
    </div>
  );
}

export default function QuizPage() {
  const { video_id } = useParams();
  const navigate = useNavigate();

  const { seekTo, isReady } = useYouTubePlayer("yt-player", video_id);

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [submitLoading, setSubmitLoading] = useState(false);

  const [language, setLanguage] = useState("en");
  const [translated, setTranslated] = useState(null);
  const [translationLoading, setTranslationLoading] = useState(false);
  const [translationError, setTranslationError] = useState("");
  const [showOriginal, setShowOriginal] = useState(false);

  const [results, setResults] = useState([]); // per-question result list
  const [showPlayerFallback, setShowPlayerFallback] = useState(false);

  const current = questions[index] || null;
  const totalQuestions = Math.max(1, questions.length);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get(`/api/quiz/questions/${video_id}`, { params: { count: 5 } });
        if (!mounted) return;
        setQuestions(res.data || []);
      } catch (e) {
        if (!mounted) return;
        setError(e?.response?.data?.message || "Failed to load quiz questions.");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => {
      mounted = false;
    };
  }, [video_id]);

  useEffect(() => {
    // Fetch translated question whenever user changes language or question changes.
    let mounted = true;
    async function loadTranslation() {
      setTranslated(null);
      setTranslationError("");
      setTranslationLoading(false);
      setShowOriginal(false);
      if (!current) return;
      if (language === "en") return;
      try {
        setTranslationLoading(true);
        const res = await api.post("/api/quiz/translate", {
          question_id: current.question_id,
          target_language: language,
        });
        if (!mounted) return;
        setTranslated(res.data);
      } catch {
        if (!mounted) return;
        // Keep original if translation fails.
        setTranslated(null);
        setTranslationError("Translation unavailable right now. Showing original question.");
      } finally {
        if (mounted) setTranslationLoading(false);
      }
    }
    loadTranslation();
    return () => {
      mounted = false;
    };
  }, [language, current?.question_id]);

  useEffect(() => {
    // Fallback to plain iframe if YouTube IFrame API player never becomes ready.
    setShowPlayerFallback(false);
    const timer = window.setTimeout(() => {
      if (!isReady) setShowPlayerFallback(true);
    }, 5000);
    return () => window.clearTimeout(timer);
  }, [video_id, isReady]);

  const questionTextToRender = useMemo(() => {
    if (!current) return "";
    if (language === "en" || !translated?.translated_question) return current.question_text;
    return translated.translated_question;
  }, [current, language, translated]);

  const alreadyAnswered = Boolean(results[index]);

  const onSubmit = async () => {
    if (!current) return;
    if (answer.trim().length < 2) return;

    setSubmitLoading(true);
    try {
      const res = await api.post("/api/quiz/submit", {
        question_id: current.question_id,
        student_answer: answer,
        language,
      });
      const r = res.data;
      setResults((prev) => {
        const next = [...prev];
        next[index] = r;
        return next;
      });
    } catch (e) {
      setError(e?.response?.data?.message || "Submit failed. Try again.");
    } finally {
      setSubmitLoading(false);
    }
  };

  const onNext = () => {
    setAnswer("");
    setTranslated(null);
    setShowOriginal(false);
    setIndex((i) => Math.min(i + 1, totalQuestions - 1));
  };

  const isComplete = results.filter(Boolean).length >= totalQuestions;

  const overallScore = useMemo(() => {
    if (!results.length) return 0;
    const vals = results.filter(Boolean).map((r) => r.final_score);
    if (!vals.length) return 0;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  }, [results]);

  const weakestConcept = useMemo(() => {
    const vals = results.filter(Boolean);
    if (!vals.length) return null;
    vals.sort((a, b) => a.final_score - b.final_score);
    return vals[0]?.weak_concept || null;
  }, [results]);

  const score = results[index]?.final_score ?? null;

  if (loading) {
    return (
      <div className={styles.wrap}>
        <div className={styles.playerSkeleton} />
        <div className={styles.quizPanel}>
          <div className={styles.panelHeader}>Loading quiz...</div>
          <div className={styles.panelBody} />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.wrap}>
        <div className={styles.errorCard}>
          <div className={styles.errorMsg}>{error}</div>
          <button className={styles.retryBtn} type="button" onClick={() => navigate("/dashboard/playlist")}>
            Try Again
          </button>
        </div>
      </div>
    );
  }

  if (!questions.length) {
    return (
      <div className={styles.wrap}>
        <div className={styles.emptyCard}>
          No questions available for this video yet. Try ingesting the playlist.
        </div>
      </div>
    );
  }

  if (isComplete) {
    return (
      <div className={styles.wrap}>
        <div className={styles.completeCard}>
          <div className={styles.completeTitle}>Quiz Complete</div>
          <div className={styles.completeScore}>
            <span className={styles.completeScoreValue}>{overallScore.toFixed(1)}</span> / 10
          </div>
          <div className={styles.completeSub}>
            Weakest concept: <span className={styles.weakest}>{weakestConcept || "—"}</span>
          </div>
          <button className={styles.primaryBtn} type="button" onClick={() => navigate("/dashboard/timeline")}>
            Go to Timeline →
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.wrap}>
      <div className={styles.playerWrap}>
        <div className={styles.playerOuter}>
          {showPlayerFallback ? (
            <iframe
              className={styles.playerInner}
              src={`https://www.youtube.com/embed/${video_id}?rel=0&modestbranding=1`}
              title="Lecture video"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerPolicy="strict-origin-when-cross-origin"
              allowFullScreen
            />
          ) : (
            <div id="yt-player" className={styles.playerInner} />
          )}
        </div>
      </div>

      <div className={styles.quizPanel}>
        <div className={styles.panelTop}>
          <div className={styles.qHeader}>
            Question {Math.min(index + 1, totalQuestions)} of {totalQuestions}
            <div className={styles.badgesRow}>
              <TopicBadge topic={current.difficulty} variant="primary" />
              <TopicBadge topic={current.topic_tag} variant="primary" />
            </div>
          </div>

          <div className={styles.langToggle}>
            {LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                className={[styles.langBtn, language === l.code ? styles.langActive : ""].filter(Boolean).join(" ")}
                onClick={() => setLanguage(l.code)}
                disabled={translationLoading}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.questionText}>{current ? questionTextToRender : "All loaded questions are completed."}</div>
        {translationLoading ? <div className={styles.translateHint}>Translating question...</div> : null}
        {translationError ? <div className={styles.translateError}>{translationError}</div> : null}

        {language !== "en" && translated?.translated_question ? (
          <div className={styles.originalToggle}>
            <button className={styles.secondaryBtn} type="button" onClick={() => setShowOriginal((s) => !s)}>
              {showOriginal ? "Hide original" : "Show original"}
            </button>
            {showOriginal ? <div className={styles.originalText}>{current.question_text}</div> : null}
          </div>
        ) : null}

        <div className={styles.answerBlock}>
          <textarea
            className={styles.textarea}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer..."
            disabled={submitLoading || alreadyAnswered}
          />
        </div>

        <div className={styles.actionsRow}>
          {!alreadyAnswered ? (
            <button className={styles.primaryBtn} type="button" onClick={onSubmit} disabled={submitLoading}>
              {submitLoading ? "Submitting..." : "Submit Answer"}
            </button>
          ) : (
            <button className={styles.nextBtn} type="button" onClick={onNext}>
              Next Question →
            </button>
          )}
        </div>

        {alreadyAnswered ? (
          <div className={styles.resultBlock}>
            <ScoreCircle score={score} />
            <div className={styles.feedbackCol}>
              <div className={styles.feedbackLabel}>Feedback</div>
              <div className={styles.feedbackText}>{results[index].feedback}</div>
            </div>
            <div className={styles.answerSection}>
              <div className={styles.answerCard}>
                <div className={styles.answerCardLabel}>Model answer</div>
                <p className={styles.answerCardBody}>{results[index].correct_answer}</p>
              </div>
              {results[index].explanation ? (
                <div className={styles.explanationCard}>
                  <div className={styles.answerCardLabel}>Explanation</div>
                  <p className={styles.explanationBody}>{results[index].explanation}</p>
                </div>
              ) : null}
              <div className={styles.resultActions}>
                <button
                  className={styles.secondaryBtn}
                  type="button"
                  onClick={() => {
                    const ts = Number(results[index].recommended_timestamp || 0);
                    if (typeof seekTo === "function" && isReady) {
                      seekTo(ts);
                    } else if (video_id) {
                      window.open(
                        `https://www.youtube.com/watch?v=${video_id}&t=${Math.floor(ts)}`,
                        "_blank",
                        "noopener,noreferrer"
                      );
                    }
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  Jump to concept in video
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

// Quick manual test:
// - Open playlist, ingest, open a processed video quiz.
// - Answer 5 questions and verify scoring feedback + jump-to-timestamp.

