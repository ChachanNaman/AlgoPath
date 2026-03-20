from __future__ import annotations

import traceback
from datetime import datetime

from celery import Celery
from pymongo import MongoClient

from app.config import Config
from app.services.embedding_service import get_embedding
from app.services.llm_provider import generate_questions_for_chunk
from app.services.transcript_service import chunk_transcript, fetch_transcript
from app.services.recommendation_service import compute_recommendations


def _parse_db_name(mongo_uri: str) -> str:
    # Match parsing logic in app/__init__.py.
    if not mongo_uri:
        return "algopath"
    try:
        # mongodb://localhost:27017/algopath -> algopath
        return (mongo_uri.rsplit("/", 1)[-1] or "algopath").split("?")[0]
    except Exception:
        return "algopath"


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
    # Build a Mongo client inside the worker.
    mongo_uri = Config.MONGO_URI
    if not mongo_uri or "your_" in mongo_uri:
        mongo_uri = "mongodb://localhost:27017/algopath"
    db_name = _parse_db_name(mongo_uri)
    db = MongoClient(mongo_uri)[db_name]

    videos = db["videos"]
    transcripts = db["transcripts"]
    questions = db["questions"]

    try:
        # Mark in-progress state (optional; helpful for UI).
        videos.update_one({"video_id": video_id}, {"$set": {"processing_error": None}}, upsert=False)

        transcript_items = fetch_transcript(video_id)
        chunks = chunk_transcript(transcript_items)

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

        # Persist transcripts and questions.
        transcripts.update_one(
            {"video_id": video_id},
            {"$set": {"chunks": all_transcript_chunks}},
            upsert=True,
        )
        if all_questions:
            questions.insert_many(all_questions)

        # Update video topics + processed.
        topic_tags = sorted({c["topic_tag"] for c in all_transcript_chunks if c.get("topic_tag")})
        videos.update_one(
            {"video_id": video_id},
            {"$set": {"processed": True, "topics": topic_tags, "processing_error": None, "updated_at": datetime.utcnow()}},
        )

    except Exception:
        err = traceback.format_exc()
        videos.update_one(
            {"video_id": video_id},
            {"$set": {"processed": False, "processing_error": err}},
        )


@celery_app.task(name="update_recommendations_task")
def update_recommendations_task(user_id: str) -> None:
    mongo_uri = Config.MONGO_URI
    if not mongo_uri or "your_" in mongo_uri:
        mongo_uri = "mongodb://localhost:27017/algopath"
    db_name = _parse_db_name(mongo_uri)
    db = MongoClient(mongo_uri)[db_name]
    compute_recommendations(user_id, db)


# Quick manual test:
# - With Redis running and Celery worker started:
#   celery -A app.tasks.celery_tasks worker --loglevel=info
# - Call:
#   POST /api/playlist/ingest
# - Verify `videos` documents become `processed=true` and `questions` insert.

