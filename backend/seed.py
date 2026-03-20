"""
Run with:
  python seed.py

Creates demo data so the app looks good immediately.

If your MongoDB is empty, this script will insert:
- test users
- sample videos
- transcript chunks (with placeholder embeddings)
- questions (15)
- quiz attempts (20) for `arjun@test.com` with topic-weakness profile
- recommendations derived from seeded attempts
"""

from __future__ import annotations

from datetime import datetime, timedelta

import bcrypt
import numpy as np

from app import create_app


# Abdul Bari DAA playlist (from your provided link).
DEFAULT_PLAYLIST_ID = "PLDN4rrl48XKpZkf03iYFl-O29szjTrs_O"

test_users = [
    {"name": "Arjun Sharma", "email": "arjun@test.com", "password": "test123"},
    {"name": "Priya Nair", "email": "priya@test.com", "password": "test123"},
    {"name": "Rahul Singh", "email": "rahul@test.com", "password": "test123"},
]

sample_videos = [
    {
        "video_id": "0IAPZzGSbME",
        "title": "Introduction to Algorithms",
        "topics": ["Introduction", "Complexity"],
        "processed": True,
    },
    {
        "video_id": "p1EnSvS3urU",
        "title": "Divide and Conquer",
        "topics": ["Divide & Conquer"],
        "processed": True,
    },
    {
        "video_id": "4VqmGXwpLqc",
        "title": "Merge Sort",
        "topics": ["Sorting", "Merge Sort"],
        "processed": True,
    },
    {
        "video_id": "7h1s2SojIRw",
        "title": "Quick Sort",
        "topics": ["Sorting", "Quick Sort"],
        "processed": True,
    },
    {
        "video_id": "ncl9Lk9QGRM",
        "title": "Dynamic Programming Introduction",
        "topics": ["Dynamic Programming"],
        "processed": True,
    },
]


EMBED_DIM = 384  # all-MiniLM-L6-v2 output size


def make_embedding(seed_value: int) -> list[float]:
    rng = np.random.default_rng(seed_value)
    v = rng.normal(size=(EMBED_DIM,)).astype(np.float32)
    norm = float(np.linalg.norm(v)) or 1.0
    v = v / norm
    return v.tolist()


def main() -> None:
    app = create_app()
    db = app.config["MONGO_DB"]

    users = db["users"]
    videos = db["videos"]
    transcripts = db["transcripts"]
    questions = db["questions"]
    quiz_attempts = db["quiz_attempts"]
    recommendations = db["recommendations"]

    # 1) Users
    for u in test_users:
        existing = users.find_one({"email": u["email"]})
        if existing:
            continue
        salt = bcrypt.gensalt(rounds=12)
        password_hash = bcrypt.hashpw(u["password"].encode("utf-8"), salt)
        now = datetime.utcnow()
        users.insert_one(
            {
                "name": u["name"],
                "email": u["email"],
                "password_hash": password_hash,
                "created_at": now,
                "language_pref": "en",
                "streak_days": 5,
                "last_active": datetime.utcnow().date(),
            }
        )

    arjun = users.find_one({"email": "arjun@test.com"})
    if not arjun:
        raise RuntimeError("Seed failed: arjun@test.com user not found after insertion.")
    arjun_id = str(arjun["_id"])

    # 2) Videos
    for v in sample_videos:
        exists = videos.find_one({"video_id": v["video_id"]})
        if exists:
            continue
        videos.insert_one(
            {
                "video_id": v["video_id"],
                "title": v["title"],
                "playlist_id": DEFAULT_PLAYLIST_ID,
                "thumbnail_url": "",
                "duration_seconds": 3600,
                "topics": v["topics"],
                "processed": bool(v.get("processed", False)),
                "processing_error": None,
                "created_at": datetime.utcnow(),
            }
        )

    # 3) Transcript chunks (placeholder)
    # We'll create 3 chunks per topic per matching video, to support later RAG selection.
    chunk_text_template = (
        "Lecture excerpt about {topic}. Key ideas, recurrence/tables, and algorithm reasoning."
    )
    topic_to_videos: dict[str, dict] = {}
    for v in sample_videos:
        for t in v["topics"]:
            topic_to_videos.setdefault(t, v)

    # For each sample topic, attach chunks to the first video that claims it.
    transcript_topic_pages = [
        "Sorting",
        "Greedy",
        "Graphs",
        "Dynamic Programming",
        "Divide & Conquer",
    ]

    for t in transcript_topic_pages:
        v = topic_to_videos.get(t)
        if not v:
            continue
        video_id = v["video_id"]

        # Upsert transcript doc
        existing = transcripts.find_one({"video_id": video_id})
        if existing and existing.get("chunks"):
            continue

        chunks = []
        base_start = 60.0
        for ci in range(3):
            start_time = base_start + ci * 100.0
            end_time = start_time + 90.0
            chunks.append(
                {
                    "text": chunk_text_template.format(topic=t),
                    "start_time": start_time,
                    "end_time": end_time,
                    "topic_tag": t,
                    "chunk_index": ci,
                    "embedding": make_embedding(hash((video_id, t, ci)) % (2**31)),
                }
            )

        transcripts.insert_one({"video_id": video_id, "chunks": chunks})

    # 4) Questions (15)
    question_seed_template = [
        # topic, difficulty, correct_answer
        ("Sorting", "easy", "O(n log n)"),
        ("Sorting", "medium", "T(n) = 2T(n/2) + O(n)"),
        ("Sorting", "hard", "Merge sort is stable and uses O(n) extra space, but avoids worst-case O(n^2)."),
        ("Greedy", "easy", "Greedy choice property + optimal substructure are required."),
        ("Greedy", "medium", "A typical greedy algorithm sorts/chooses locally optimal options."),
        ("Greedy", "hard", "Greedy algorithms fail if the greedy-choice property does not hold."),
        ("Graphs", "easy", "DFS explores depth-first; BFS explores breadth-first."),
        ("Graphs", "medium", "Dijkstra requires non-negative edge weights."),
        ("Graphs", "hard", "In the worst case, Dijkstra runs in O((V+E) log V) with a heap."),
        ("Dynamic Programming", "easy", "DP uses overlapping subproblems and optimal substructure."),
        ("Dynamic Programming", "medium", "Bottom-up tabulation iterates from smaller to larger."),
        ("Dynamic Programming", "hard", "Recurrence relations derive the complexity and transition structure."),
        ("Divide & Conquer", "easy", "Divide & conquer splits into subproblems and combines results."),
        ("Divide & Conquer", "medium", "Master theorem solves recurrences like T(n)=aT(n/b)+f(n)."),
        ("Divide & Conquer", "hard", "Complexity depends on compare between f(n) and n^{log_b(a)}."),
    ]

    # Insert questions only if they don't already exist for a video/topic combination.
    # We will map each topic to a video from sample_videos.
    topic_to_video = {
        "Sorting": "4VqmGXwpLqc",  # default to Merge Sort
        "Greedy": "0IAPZzGSbME",  # fallback to intro
        "Graphs": "0IAPZzGSbME",
        "Dynamic Programming": "ncl9Lk9QGRM",
        "Divide & Conquer": "p1EnSvS3urU",
    }

    now = datetime.utcnow()
    inserted_questions = []
    for idx, (topic, difficulty, correct_answer) in enumerate(question_seed_template):
        video_id = topic_to_video.get(topic)
        if not video_id:
            continue

        existing = questions.find_one(
            {"video_id": video_id, "topic_tag": topic, "question_text": {"$regex": str(topic)}}
        )
        # If any matching question exists, skip to keep idempotency.
        if existing:
            continue

        timestamp_start = 60.0 + (idx % 3) * 100.0
        question_text = f"[{difficulty}] Explain {topic} concept with respect to time complexity and correctness."

        q_id = questions.insert_one(
            {
                "video_id": video_id,
                "chunk_index": idx % 3,
                "question_text": question_text,
                "correct_answer": correct_answer,
                "explanation": "This answer summarizes the expected algorithmic idea and its time complexity reasoning.",
                "difficulty": difficulty,
                "topic_tag": topic,
                "timestamp_start": timestamp_start,
                "language": "en",
                "embedding": make_embedding(hash((video_id, idx)) % (2**31)),
            }
        )
        inserted_questions.append(str(q_id.inserted_id))

    # 5) Quiz attempts (20) for arjun with realistic weakness profile
    # Target averages:
    # Sorting avg=3.2, Greedy avg=4.1, Graphs avg=7.8, DP avg=5.5, D&C avg=6.0
    attempts_plan = [
        ("Sorting", [2, 3, 3, 4]),
        ("Greedy", [3, 4, 4, 5]),
        ("Graphs", [7, 8, 8, 9]),
        ("Dynamic Programming", [4, 5, 6, 7]),
        ("Divide & Conquer", [5, 6, 6, 7]),
    ]

    # Build a pool of questions per topic.
    questions_by_topic = {}
    for topic in topic_to_video.keys():
        qs = list(questions.find({"topic_tag": topic}))
        if qs:
            questions_by_topic[topic] = qs

    attempt_inserts = []
    for topic, scores in attempts_plan:
        qs = questions_by_topic.get(topic, [])
        for i, final in enumerate(scores):
            q = qs[i % len(qs)] if qs else None
            if not q:
                continue
            # llm_score and semantic_score are placeholders; later code will recompute.
            llm_score = max(0, min(10, final - 1))
            semantic_score = max(0.0, min(1.0, (final + 0.5) / 10.0))
            attempt_inserts.append(
                {
                    "user_id": arjun_id,
                    "question_id": str(q["_id"]),
                    "video_id": q["video_id"],
                    "student_answer": "My explanation based on lecture notes.",
                    "llm_score": int(llm_score),
                    "semantic_score": float(semantic_score),
                    "final_score": int(round(final)),
                    "feedback": "Review the key steps and ensure the recurrence/time complexity is derived clearly.",
                    "weak_concept": topic,
                    "topic_tag": topic,
                    "timestamp_start": float(q["timestamp_start"]),
                    "attempted_at": now - timedelta(days=(i % 14)),
                }
            )

    if attempt_inserts:
        quiz_attempts.insert_many(attempt_inserts)

    # 6) Recommendations (top 5 weakest topics for arjun)
    # Recompute averages from newly inserted attempts (or existing).
    attempts = list(quiz_attempts.find({"user_id": arjun_id}))
    if attempts:
        topic_scores = {}
        topic_counts = {}
        for a in attempts:
            topic = a.get("topic_tag") or "Unknown"
            topic_scores[topic] = topic_scores.get(topic, 0.0) + float(a.get("final_score", 0))
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

        avg_by_topic = {t: topic_scores[t] / max(1, topic_counts[t]) for t in topic_scores}
        weak_topics = sorted(avg_by_topic.items(), key=lambda x: x[1])[:5]

        topic_to_recommend_video = {}
        for v in sample_videos:
            for t in v["topics"]:
                topic_to_recommend_video.setdefault(t, v)

        recommendations_payload = []
        for topic, avg in weak_topics:
            # pick earliest question timestamp for the topic
            q = questions.find_one({"topic_tag": topic}, sort=[("timestamp_start", 1)])
            if not q:
                continue
            vdoc = videos.find_one({"video_id": q["video_id"]})
            rec = {
                "topic": topic,
                "avg_score": float(round(avg, 2)),
                "recommended_video_id": q["video_id"],
                "recommended_timestamp": float(q["timestamp_start"]),
                "video_title": (vdoc or {}).get("title", ""),
            }
            recommendations_payload.append(rec)

        if recommendations_payload:
            recommendations.update_one(
                {"user_id": arjun_id},
                {"$set": {"user_id": arjun_id, "weak_topics": recommendations_payload, "updated_at": datetime.utcnow()}},
                upsert=True,
            )

    print("Seed complete.")


if __name__ == "__main__":
    main()


# Quick verification:
# - Start MongoDB locally (or set MONGO_URI for Atlas) and run `python seed.py`
# - Then login via:
#   curl -X POST http://localhost:5000/api/auth/login \
#     -H "Content-Type: application/json" \
#     -d '{"email":"arjun@test.com","password":"test123"}'

