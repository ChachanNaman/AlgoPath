import React, { useContext, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api.js";
import { AuthContext } from "../context/AuthContext.jsx";
import styles from "./KnowledgeGraphPage.module.css";

const COLORS = {
  mastered: "#4CAF82",
  learning: "#F5A623",
  weak: "#FF6B6B",
  untested: "#2A2E3E",
};

function strokeFor(fill) {
  return fill;
}

export default function KnowledgeGraphPage() {
  const { user } = useContext(AuthContext);
  const userId = user?.email;
  const navigate = useNavigate();

  const canvasRef = useRef(null);
  const [graph, setGraph] = useState(null);
  const [hover, setHover] = useState(null); // { node, x, y }

  const layout = useMemo(() => {
    if (!graph?.nodes?.length) return null;
    const levels = {};
    for (const n of graph.nodes) {
      const lvl = Number(n.level || 1);
      levels[lvl] = levels[lvl] || [];
      levels[lvl].push(n);
    }
    const xs = { 1: 100, 2: 280, 3: 460, 4: 640 };
    const out = {};
    for (const lvl of Object.keys(levels)) {
      const l = Number(lvl);
      const arr = levels[l];
      const count = arr.length;
      for (let i = 0; i < count; i++) {
        const y = 90 + (count === 1 ? 200 : (i * (420 / (count - 1))));
        out[arr[i].id] = { x: xs[l] || 100 + (l - 1) * 180, y };
      }
    }
    return out;
  }, [graph]);

  useEffect(() => {
    let mounted = true;
    async function load() {
      if (!userId) return;
      const res = await api.get(`/api/progress/knowledge-graph/${encodeURIComponent(userId)}`);
      if (!mounted) return;
      setGraph(res.data);
    }
    load().catch(() => {});
    return () => {
      mounted = false;
    };
  }, [userId]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graph || !layout) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = Math.floor(rect.width * dpr);
    canvas.height = Math.floor(rect.height * dpr);
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    ctx.clearRect(0, 0, w, h);

    // edges first
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255,255,255,0.15)";
    for (const e of graph.edges || []) {
      const a = layout[e.from];
      const b = layout[e.to];
      if (!a || !b) continue;
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    // nodes
    const radius = 38;
    for (const n of graph.nodes || []) {
      const p = layout[n.id];
      if (!p) continue;
      const status = n.status || "untested";
      const fill = COLORS[status] || COLORS.untested;

      const isHover = hover?.node?.id === n.id;
      const r = isHover ? radius + 3 : radius;

      // fill
      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.fill();

      // stroke
      ctx.lineWidth = isHover ? 3 : 2;
      ctx.strokeStyle = strokeFor(fill);
      ctx.stroke();

      // label
      ctx.fillStyle = "#fff";
      ctx.font = "600 11px Space Grotesk, system-ui, -apple-system, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      const label = String(n.label || n.id);
      ctx.fillText(label, p.x, p.y - 4);

      // score
      const scoreText = typeof n.score === "number" ? `${n.score.toFixed(1)}/10` : "—";
      ctx.fillStyle = "rgba(255,255,255,0.82)";
      ctx.font = "500 10px Space Grotesk, system-ui, -apple-system, sans-serif";
      ctx.fillText(scoreText, p.x, p.y + 14);
    }
  }, [graph, layout, hover]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !graph || !layout) return;

    const radius = 38;
    function toLocal(e) {
      const rect = canvas.getBoundingClientRect();
      return { x: e.clientX - rect.left, y: e.clientY - rect.top };
    }

    function onMove(e) {
      const { x, y } = toLocal(e);
      let found = null;
      for (const n of graph.nodes || []) {
        const p = layout[n.id];
        if (!p) continue;
        const dx = x - p.x;
        const dy = y - p.y;
        if (Math.sqrt(dx * dx + dy * dy) <= radius) {
          found = { node: n, x: e.clientX, y: e.clientY };
          break;
        }
      }
      setHover(found);
    }

    function onLeave() {
      setHover(null);
    }

    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);
    return () => {
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
    };
  }, [graph, layout]);

  return (
    <div className={styles.wrap}>
      <div className={styles.title}>Knowledge Map</div>
      <div className={styles.sub}>Your DAA learning path — hover any topic to see mastery.</div>

      <div className={styles.canvasCard}>
        <canvas ref={canvasRef} className={styles.canvas} />
        {hover?.node ? (
          <div
            className={styles.tip}
            style={{ left: Math.min(window.innerWidth - 320, hover.x + 12), top: Math.max(18, hover.y - 10) }}
          >
            <div className={styles.tipTitle}>{hover.node.label}</div>
            <div className={styles.tipRow}>
              Score: {typeof hover.node.score === "number" ? `${hover.node.score.toFixed(1)}/10` : "Not tested yet"}
            </div>
            <div className={styles.tipRow}>Status: {hover.node.status}</div>
            <div className={styles.tipActionHint}>Start Quiz on this topic → (coming in Review Queue)</div>
          </div>
        ) : null}
      </div>

      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: COLORS.mastered }} /> Mastered
        </span>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: COLORS.learning }} /> Learning
        </span>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: COLORS.weak }} /> Needs Work
        </span>
        <span className={styles.legendItem}>
          <span className={styles.dot} style={{ background: COLORS.untested }} /> Not Tested Yet
        </span>
      </div>
    </div>
  );
}

