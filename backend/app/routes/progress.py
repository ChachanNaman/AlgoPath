from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required


progress_bp = Blueprint("progress_bp", __name__)


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

    # Overall + topic aggregates
    topic_sum: dict[str, float] = {}
    topic_count: dict[str, int] = {}
    total_sum = 0.0
    for a in attempts:
        final = float(a.get("final_score", 0) or 0)
        total_sum += final
        t = a.get("topic_tag") or "Unknown"
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
            }
        ),
        200,
    )


# Test:
# curl http://localhost:5000/api/progress/arjun@test.com -H "Authorization: Bearer TOKEN_HERE"

