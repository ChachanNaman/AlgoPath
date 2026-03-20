from __future__ import annotations

"""
LLM provider wrapper.

During early development we use mock responses (`mock_llm_service.py`) to build the full pipeline
without requiring Groq credentials. Flip `Config.USE_MOCK_LLM` to False for real Groq calls.
"""

from app.config import Config


if Config.USE_MOCK_LLM:
    from mock_llm_service import (  # type: ignore
        ai_tutor_respond,
        evaluate_student_answer,
        generate_questions_for_chunk,
        translate_content,
    )
else:
    from .llm_service import (  # noqa: F401
        ai_tutor_respond,
        evaluate_student_answer,
        generate_questions_for_chunk,
        translate_content,
    )


__all__ = [
    "generate_questions_for_chunk",
    "evaluate_student_answer",
    "translate_content",
    "ai_tutor_respond",
]


# Quick test (manual):
# - Set `USE_MOCK_LLM=True` in `backend/.env`
# - Then:
#     from app.services.llm_provider import generate_questions_for_chunk
#     generate_questions_for_chunk("...", "Sorting", 12.0)
#   should return 3 mock questions immediately.

