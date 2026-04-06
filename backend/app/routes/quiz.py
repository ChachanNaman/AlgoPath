from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.services.evaluation_service import evaluate_student_answer_hybrid
from app.services.llm_provider import translate_content
from app.services.recommendation_service import compute_recommendations
from app.services.transcript_service import infer_topic_tag
from app.tasks.celery_tasks import update_recommendations_task

# Match recommendations when transcript has no per-chunk timestamps.
_FALLBACK_TIMESTAMP_SECONDS = 48.0


quiz_bp = Blueprint("quiz_bp", __name__)


def _strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]*?>", "", value or "")


def _sanitize_user_input(value: str, max_len: int = 2000) -> str:
    return _strip_html_tags((value or "").strip()[:max_len])


@quiz_bp.get("/questions/<video_id>")
@jwt_required()
def get_questions(video_id: str):
    difficulty = request.args.get("difficulty")
    count = int(request.args.get("count", 5))
    count = max(1, min(count, 20))

    questions = current_app.config["MONGO_DB"]["questions"]

    query: dict[str, Any] = {"video_id": video_id}
    if difficulty in ("easy", "medium", "hard"):
        query["difficulty"] = difficulty

    docs = list(questions.find(query))
    if not docs:
        return jsonify([]), 200

    import random

    random.shuffle(docs)
    docs = docs[:count]

    resp = []
    for d in docs:
        d = dict(d)
        d["_id"] = str(d.get("_id"))
        resp.append(
            {
                "question_id": d["_id"],
                "question_text": d.get("question_text", ""),
                "correct_answer": d.get("correct_answer", ""),
                "explanation": d.get("explanation", ""),
                "difficulty": d.get("difficulty", "easy"),
                "topic_tag": d.get("topic_tag", ""),
                "timestamp_start": float(d.get("timestamp_start", 0.0)),
                "video_id": d.get("video_id", video_id),
            }
        )
    # Spec says array of question objects without embedding field; we comply by omitting `embedding`.
    return jsonify(resp), 200


@quiz_bp.post("/submit")
@jwt_required()
@limiter.limit("30/minute", key_func=lambda: get_jwt_identity() or request.remote_addr)
def submit_answer():
    payload = request.get_json(silent=True) or {}
    question_id = payload.get("question_id")
    student_answer_raw = payload.get("student_answer", "")
    language = payload.get("language", "en") or "en"

    if not question_id or not isinstance(question_id, str):
        return jsonify({"message": "question_id is required"}), 400
    student_answer = _sanitize_user_input(student_answer_raw)

    db = current_app.config["MONGO_DB"]
    questions = db["questions"]
    quiz_attempts = db["quiz_attempts"]
    videos = db["videos"]

    try:
        q_oid = ObjectId(question_id)
    except Exception:
        return jsonify({"message": "invalid question_id"}), 400

    question = questions.find_one({"_id": q_oid})
    if not question:
        return jsonify({"message": "question not found"}), 404

    llm_question_text = _sanitize_user_input(question.get("question_text", ""), max_len=2000)
    correct_answer = _sanitize_user_input(question.get("correct_answer", ""), max_len=2000)
    topic_tag = (question.get("topic_tag") or "").strip() or "Unknown"
    timestamp_start = float(question.get("timestamp_start", 0.0))
    video_id = question.get("video_id", "")
    question_embedding = question.get("embedding")

    video_doc = videos.find_one({"video_id": video_id}) or {}
    title = (video_doc.get("title") or "").strip()
    inferred = infer_topic_tag(title) if title else "General"
    if topic_tag in ("General", "Unknown", ""):
        topic_tag = inferred if inferred not in ("General",) else (topic_tag or "General")
    if timestamp_start <= 0:
        timestamp_start = _FALLBACK_TIMESTAMP_SECONDS

    if not isinstance(question_embedding, list):
        return jsonify({"message": "question embedding missing; please try again."}), 500

    # Hybrid scoring (LLM + semantic similarity).
    evaluation = evaluate_student_answer_hybrid(
        question=llm_question_text,
        correct_answer=correct_answer,
        student_answer=student_answer,
        topic_tag=topic_tag,
        question_embedding=question_embedding,
        language=language,
    )

    llm_score = int(evaluation["llm_score"])
    semantic_score = float(evaluation["semantic_score"])
    final_score = int(evaluation["final_score"])
    feedback = evaluation["feedback"]

    identity = get_jwt_identity()
    weak_concept = evaluation.get("weak_concept") or topic_tag

    quiz_attempts.insert_one(
        {
            "user_id": identity,
            "question_id": question_id,
            "video_id": video_id,
            "student_answer": student_answer,
            "llm_score": llm_score,
            "semantic_score": semantic_score,
            "final_score": final_score,
            "feedback": feedback,
            "weak_concept": weak_concept,
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
            "attempted_at": datetime.utcnow(),
        }
    )

    # Async recommendations update (or sync if Celery broker is down).
    try:
        update_recommendations_task.delay(str(identity))
    except Exception:
        try:
            compute_recommendations(str(identity), db)
        except Exception:
            pass

    return (
        jsonify(
            {
                "final_score": final_score,
                "feedback": feedback,
                "weak_concept": weak_concept,
                "correct_answer": correct_answer,
                "explanation": question.get("explanation", ""),
                "recommended_timestamp": timestamp_start,
                "video_id": video_id,
            }
        ),
        200,
    )


@quiz_bp.post("/translate")
@jwt_required()
def translate_question():
    payload = request.get_json(silent=True) or {}
    question_id = payload.get("question_id")
    target_language = payload.get("target_language", "en") or "en"

    if not question_id:
        return jsonify({"message": "question_id is required"}), 400

    db = current_app.config["MONGO_DB"]
    questions = db["questions"]
    try:
        q_oid = ObjectId(question_id)
    except Exception:
        return jsonify({"message": "invalid question_id"}), 400

    question = questions.find_one({"_id": q_oid})
    if not question:
        return jsonify({"message": "question not found"}), 404

    question_text = _sanitize_user_input(question.get("question_text", ""), max_len=2000)
    correct_answer = _sanitize_user_input(question.get("correct_answer", ""), max_len=2000)

    translated_q = translate_content(question_text, target_language)
    translated_a = translate_content(correct_answer, target_language)

    return jsonify({"translated_question": translated_q.get("translated", translated_q), "translated_answer": translated_a.get("translated", translated_a)}), 200


@quiz_bp.get("/due-reviews/<user_id>")
@jwt_required()
def get_due_reviews(user_id: str):
    identity = get_jwt_identity()
    if str(identity) != str(user_id):
        return jsonify({"message": "forbidden"}), 403

    from datetime import timedelta

    now = datetime.utcnow()
    db = current_app.config["MONGO_DB"]
    quiz_attempts = db["quiz_attempts"]
    questions = db["questions"]

    attempts = list(
        quiz_attempts.find({"user_id": user_id, "final_score": {"$lt": 7}}).sort("attempted_at", -1)
    )

    due = []
    seen_questions = set()

    for attempt in attempts:
        qid = str(attempt.get("question_id", "") or "")
        if not qid or qid in seen_questions:
            continue
        seen_questions.add(qid)

        score = int(attempt.get("final_score", 0) or 0)
        attempted_at = attempt.get("attempted_at") or now
        if not isinstance(attempted_at, datetime):
            attempted_at = now

        # Interval based on score (lower score = sooner review)
        if score <= 3:
            interval_days = 1
        elif score <= 5:
            interval_days = 3
        else:
            interval_days = 7

        due_date = attempted_at + timedelta(days=interval_days)
        if due_date > now:
            continue

        try:
            q_oid = ObjectId(qid)
        except Exception:
            continue

        question = questions.find_one({"_id": q_oid})
        if not question:
            continue

        due.append(
            {
                "_id": str(question.get("_id")),
                "question_text": question.get("question_text", ""),
                "topic_tag": question.get("topic_tag", ""),
                "difficulty": question.get("difficulty", "easy"),
                "previous_score": score,
                "video_id": question.get("video_id", ""),
                "timestamp_start": float(question.get("timestamp_start", 0.0) or 0.0),
                "days_overdue": int((now - due_date).days),
                "attempted_at": attempted_at.isoformat(),
            }
        )

    due.sort(key=lambda x: x.get("days_overdue", 0), reverse=True)
    return jsonify({"due_count": len(due), "questions": due[:10]}), 200


@quiz_bp.get("/heatmap/<video_id>")
@jwt_required()
def get_video_heatmap(video_id: str):
    db = current_app.config["MONGO_DB"]
    questions = db["questions"]
    quiz_attempts = db["quiz_attempts"]

    q_docs = list(questions.find({"video_id": video_id}, {"timestamp_start": 1, "topic_tag": 1}))
    q_map = {str(q.get("_id")): q for q in q_docs}

    attempts = list(quiz_attempts.find({"video_id": video_id}))

    buckets: dict[int, list[float]] = {}
    for attempt in attempts:
        qid = str(attempt.get("question_id", "") or "")
        if qid not in q_map:
            continue
        ts = float((q_map[qid] or {}).get("timestamp_start", 0) or 0)
        bucket = int(ts // 60) * 60
        buckets.setdefault(bucket, []).append(float(attempt.get("final_score", 5) or 5))

    heatmap = []
    for bucket_ts, scores in buckets.items():
        avg = sum(scores) / max(1, len(scores))
        heatmap.append(
            {
                "timestamp": int(bucket_ts),
                "avg_score": round(avg, 1),
                "attempt_count": int(len(scores)),
                "difficulty": "hard" if avg < 4 else "medium" if avg < 7 else "easy",
            }
        )

    heatmap.sort(key=lambda x: x["timestamp"])
    return jsonify({"heatmap": heatmap}), 200


# Test:
# 1) Get questions:
# curl http://localhost:5000/api/quiz/questions/VIDEO_ID?count=5&difficulty=easy \
#   -H "Authorization: Bearer TOKEN_HERE"
#
# 2) Submit:
# curl -X POST http://localhost:5000/api/quiz/submit \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer TOKEN_HERE" \
#   -d '{"question_id":"QUESTION_OID","student_answer":"...","language":"en"}'

