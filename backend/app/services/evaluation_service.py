from __future__ import annotations

from app.services.embedding_service import cosine_similarity, get_embedding
from app.services.llm_provider import evaluate_student_answer


def compute_final_score(*, llm_score: int, semantic_score: float) -> int:
    """
    Final score per spec:
      final_score = round(0.7 * llm_score + 0.3 * (semantic_score * 10))

    Where `semantic_score` is cosine similarity expected in [0,1] range.
    """
    return int(round(0.7 * llm_score + 0.3 * (semantic_score * 10)))


def evaluate_student_answer_hybrid(
    *,
    question: str,
    correct_answer: str,
    student_answer: str,
    topic_tag: str,
    question_embedding: list[float],
    language: str = "en",
) -> dict:
    """
    Hybrid evaluation:
    - semantic_score from cosine similarity between question embedding and student answer embedding
    - llm_score from Groq examiner feedback (0-10)
    """
    s_embedding = get_embedding(student_answer)
    semantic_score = cosine_similarity(s_embedding, question_embedding)

    llm_result = evaluate_student_answer(
        question=question,
        correct_answer=correct_answer,
        student_answer=student_answer,
        topic_tag=topic_tag,
        language=language,
    )

    llm_score = int(llm_result.get("score", 0) or 0)
    # Spec formula: final_score = round(0.7*llm_score + 0.3*(semantic_score*10))
    final_score = compute_final_score(llm_score=llm_score, semantic_score=semantic_score)
    final_score = max(0, min(10, final_score))

    return {
        "llm_score": llm_score,
        "semantic_score": float(semantic_score),
        "final_score": final_score,
        "feedback": llm_result.get("feedback", ""),
        "weak_concept": llm_result.get("weak_concept", topic_tag),
        "is_partially_correct": bool(llm_result.get("is_partially_correct", False)),
    }


# Quick test (manual):
# - Call evaluate_student_answer_hybrid(...) after implementing the quiz submit route.

