from __future__ import annotations

import re
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app import limiter
from app.services.embedding_service import find_top_chunks, get_embedding
from app.services.llm_provider import ai_tutor_respond, translate_content
from app.config import Config


ai_tutor_bp = Blueprint("ai_tutor_bp", __name__)


def _strip_html_tags(value: str) -> str:
    return re.sub(r"<[^>]*?>", "", value or "")


def _sanitize(value: str, max_len: int = 2000) -> str:
    return _strip_html_tags((value or "").strip()[:max_len])


@ai_tutor_bp.post("/chat")
@jwt_required()
@limiter.limit("20/minute", key_func=lambda: get_jwt_identity() or request.remote_addr)
def chat():
    payload = request.get_json(silent=True) or {}
    message = _sanitize(payload.get("message", ""))
    conversation_history_raw = payload.get("conversation_history", []) or []
    conversation_history = []
    # Sanitize all history entries before sending to LLM.
    for m in conversation_history_raw:
        if not isinstance(m, dict):
            continue
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        conversation_history.append({"role": role, "content": _sanitize(m.get("content", ""), 2000)})
    language = payload.get("language", "en") or "en"

    identity = get_jwt_identity()
    db = current_app.config["MONGO_DB"]
    quiz_attempts = db["quiz_attempts"]
    transcripts = db["transcripts"]
    videos = db["videos"]

    # Determine which videos the user has interacted with.
    video_ids = quiz_attempts.distinct("video_id", {"user_id": identity})
    if not video_ids:
        # Still respond; just no context chunks.
        response_text = ai_tutor_respond(message, conversation_history, [])
        if language != "en":
            response_text = translate_content(response_text, language).get("translated", response_text)
        return jsonify({"response": response_text, "context_chunks": []}), 200

    # Flatten transcript chunks across those videos.
    transcript_docs = list(transcripts.find({"video_id": {"$in": list(video_ids)}}))
    transcript_chunks = []
    for doc in transcript_docs:
        parent_video_id = doc.get("video_id")
        for c in doc.get("chunks", []) or []:
            chunk_obj = dict(c)
            chunk_obj["video_id"] = parent_video_id
            transcript_chunks.append(chunk_obj)

    # RAG: retrieve top 3 chunks using embedding similarity.
    # Note: find_top_chunks expects chunk objects to include `embedding`.
    top_chunks = find_top_chunks(message, transcript_chunks, top_k=3)

    # Add video titles to context chunks for display + grounding formatting.
    chunk_with_titles = []
    for chunk in top_chunks:
        parent_video_id = chunk.get("video_id")
        video_doc = videos.find_one({"video_id": parent_video_id})
        video_title = (video_doc or {}).get("title", "") or ""
        chunk_with_titles.append({**chunk, "video_title": video_title})

    response_text = ai_tutor_respond(message, conversation_history, chunk_with_titles)
    if language != "en":
        response_text = translate_content(response_text, language).get("translated", response_text)

    context_payload = [
        {"video_title": c.get("video_title", ""), "start_time": float(c.get("start_time", 0.0)), "end_time": float(c.get("end_time", 0.0))}
        for c in chunk_with_titles
    ]

    return jsonify({"response": response_text, "context_chunks": context_payload}), 200


@ai_tutor_bp.post("/explain")
@jwt_required()
@limiter.limit("30/minute", key_func=lambda: get_jwt_identity() or request.remote_addr)
def explain_concept():
    payload = request.get_json(silent=True) or {}
    question = _sanitize(payload.get("question", ""), 2000)
    correct_answer = _sanitize(payload.get("correct_answer", ""), 2000)
    topic = _sanitize(payload.get("topic", ""), 200)

    # In real mode use Groq via llm_service; in mock mode provide a stable fallback.
    if Config.USE_MOCK_LLM or not (Config.GROQ_API_KEY or "").strip():
        explanation = (
            f"Think of `{topic or 'this concept'}` like a real-life checklist: you follow a simple rule each step to avoid mistakes. "
            "The key is to focus on the one condition that must always stay true.\n\n"
            f"Key takeaway: {correct_answer[:140]}"
        )
        return jsonify({"explanation": explanation}), 200

    from app.services.llm_service import call_groq

    messages = [
        {
            "role": "system",
            "content": (
                "You are a patient DAA tutor who explains hard concepts using simple everyday analogies. "
                "Be concise — max 4 sentences. Always end with one key takeaway."
            ),
        },
        {
            "role": "user",
            "content": (
                "A student got this wrong:\n"
                f"Question: {question}\n"
                f"Correct answer: {correct_answer}\n"
                f"Topic: {topic}\n\n"
                "Explain this concept simply using an analogy a beginner would understand. "
                "Then give the key formula or rule to remember."
            ),
        },
    ]

    explanation = call_groq(messages, expect_json=False)
    return jsonify({"explanation": explanation}), 200


# Test:
# curl -X POST http://localhost:5000/api/ai_tutor/chat \
#   -H "Content-Type: application/json" \
#   -H "Authorization: Bearer TOKEN_HERE" \
#   -d '{"message":"Explain Merge Sort","conversation_history":[],"language":"en"}'

