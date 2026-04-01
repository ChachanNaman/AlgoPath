from __future__ import annotations

import traceback
from datetime import datetime
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from celery import Celery
from pymongo import MongoClient
import certifi

from app.config import Config
from app.services.embedding_service import get_embedding
from app.services.llm_provider import generate_questions_for_chunk
from app.services.transcript_service import chunk_transcript, fetch_transcript, infer_topic_tag
from app.services.recommendation_service import compute_recommendations


def _parse_db_name(mongo_uri: str) -> str:
    # Match parsing logic in app/__init__.py.
    if not mongo_uri:
        return "algopath"
    try:
        # mongodb://localhost:27017/algopath -> algopath
        name = (mongo_uri.rsplit("/", 1)[-1] or "").split("?")[0].strip()
        return name or "algopath"
    except Exception:
        return "algopath"


def _append_mongo_query_param(uri: str, key: str, value: str) -> str:
    if not uri:
        return uri
    parsed = urlparse(uri)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if key not in query:
        query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def _connect_mongo_db(uri: str):
    is_srv = uri.startswith("mongodb+srv://")
    kwargs = {
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000,
        "socketTimeoutMS": 20000,
    }
    if is_srv:
        kwargs["tlsCAFile"] = certifi.where()
    client = MongoClient(uri, **kwargs)
    db = client[_parse_db_name(uri)]
    db.command("ping")
    return db


def _get_worker_db():
    """
    Keep Celery DB behavior aligned with Flask app:
    1) configured MONGO_URI
    2) local mongodb://localhost:27017/algopath
    3) optional mongomock when USE_MOCK_DB=True
    """
    mongo_uri = Config.MONGO_URI
    if not mongo_uri or "your_" in mongo_uri:
        mongo_uri = "mongodb://localhost:27017/algopath"
    if Config.MONGO_TLS_ALLOW_INVALID:
        mongo_uri = _append_mongo_query_param(mongo_uri, "tlsAllowInvalidCertificates", "true")

    try:
        return _connect_mongo_db(mongo_uri)
    except Exception:
        try:
            return _connect_mongo_db("mongodb://localhost:27017/algopath")
        except Exception:
            if not Config.USE_MOCK_DB:
                raise
            import mongomock

            return mongomock.MongoClient()["algopath"]


celery_app = Celery(
    "algopath",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)

# Compatibility: the recommended run command is:
#   celery -A app.tasks.celery_tasks worker --loglevel=info
# Celery expects a Celery instance named `app` by default.
app = celery_app


@celery_app.task(name="process_video_task")
def process_video_task(video_id: str) -> None:
    """
    Celery ingestion pipeline for one video:
    - fetch transcript
    - chunk into ~90s topic units
    - generate 3 questions per chunk (easy/medium/hard)
    - embed question text + chunk text
    - persist transcripts + questions
    - update video processed/topics
    """
    videos = None
    try:
        db = _get_worker_db()
        videos = db["videos"]
        transcripts = db["transcripts"]
        questions = db["questions"]

        # Mark in-progress state (optional; helpful for UI).
        videos.update_one({"video_id": video_id}, {"$set": {"processing_error": None}}, upsert=False)

        # Try fetching and chunking the real transcript.
        # Some videos intermittently fail transcript parsing (e.g. XML parser errors).
        # We degrade gracefully to fallback chunks instead of failing the whole video.
        try:
            transcript_items = fetch_transcript(video_id)
        except Exception:
            transcript_items = []
        chunks = chunk_transcript(transcript_items) if transcript_items else []

        # Fallback: if transcript is missing/unavailable, still generate questions
        # so the UI works for demos.
        if not chunks:
            video_doc = videos.find_one({"video_id": video_id}) or {}
            title = video_doc.get("title", "") or video_id
            topic_tag = infer_topic_tag(title)
            fallback_text = f"Lecture excerpt about {topic_tag}. Video title: {title}"
            chunks = [
                {
                    "text": fallback_text,
                    # Non-zero so timeline / “jump to concept” aren’t stuck at 0:00 when transcript is missing.
                    "start_time": 45.0,
                    "end_time": 135.0,
                    "topic_tag": topic_tag,
                    "chunk_index": 0,
                }
            ]

        all_transcript_chunks = []
        all_questions = []

        for chunk in chunks:
            try:
                chunk_text = chunk["text"]
                topic_tag = chunk["topic_tag"]
                timestamp_start = float(chunk["start_time"])
                chunk_embedding = get_embedding(chunk_text)

                # Generate questions via mock or Groq depending on Config.
                llm_questions = generate_questions_for_chunk(chunk_text, topic_tag, timestamp_start)

                # Each generated question gets its own embedding for semantic scoring.
                for q in llm_questions:
                    question_text = q.get("question", "") or ""
                    if not question_text:
                        continue
                    q_embedding = get_embedding(question_text)
                    all_questions.append(
                        {
                            "video_id": video_id,
                            "chunk_index": int(chunk["chunk_index"]),
                            "question_text": question_text,
                            "correct_answer": q.get("correct_answer", "") or "",
                            "explanation": q.get("explanation", "") or "",
                            "difficulty": q.get("difficulty", "easy") or "easy",
                            "topic_tag": q.get("topic_tag", topic_tag) or topic_tag,
                            "timestamp_start": timestamp_start,
                            "language": "en",
                            "embedding": q_embedding,
                        }
                    )

                all_transcript_chunks.append(
                    {
                        "text": chunk_text,
                        "start_time": float(chunk["start_time"]),
                        "end_time": float(chunk["end_time"]),
                        "topic_tag": topic_tag,
                        "chunk_index": int(chunk["chunk_index"]),
                        "embedding": chunk_embedding,
                    }
                )
            except Exception:
                # Per-chunk failure shouldn't fail the whole video.
                # We'll keep going; worst case the chunk just contributes no questions/chunk entry.
                continue

        # Clear old questions/transcripts for this video before inserting (idempotent retries).
        questions.delete_many({"video_id": video_id})
        transcripts.delete_many({"video_id": video_id})

        # If no questions were generated, mark as failed.
        if not all_questions:
            raise RuntimeError("No questions were generated for this video (all_questions empty).")

        # Persist transcripts and questions.
        transcripts.update_one(
            {"video_id": video_id},
            {"$set": {"chunks": all_transcript_chunks}},
            upsert=True,
        )
        questions.insert_many(all_questions)

        # Update video topics + processed.
        topic_tags = sorted({c["topic_tag"] for c in all_transcript_chunks if c.get("topic_tag")})
        videos.update_one(
            {"video_id": video_id},
            {"$set": {"processed": True, "topics": topic_tags, "processing_error": None, "updated_at": datetime.utcnow()}},
        )

    except Exception:
        err = traceback.format_exc()
        if videos is None:
            try:
                db = _get_worker_db()
                videos = db["videos"]
            except Exception:
                return
        videos.update_one(
            {"video_id": video_id},
            {
                "$set": {
                    "processed": False,
                    # Keep it concise for UI debugging.
                    "processing_error": str(err.splitlines()[-1])[:350],
                }
            },
        )


@celery_app.task(name="update_recommendations_task")
def update_recommendations_task(user_id: str) -> None:
    db = _get_worker_db()
    compute_recommendations(user_id, db)


# Quick manual test:
# - With Redis running and Celery worker started:
#   celery -A app.tasks.celery_tasks worker --loglevel=info
# - Call:
#   POST /api/playlist/ingest
# - Verify `videos` documents become `processed=true` and `questions` insert.

