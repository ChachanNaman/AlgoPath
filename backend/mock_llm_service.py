def generate_questions_for_chunk(chunk_text, topic_tag, timestamp_start):
    # Topic-aware mock questions so the UI + tutor don't look identical.
    t = (topic_tag or "DAA").strip().lower()

    if "sorting" in t or "merge" in t or "quick" in t:
        return [
            {
                "question": "What is the typical time complexity of merge sort?",
                "correct_answer": "O(n log n)",
                "explanation": "Merge sort splits recursively and merges in linear time per level.",
                "difficulty": "easy",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "Write the recurrence relation for merge sort.",
                "correct_answer": "T(n) = 2T(n/2) + O(n)",
                "explanation": "Two subproblems of size n/2 plus O(n) work to merge.",
                "difficulty": "medium",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "Why is merge sort suitable for linked lists?",
                "correct_answer": "It does not require random access; it works with sequential traversal.",
                "explanation": "Linked lists avoid random access, and merge sort uses sequential split/merge.",
                "difficulty": "hard",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
        ]

    if "greedy" in t:
        return [
            {
                "question": "What property must hold for a greedy algorithm to be correct?",
                "correct_answer": "Greedy-choice property and optimal substructure.",
                "explanation": "Greedy-choice property ensures local decisions lead to a global optimum.",
                "difficulty": "easy",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "How do greedy algorithms work conceptually?",
                "correct_answer": "Choose the best local option at each step and reduce the remaining problem.",
                "explanation": "They iterate on a smaller subproblem after each local selection.",
                "difficulty": "medium",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "Why can greedy fail if the greedy-choice property doesn't hold?",
                "correct_answer": "Local optimum can prevent the global optimum.",
                "explanation": "Without the property, a locally best choice may lead to a globally suboptimal solution.",
                "difficulty": "hard",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
        ]

    if "graph" in t:
        return [
            {
                "question": "Which traversal explores neighbors level-by-level?",
                "correct_answer": "BFS (Breadth-First Search).",
                "explanation": "BFS uses a queue and expands nodes in increasing distance order.",
                "difficulty": "easy",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "When are shortest paths typically computed with Dijkstra?",
                "correct_answer": "When all edge weights are non-negative.",
                "explanation": "Dijkstra relies on non-negative weights to finalize distances safely.",
                "difficulty": "medium",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "Why can Dijkstra fail with negative edges?",
                "correct_answer": "Negative edges can produce shorter paths after a node is finalized.",
                "explanation": "The greedy finalize step breaks when distances can decrease later.",
                "difficulty": "hard",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
        ]

    if "dynamic programming" in t or t.startswith("dp"):
        return [
            {
                "question": "What is the key idea behind dynamic programming?",
                "correct_answer": "Overlapping subproblems and optimal substructure.",
                "explanation": "DP reuses computed answers and composes optimal solutions from smaller ones.",
                "difficulty": "easy",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "What do DP solutions typically define?",
                "correct_answer": "State, transition (recurrence), and how to compute from smaller states.",
                "explanation": "You define what each DP state represents and then compute via recurrence.",
                "difficulty": "medium",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "How do you implement DP in practice?",
                "correct_answer": "Use memoization (top-down) or tabulation (bottom-up).",
                "explanation": "Memoization caches recursive results; tabulation fills a table iteratively.",
                "difficulty": "hard",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
        ]

    if "divide" in t or "conquer" in t:
        return [
            {
                "question": "What does divide-and-conquer do conceptually?",
                "correct_answer": "Divide into subproblems, solve recursively, and combine results.",
                "explanation": "It reduces complexity by breaking and merging solutions.",
                "difficulty": "easy",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "What is commonly used to solve divide-and-conquer recurrences?",
                "correct_answer": "Master Theorem.",
                "explanation": "Master Theorem compares f(n) with n^{log_b(a)} to determine complexity.",
                "difficulty": "medium",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
            {
                "question": "Why is recurrence analysis important for time complexity?",
                "correct_answer": "It captures how many subproblems exist and the combine cost per level.",
                "explanation": "The recurrence turns recursive structure into measurable total work.",
                "difficulty": "hard",
                "topic_tag": topic_tag,
                "timestamp_start": timestamp_start,
            },
        ]

    # Generic fallback
    return [
        {
            "question": "Explain the main algorithm idea for this topic.",
            "correct_answer": "Use the defining recurrence/invariant and reason about correctness + complexity.",
            "explanation": "Correct reasoning depends on the topic's standard structure (recurrence or invariant).",
            "difficulty": "easy",
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
        },
        {
            "question": "What usually drives the time complexity here?",
            "correct_answer": "The number of subproblems and the work done per recursion/transition step.",
            "explanation": "Complexity is determined by recursion depth and per-level cost.",
            "difficulty": "medium",
            "topic_tag": topic_tag,
            "timestamp_start": timestamp_start,
        },
        {
            "question": "Why does the approach produce correct results?",
            "correct_answer": "It preserves the necessary invariant/optimal substructure during decomposition.",
            "explanation": "Correctness follows from decomposition and how subresults combine.",
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
    # Make mock tutor responses vary using retrieved context.
    msg = (user_message or "").strip()

    if not context_chunks:
        return (
            "I don’t yet have lecture context to ground this answer. "
            "Try submitting a couple of quiz answers first, then ask again."
        )

    topic_list = []
    timestamp_list = []
    for c in context_chunks[:3]:
        topic_list.append(c.get("topic_tag") or c.get("weak_topic") or "DAA")
        start = c.get("start_time", 0)
        end = c.get("end_time", 0)
        timestamp_list.append((start, end))

    def _mmss(sec):
        sec = float(sec or 0)
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m:02d}:{s:02d}"

    primary_topic = topic_list[0]
    primary_start, primary_end = timestamp_list[0]

    return (
        f"You’re asking about: {msg[:80]}. "
        f"From the lecture segment on `{primary_topic}` (around {_mmss(primary_start)}–{_mmss(primary_end)}), "
        "the key idea is to connect the problem definition to the correct complexity and correctness reasoning. "
        "If you share your approach, I’ll point out where it matches (or where the recurrence/invariants need fixing)."
    )


# Quick test (manual):
# - Run a python repl and call:
#   from backend.mock_llm_service import generate_questions_for_chunk
#   generate_questions_for_chunk("...", "Sorting", 12.0)

