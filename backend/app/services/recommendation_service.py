from __future__ import annotations

from datetime import datetime


def compute_recommendations(user_id: str, db) -> list[dict]:
    """
    Spec:
      1) Fetch all quiz_attempts for user
      2) Group by topic_tag, compute mean final_score
      3) Sort ascending by avg_score (weakest first)
      4) For top 5 weak topics:
         - Query questions collection: find earliest timestamp_start for that topic
         - Fetch video title for the selected question's video_id
      5) Upsert into recommendations collection
    """
    quiz_attempts = db["quiz_attempts"]
    questions = db["questions"]
    videos = db["videos"]
    recommendations = db["recommendations"]

    attempts = list(quiz_attempts.find({"user_id": user_id}))
    if not attempts:
        # Upsert empty recommendations so UI can render empty state.
        recommendations.update_one(
            {"user_id": user_id},
            {"$set": {"weak_topics": [], "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return []

    topic_sum: dict[str, float] = {}
    topic_count: dict[str, int] = {}
    for a in attempts:
        t = a.get("topic_tag") or "Unknown"
        topic_sum[t] = topic_sum.get(t, 0.0) + float(a.get("final_score", 0))
        topic_count[t] = topic_count.get(t, 0) + 1

    avg_by_topic = [(t, topic_sum[t] / max(1, topic_count[t])) for t in topic_sum.keys()]
    avg_by_topic.sort(key=lambda x: x[1])

    weak_topics_payload: list[dict] = []
    for topic, avg_score in avg_by_topic[:5]:
        # earliest timestamp question for that topic
        q = questions.find_one({"topic_tag": topic}, sort=[("timestamp_start", 1)])
        if not q:
            continue
        vdoc = videos.find_one({"video_id": q.get("video_id")})
        weak_topics_payload.append(
            {
                "topic": topic,
                "avg_score": float(round(avg_score, 2)),
                "recommended_video_id": q.get("video_id"),
                "recommended_timestamp": float(q.get("timestamp_start", 0.0)),
                "video_title": (vdoc or {}).get("title", ""),
            }
        )

    recommendations.update_one(
        {"user_id": user_id},
        {"$set": {"weak_topics": weak_topics_payload, "updated_at": datetime.utcnow()}},
        upsert=True,
    )

    return weak_topics_payload


# Quick test (manual):
# - Seed demo data (`python seed.py`)
# - Compute with:
#   from app.services.recommendation_service import compute_recommendations
#   compute_recommendations("arjun@test.com", db)

