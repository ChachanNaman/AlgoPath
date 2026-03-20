from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required


leaderboard_bp = Blueprint("leaderboard_bp", __name__)


@leaderboard_bp.get("")
@jwt_required()
def leaderboard():
    # Spec: GET /api/leaderboard protected; return top 10.
    _identity = get_jwt_identity()
    db = current_app.config["MONGO_DB"]
    users = db["users"]
    quiz_attempts = db["quiz_attempts"]

    users_docs = list(users.find({}))
    user_by_email = {u.get("email"): u for u in users_docs}
    if not user_by_email:
        return jsonify([]), 200

    attempts = list(quiz_attempts.find({}))

    # Group attempts by user_id.
    agg = {}
    topic_sum = {}
    topic_count = {}

    for a in attempts:
        uid = a.get("user_id")
        if not uid:
            continue
        final_score = float(a.get("final_score", 0) or 0)
        agg.setdefault(uid, {"sum": 0.0, "count": 0})
        agg[uid]["sum"] += final_score
        agg[uid]["count"] += 1

        topic = a.get("topic_tag") or "Unknown"
        topic_sum.setdefault(uid, {})
        topic_count.setdefault(uid, {})
        topic_sum[uid][topic] = topic_sum[uid].get(topic, 0.0) + final_score
        topic_count[uid][topic] = topic_count[uid].get(topic, 0) + 1

    rows = []
    for uid, v in agg.items():
        count = v["count"]
        if count <= 0:
            continue
        avg_score = v["sum"] / count

        # Strongest topic by avg.
        best_topic = None
        best_avg = -1.0
        for topic, s in topic_sum.get(uid, {}).items():
            c = topic_count.get(uid, {}).get(topic, 1)
            avg = s / max(1, c)
            if avg > best_avg:
                best_avg = avg
                best_topic = topic

        udoc = user_by_email.get(uid) or {}
        rows.append(
            {
                "user_id": uid,
                "name": udoc.get("name", uid),
                "avg_score": float(round(avg_score, 2)),
                "total_attempts": int(count),
                "strongest_topic": best_topic,
            }
        )

    rows.sort(key=lambda x: x["avg_score"], reverse=True)
    rows = rows[:10]

    for i, r in enumerate(rows, start=1):
        r["rank"] = i

    return jsonify(rows), 200


# Test:
# curl http://localhost:5000/api/leaderboard -H "Authorization: Bearer TOKEN_HERE"

