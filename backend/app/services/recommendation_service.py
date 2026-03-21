from __future__ import annotations

from datetime import datetime

from app.services.transcript_service import infer_topic_tag

# When transcript timestamps are missing, avoid useless 0:00 jumps.
_DEFAULT_LECTURE_JUMP_SECONDS = 48.0

# Show more weak areas and prefer topics you practiced recently (ties / near-ties).
_MAX_WEAK_TOPICS = 12


def _effective_topic_tag(attempt: dict, videos_by_id: dict[str, dict]) -> str:
    """
    Quiz rows often store topic_tag='General' when questions were generated from title-only chunks.
    Re-label using the playlist video title so Weak Topics / Timeline / radar stay accurate.
    """
    t = (attempt.get("topic_tag") or "Unknown").strip() or "Unknown"
    if t not in ("General", "Unknown", ""):
        return t
    vid = attempt.get("video_id") or ""
    title = (videos_by_id.get(vid) or {}).get("title", "") or ""
    inferred = infer_topic_tag(title)
    if inferred and inferred not in ("General",):
        return inferred
    return t


def compute_recommendations(user_id: str, db) -> list[dict]:
    """
    Spec:
      1) Fetch all quiz_attempts for user
      2) Group by topic_tag, compute mean final_score
      3) Sort ascending by avg_score
      4) For top weak topics:
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
        recommendations.update_one(
            {"user_id": user_id},
            {"$set": {"weak_topics": [], "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return []

    vids = list({a.get("video_id") for a in attempts if a.get("video_id")})
    vdocs = list(videos.find({"video_id": {"$in": vids}})) if vids else []
    videos_by_id = {v["video_id"]: v for v in vdocs}

    topic_sum: dict[str, float] = {}
    topic_count: dict[str, int] = {}
    topic_latest: dict[str, datetime] = {}

    for a in attempts:
        t = _effective_topic_tag(a, videos_by_id)
        final = float(a.get("final_score", 0) or 0)
        topic_sum[t] = topic_sum.get(t, 0.0) + final
        topic_count[t] = topic_count.get(t, 0) + 1
        at = a.get("attempted_at")
        if isinstance(at, datetime):
            prev = topic_latest.get(t)
            if prev is None or at > prev:
                topic_latest[t] = at

    avg_by_topic: list[tuple[str, float, float]] = []
    for t in topic_sum.keys():
        avg = topic_sum[t] / max(1, topic_count[t])
        latest_ts = topic_latest.get(t, datetime.min).timestamp()
        avg_by_topic.append((t, avg, latest_ts))

    # Weakest first; when averages are close, prefer the topic you touched most recently.
    avg_by_topic.sort(key=lambda row: (row[1], -row[2]))

    weak_topics_payload: list[dict] = []
    for topic, avg_score, _ in avg_by_topic[:_MAX_WEAK_TOPICS]:
        topic_attempts = [
            a for a in attempts if _effective_topic_tag(a, videos_by_id) == topic
        ]
        topic_attempts.sort(key=lambda a: float(a.get("final_score", 0)))

        preferred_video_id = None
        preferred_timestamp = 0.0
        for a in topic_attempts:
            ts = float(a.get("timestamp_start", 0.0) or 0.0)
            if ts > 0:
                preferred_video_id = a.get("video_id")
                preferred_timestamp = ts
                break

        q = None
        if preferred_video_id:
            q = questions.find_one(
                {"topic_tag": topic, "video_id": preferred_video_id, "timestamp_start": {"$gt": 0}},
                sort=[("timestamp_start", 1)],
            )

        if not q:
            q = questions.find_one({"topic_tag": topic, "timestamp_start": {"$gt": 0}}, sort=[("timestamp_start", 1)])
        if not q:
            q = questions.find_one({"topic_tag": topic}, sort=[("timestamp_start", 1)])

        # Title-inferred topics won't match stored question.topic_tag (still "General"); widen search.
        if not q and topic_attempts:
            vid0 = topic_attempts[0].get("video_id")
            if vid0:
                q = questions.find_one(
                    {"video_id": vid0},
                    sort=[("timestamp_start", 1)],
                )

        if not q:
            continue

        final_video_id = preferred_video_id or q.get("video_id")
        raw_ts = preferred_timestamp or float(q.get("timestamp_start", 0.0) or 0.0)
        if raw_ts <= 0:
            raw_ts = _DEFAULT_LECTURE_JUMP_SECONDS

        vdoc = videos.find_one({"video_id": final_video_id})
        weak_topics_payload.append(
            {
                "topic": topic,
                "avg_score": float(round(avg_score, 2)),
                "recommended_video_id": final_video_id,
                "recommended_timestamp": raw_ts,
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
