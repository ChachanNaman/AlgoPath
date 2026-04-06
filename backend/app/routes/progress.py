from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.services.transcript_service import infer_topic_tag


progress_bp = Blueprint("progress_bp", __name__)


@progress_bp.get("/knowledge-graph/<user_id>")
@jwt_required()
def get_knowledge_graph(user_id: str):
    identity = get_jwt_identity()
    if str(identity) != str(user_id):
        return jsonify({"message": "forbidden"}), 403

    db = current_app.config["MONGO_DB"]
    quiz_attempts = db["quiz_attempts"]

    # Hardcoded DAA topic graph (nodes + edges)
    nodes = [
        {"id": "arrays", "label": "Arrays & Basics", "level": 1},
        {"id": "recursion", "label": "Recursion", "level": 1},
        {"id": "sorting", "label": "Sorting", "level": 2},
        {"id": "divide_conquer", "label": "Divide & Conquer", "level": 2},
        {"id": "hashing", "label": "Hashing", "level": 2},
        {"id": "trees", "label": "Trees", "level": 2},
        {"id": "graphs", "label": "Graphs", "level": 3},
        {"id": "dp", "label": "Dynamic Programming", "level": 3},
        {"id": "greedy", "label": "Greedy", "level": 3},
        {"id": "backtracking", "label": "Backtracking", "level": 3},
        {"id": "np", "label": "NP Completeness", "level": 4},
    ]
    edges = [
        {"from": "arrays", "to": "sorting"},
        {"from": "arrays", "to": "hashing"},
        {"from": "recursion", "to": "divide_conquer"},
        {"from": "recursion", "to": "backtracking"},
        {"from": "recursion", "to": "trees"},
        {"from": "divide_conquer", "to": "sorting"},
        {"from": "trees", "to": "graphs"},
        {"from": "graphs", "to": "dp"},
        {"from": "arrays", "to": "dp"},
        {"from": "greedy", "to": "np"},
        {"from": "dp", "to": "np"},
        {"from": "backtracking", "to": "np"},
    ]

    # Get user's scores per topic
    attempts = list(quiz_attempts.find({"user_id": user_id}))
    topic_scores: dict[str, float] = {}
    topic_counts: dict[str, int] = {}

    def _norm_topic(t: str) -> str:
        t = (t or "").lower().replace("&", "and")
        t = re.sub(r"[^a-z0-9]+", "_", t)
        t = re.sub(r"_+", "_", t).strip("_")
        return t

    for a in attempts:
        raw = a.get("topic_tag", "") or ""
        t = _norm_topic(raw)
        # fuzzy match to node IDs
        for node in nodes:
            nid = node["id"]
            if nid in t or t in nid:
                topic_scores[nid] = topic_scores.get(nid, 0.0) + float(a.get("final_score", 0) or 0)
                topic_counts[nid] = topic_counts.get(nid, 0) + 1

    for node in nodes:
        nid = node["id"]
        if topic_counts.get(nid, 0) > 0:
            avg = topic_scores[nid] / topic_counts[nid]
            node["score"] = round(avg, 1)
            node["status"] = "mastered" if avg >= 7 else "learning" if avg >= 4 else "weak"
        else:
            node["score"] = None
            node["status"] = "untested"

    return jsonify({"nodes": nodes, "edges": edges}), 200


def _effective_topic_for_attempt(attempt: dict, videos_by_id: dict) -> str:
    t = (attempt.get("topic_tag") or "Unknown").strip() or "Unknown"
    if t not in ("General", "Unknown", ""):
        return t
    vid = attempt.get("video_id") or ""
    title = (videos_by_id.get(vid) or {}).get("title", "") or ""
    inferred = infer_topic_tag(title)
    if inferred and inferred not in ("General",):
        return inferred
    return t


def _to_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value)).date()
    except Exception:
        return None


@progress_bp.get("/<user_id>")
@jwt_required()
def get_progress(user_id: str):
    identity = get_jwt_identity()
    if str(identity) != str(user_id):
        return jsonify({"message": "forbidden"}), 403

    db = current_app.config["MONGO_DB"]
    users = db["users"]
    quiz_attempts = db["quiz_attempts"]
    videos = db["videos"]

    user_doc = users.find_one({"email": user_id}) or {}
    streak_days = int(user_doc.get("streak_days", 0) or 0)

    attempts = list(quiz_attempts.find({"user_id": user_id}))
    if not attempts:
        # Return a stable shape for frontend.
        today = date.today()
        daily_scores = []
        for i in range(14):
            d = today - timedelta(days=(13 - i))
            daily_scores.append({"date": d.isoformat(), "avg_score": 0.0})

        return (
            jsonify(
                {
                    "overall_avg_score": 0.0,
                    "topic_scores": {},
                    "total_questions_attempted": 0,
                    "streak_days": streak_days,
                    "strongest_topic": None,
                    "weakest_topic": None,
                    "daily_scores": daily_scores,
                }
            ),
            200,
        )

    vids = list({a.get("video_id") for a in attempts if a.get("video_id")})
    vdocs = list(videos.find({"video_id": {"$in": vids}})) if vids else []
    videos_by_id = {v["video_id"]: v for v in vdocs}

    # Overall + topic aggregates (re-label General using video title for radar / analytics)
    topic_sum: dict[str, float] = {}
    topic_count: dict[str, int] = {}
    total_sum = 0.0
    for a in attempts:
        final = float(a.get("final_score", 0) or 0)
        total_sum += final
        t = _effective_topic_for_attempt(a, videos_by_id)
        topic_sum[t] = topic_sum.get(t, 0.0) + final
        topic_count[t] = topic_count.get(t, 0) + 1

    overall_avg = round(total_sum / max(1, len(attempts)), 1)
    topic_scores = {t: round(topic_sum[t] / max(1, topic_count[t]), 2) for t in topic_sum}

    strongest_topic = max(topic_scores.items(), key=lambda x: x[1])[0] if topic_scores else None
    weakest_topic = min(topic_scores.items(), key=lambda x: x[1])[0] if topic_scores else None

    # Daily scores for last 14 days
    today = date.today()
    start_day = today - timedelta(days=13)
    daily_scores = []
    for i in range(14):
        d = start_day + timedelta(days=i)
        day_attempts = [a for a in attempts if _to_date(a.get("attempted_at")) == d]
        if not day_attempts:
            daily_scores.append({"date": d.isoformat(), "avg_score": 0.0})
            continue
        avg = sum(float(a.get("final_score", 0) or 0) for a in day_attempts) / len(day_attempts)
        daily_scores.append({"date": d.isoformat(), "avg_score": float(round(avg, 2))})

    # Achievement badges
    total_attempts = len(attempts)
    badges = []
    if total_attempts >= 1:
        badges.append({"id": "first_quiz", "label": "First Step", "icon": "🎯", "desc": "Completed your first quiz"})
    if total_attempts >= 10:
        badges.append({"id": "ten_quizzes", "label": "Getting Serious", "icon": "📚", "desc": "Completed 10 quizzes"})
    if overall_avg >= 7:
        badges.append({"id": "high_scorer", "label": "High Achiever", "icon": "⭐", "desc": "Average score above 7"})
    if streak_days >= 3:
        badges.append({"id": "streak_3", "label": "On Fire", "icon": "🔥", "desc": "3-day study streak"})
    if streak_days >= 7:
        badges.append({"id": "streak_7", "label": "Unstoppable", "icon": "⚡", "desc": "7-day study streak"})
    for topic, score in topic_scores.items():
        try:
            if float(score) >= 8:
                badges.append({"id": f"master_{topic}", "label": f"{topic} Master", "icon": "🏆", "desc": f"Mastered {topic}"})
                break
        except Exception:
            continue

    return (
        jsonify(
            {
                "overall_avg_score": overall_avg,
                "topic_scores": topic_scores,
                "total_questions_attempted": len(attempts),
                "streak_days": streak_days,
                "strongest_topic": strongest_topic,
                "weakest_topic": weakest_topic,
                "daily_scores": daily_scores,
                "badges": badges,
            }
        ),
        200,
    )


# Test:
# curl http://localhost:5000/api/progress/arjun@test.com -H "Authorization: Bearer TOKEN_HERE"

