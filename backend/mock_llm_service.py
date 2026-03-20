def generate_questions_for_chunk(chunk_text, topic_tag, timestamp_start):
    return [
        {
            "question": f"What is the time complexity of merge sort?",
            "correct_answer": "O(n log n)",
            "explanation": "Merge sort divides array in half recursively and merges.",
            "difficulty": "easy",
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
        },
        {
            "question": f"Explain the recurrence relation for merge sort.",
            "correct_answer": "T(n) = 2T(n/2) + O(n)",
            "explanation": "Two subproblems of size n/2 plus linear merge step.",
            "difficulty": "medium",
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
        },
        {
            "question": f"Why is merge sort preferred over quicksort for linked lists?",
            "correct_answer": "Merge sort does not require random access, making it ideal for linked lists where random access is O(n).",
            "explanation": "Sequential access pattern of merge sort suits linked list traversal.",
            "difficulty": "hard",
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
        },
    ]


def evaluate_student_answer(question, correct_answer, student_answer, topic_tag, language="en"):
    score = 7 if len(student_answer) > 20 else 3
    return {
        "score": score,
        "feedback": "Good attempt. Review the time complexity derivation more carefully.",
        "weak_concept": topic_tag,
        "is_partially_correct": score > 4,
    }


def translate_content(text, target_language):
    return {"translated": f"[{target_language} translation of: {text[:50]}...]"}


def ai_tutor_respond(user_message, conversation_history, context_chunks):
    return (
        f"Based on the lecture content, {user_message[:30]}... involves important algorithmic concepts. "
        "The key insight is that understanding the recurrence relation helps derive the time complexity."
    )


# Quick test (manual):
# - Run a python repl and call:
#   from backend.mock_llm_service import generate_questions_for_chunk
#   generate_questions_for_chunk("...", "Sorting", 12.0)

