import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./AITutorPage.module.css";
import TopicBadge from "../components/TopicBadge.jsx";
import { formatTimestamp } from "../utils/formatTimestamp.js";

const LANGS = [
  { code: "en", label: "EN" },
  { code: "hi", label: "HI" },
  { code: "ta", label: "TA" },
  { code: "te", label: "TE" },
];

export default function AITutorPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;

  const [messages, setMessages] = useState([]); // {role, content}
  const [contextSources, setContextSources] = useState([]); // {video_title, start_time, end_time}
  const [typing, setTyping] = useState(false);

  const [language, setLanguage] = useState("en");
  const [input, setInput] = useState("");

  const chatEndRef = useRef(null);

  useEffect(() => {
    // Keep scrolled to bottom on new messages.
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, typing]);

  const conversationHistory = useMemo(() => {
    return messages.map((m) => ({ role: m.role, content: m.content }));
  }, [messages]);

  const onSend = async () => {
    const msg = input.trim();
    if (!msg || typing) return;

    setInput("");
    const nextUserMsg = { role: "user", content: msg };
    setMessages((prev) => [...prev, nextUserMsg]);
    setTyping(true);

    try {
      const res = await api.post("/api/ai_tutor/chat", {
        message: msg,
        conversation_history: conversationHistory,
        language,
      });
      const assistantText = res.data?.response || "";
      const ctx = res.data?.context_chunks || [];
      setContextSources(ctx);
      setMessages((prev) => [...prev, { role: "assistant", content: assistantText }]);
    } catch (e) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: e?.response?.data?.message || "Tutor request failed." },
      ]);
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className={styles.wrap}>
      <div className={styles.leftPanel}>
        <div className={styles.leftTitle}>Context Sources</div>
        {contextSources.length ? (
          <div className={styles.contextList}>
            {contextSources.map((c, idx) => (
              <div key={`${c.video_title}-${c.start_time}-${idx}`} className={styles.contextItem}>
                <div className={styles.contextVideo}>{c.video_title || "Lecture"}</div>
                <div className={styles.contextTime}>
                  {formatTimestamp(Number(c.start_time || 0))} – {formatTimestamp(Number(c.end_time || 0))}
                </div>
                <TopicBadge topic="Context" variant="primary" />
              </div>
            ))}
          </div>
        ) : (
          <div className={styles.noContext}>
            No context yet. Submit at least one quiz answer to power the Tutor.
          </div>
        )}
      </div>

      <div className={styles.rightPanel}>
        <div className={styles.chatArea}>
          {messages.map((m, idx) => (
            <div
              key={`${m.role}-${idx}`}
              className={m.role === "user" ? styles.msgUser : styles.msgAi}
            >
              {m.content}
            </div>
          ))}

          {typing ? (
            <div className={styles.typingRow}>
              <div className={styles.typingDots} aria-label="Typing">
                <span className={styles.dot} />
                <span className={styles.dot} />
                <span className={styles.dot} />
              </div>
            </div>
          ) : null}
          <div ref={chatEndRef} />
        </div>

        <div className={styles.inputBar}>
          <div className={styles.langRow}>
            {LANGS.map((l) => (
              <button
                key={l.code}
                type="button"
                className={[styles.langBtn, language === l.code ? styles.langActive : ""].filter(Boolean).join(" ")}
                onClick={() => setLanguage(l.code)}
              >
                {l.label}
              </button>
            ))}
          </div>

          <div className={styles.composeRow}>
            <textarea
              className={styles.textarea}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about DAA..."
              rows={1}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSend();
                }
              }}
              style={{ maxHeight: 140 }}
            />
            <button className={styles.sendBtn} type="button" onClick={onSend} disabled={typing || !input.trim()}>
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Quick manual test:
// - Go to `/dashboard/tutor`, ask a question, verify response + context panel updates.

