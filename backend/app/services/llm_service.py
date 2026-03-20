from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from groq import Groq


client = Groq(api_key=os.getenv("GROQ_API_KEY"))
GROQ_MODEL = "llama-3.3-70b-versatile"


def _strip_html_tags(text: str) -> str:
    return re.sub(r"<[^>]*?>", "", text or "")


def call_groq(messages: list[dict[str, Any]], expect_json: bool = True, retries: int = 3) -> str:
    """
    Groq SDK wrapper.
    - Uses `response_format={"type":"json_object"}` when `expect_json=True`
    """
    for attempt in range(retries):
        try:
            kwargs: dict[str, Any] = {
                "model": GROQ_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.3,
            }
            if expect_json:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2**attempt)
            else:
                raise e


def generate_questions_for_chunk(chunk_text: str, topic_tag: str, timestamp_start: float):
    system_prompt = (
        "You are a university-level DAA professor. Generate exam-quality questions with clear, unambiguous correct answers. "
        "Return only valid JSON."
    )
    user_prompt = (
        f"Given this lecture transcript chunk on the topic '{topic_tag}': {chunk_text}\n\n"
        "Generate exactly 3 questions — one easy, one medium, one hard. "
        'Return JSON: {"questions": [{"question":"...","correct_answer":"...","explanation":"...","difficulty":"easy","topic_tag":"...","timestamp_start": '
        f"{timestamp_start}" + "}]}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = call_groq(messages, expect_json=True)

    try:
        parsed = json.loads(raw)
        return parsed.get("questions", [])
    except json.JSONDecodeError:
        # Fallback: return empty set so pipeline continues safely.
        return []


def evaluate_student_answer(
    question: str,
    correct_answer: str,
    student_answer: str,
    topic_tag: str,
    language: str = "en",
):
    system_prompt = (
        "You are a strict but fair DAA examiner. Score student answers 0-10. "
        "Be generous with partial credit. Return only valid JSON."
    )

    lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu"}
    language_name = lang_map.get(language, "English")
    student_clean = _strip_html_tags((student_answer or "")[:2000].strip())

    user_prompt = (
        f"Question: {question}\n"
        f"Model Answer: {correct_answer}\n"
        f"Student Answer: {student_clean}\n"
        f"Topic Tag: {topic_tag}\n"
    )
    if language != "en":
        user_prompt += (
            f"Provide your feedback in {language_name} language but keep all technical terms "
            "(Big O notation, algorithm names, and data structure names) in English."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = call_groq(messages, expect_json=True)

    try:
        parsed = json.loads(raw)
        return parsed
    except json.JSONDecodeError:
        return {"score": 0, "feedback": "Could not parse evaluator output.", "weak_concept": topic_tag, "is_partially_correct": False}


def translate_content(text: str, target_language: str):
    lang_map = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu"}
    target_language_name = lang_map.get(target_language, target_language)

    system_prompt = "You are a helpful translation engine for technical CS content."
    user_prompt = (
        f"Translate the following to {target_language_name}. "
        "Keep all technical CS terms, algorithm names, and Big O notation in English. "
        f"Return JSON: {{\"translated\": \"...\"}}\n\n{text}"
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = call_groq(messages, expect_json=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"translated": text}


def ai_tutor_respond(user_message: str, conversation_history: list[dict], context_chunks: list[dict]):
    # Ground tutor response in transcript chunks.
    system_prompt = "You are a DAA tutor. Use the provided lecture context to answer the user's question."
    context_joined = "\n\n".join(
        [
            f"[{c.get('video_title','')}] {c.get('start_time','')}–{c.get('end_time','')}: {c.get('text','')}"
            for c in context_chunks
        ]
    )
    base_context = f"Here is lecture context:\n{context_joined}\n\nAnswer the user based on this context."

    messages = [{"role": "system", "content": f"{system_prompt}\n\n{base_context}"}]
    for m in conversation_history or []:
        if m.get("role") in ("user", "assistant"):
            messages.append({"role": m["role"], "content": m.get("content", "")})
    messages.append({"role": "user", "content": _strip_html_tags((user_message or "")[:2000].strip())})

    raw = call_groq(messages, expect_json=False)
    return raw


# Quick manual test (Phase 7):
# - Set `backend/.env` with a valid `GROQ_API_KEY`
# - Run a Python snippet to call `generate_questions_for_chunk(...)`


