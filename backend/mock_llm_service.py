import re


def _extract_video_title(chunk_text: str) -> str:
    """Pull title from Celery fallback chunk or use first line of real transcript."""
    text = (chunk_text or "").strip()
    m = re.search(r"Video title:\s*(.+?)(?:\n|$)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()[:200]
    line = text.split("\n")[0].strip()
    return line[:200] if line else ""


def _transcript_snippet(chunk_text: str, max_len: int = 220) -> str:
    """Strip boilerplate; keep a short excerpt for grounded questions."""
    text = (chunk_text or "").strip()
    text = re.sub(r"^Lecture excerpt about[^.]*\.\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Video title:.*", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]


def _combined_context(chunk_text: str, topic_tag: str) -> str:
    return f"{topic_tag or ''} {chunk_text or ''}".lower()


def _title_grounded_pack(title: str, topic_tag: str, timestamp_start: float):
    """
    When we don't have a specialized template, still tie every question to this video's title/snippet
    so quizzes are not identical across lectures.
    """
    label = (title or topic_tag or "this lecture").strip() or "this lecture"
    return [
        {
            "question": f'For the lecture titled “{label}”, what problem, definition, or structure is the instructor introducing first?',
            "correct_answer": f"The opening of “{label}” states the main definition or setup (what objects you measure and what you compare).",
            "explanation": "Restate the definition using the same terms the instructor uses in the first few minutes.",
            "difficulty": "easy",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
        {
            "question": f'In “{label}”, what is the main algorithm or method taught, and what is one key step or rule it relies on?',
            "correct_answer": f"Name the technique from “{label}” and one concrete step the instructor demonstrates (e.g., a formula, case split, or update rule).",
            "explanation": "Your answer should match the method in this video, not a different algorithm with a similar name.",
            "difficulty": "medium",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
        {
            "question": f'Why does the approach in “{label}” work or save effort compared to brute force—what argument (correctness, pruning, recurrence, or invariant) does the instructor use?',
            "correct_answer": f"Give the core justification from “{label}” (e.g., a bound, induction/invariant, or why a recurrence models the running time).",
            "explanation": "Connect the proof sketch or intuition the lecture gives to the problem being solved.",
            "difficulty": "hard",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
    ]


def _snippet_aware_questions(title: str, snippet: str, topic_tag: str, timestamp_start: float):
    """If we have real transcript text, quote it so the quiz is clearly lecture-specific."""
    label = (title or topic_tag or "this lecture").strip() or "this lecture"
    sn = (snippet or "").strip()
    if len(sn) < 40:
        return _title_grounded_pack(title, topic_tag, timestamp_start)
    quote = sn if len(sn) <= 160 else sn[:157] + "…"
    return [
        {
            "question": f'The lecture “{label}” includes this line: “{quote}”. In your own words, what idea is being explained?',
            "correct_answer": "A concise paraphrase that reuses the key technical terms from the quote and ties them to the lecture title.",
            "explanation": "Answers should reflect the quoted transcript, not unrelated algorithms.",
            "difficulty": "easy",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
        {
            "question": f'Using the same context (“{quote}”), what would change in the algorithm or analysis if an assumption from the lecture were violated?',
            "correct_answer": "Name one concrete change (e.g., worse complexity, incorrect output, or need for a different data structure) when the assumption breaks.",
            "explanation": "Shows you understand what the assumption is buying in the analysis.",
            "difficulty": "medium",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
        {
            "question": f'How does the segment containing “{quote}” relate to the overall solution strategy in “{label}”?',
            "correct_answer": "It is a local step that supports the global strategy (e.g., setup, recurrence, pruning, or combining partial results) for this lecture.",
            "explanation": "Connect local detail to the global algorithmic story in the video.",
            "difficulty": "hard",
            "topic_tag": topic_tag or "General",
            "timestamp_start": timestamp_start,
        },
    ]


def generate_questions_for_chunk(chunk_text, topic_tag, timestamp_start):
    # Topic-aware mock questions so the UI + tutor don't look identical.
    t = (topic_tag or "DAA").strip().lower()
    ctx = _combined_context(chunk_text, topic_tag)
    title = _extract_video_title(chunk_text)
    snippet = _transcript_snippet(chunk_text)

    # Lecture-specific combos (check before broad "graph" templates).
    if "branch" in ctx and "bound" in ctx:
        lab = title or "Branch and Bound"
        return [
            {
                "question": f'In “{lab}”, what is a live node vs a dead node in the state-space tree?',
                "correct_answer": "A live node can still expand into feasible children; a dead node cannot lead to a better complete solution (pruned or infeasible).",
                "explanation": "Branch-and-bound explores only promising branches using bounds.",
                "difficulty": "easy",
                "topic_tag": topic_tag or "Backtracking",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'How does branch-and-bound reduce search compared to brute force in “{lab}”?',
                "correct_answer": "It uses a lower/upper bound to prune subtrees that cannot beat the best complete solution found so far.",
                "explanation": "Pruning eliminates parts of the state space without enumerating all completions.",
                "difficulty": "medium",
                "topic_tag": topic_tag or "Backtracking",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'For TSP-style problems in “{lab}”, what does a typical cost bound at a partial tour represent?',
                "correct_answer": "A lower bound on the cheapest way to complete the partial tour into a full Hamiltonian cycle (often via reduced matrix / minimum outgoing edges).",
                "explanation": "Bounding estimates remaining cost to finish the tour.",
                "difficulty": "hard",
                "topic_tag": topic_tag or "Backtracking",
                "timestamp_start": timestamp_start,
            },
        ]

    if "traveling" in ctx or "travelling" in ctx or re.search(r"\btsp\b", ctx):
        lab = title or "Traveling Salesman Problem"
        return [
            {
                "question": f'In “{lab}”, what exactly are we minimizing, and over what set of solutions?',
                "correct_answer": "Minimize total tour cost over all Hamiltonian cycles that visit each city exactly once and return to the start.",
                "explanation": "TSP is an optimization over permutations/cycles, not arbitrary paths.",
                "difficulty": "easy",
                "topic_tag": topic_tag or "Graphs",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'Why is exhaustive enumeration expensive for TSP as n grows, in “{lab}”?',
                "correct_answer": "There are (n-1)!/2 distinct tours under common symmetry assumptions, which grows super-exponentially.",
                "explanation": "Search space size motivates branch-and-bound or heuristics.",
                "difficulty": "medium",
                "topic_tag": topic_tag or "Graphs",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'In “{lab}”, how does reduced-cost matrix reasoning support branching decisions?',
                "correct_answer": "Row/column reduction yields a lower bound; choosing an edge to branch on splits into include/exclude cases while updating the matrix.",
                "explanation": "This matches Abdul Bari–style TSP B&B on cost matrices.",
                "difficulty": "hard",
                "topic_tag": topic_tag or "Graphs",
                "timestamp_start": timestamp_start,
            },
        ]

    if (
        "asymptotic" in ctx
        or "big o" in ctx
        or "big-o" in ctx
        or "rate of growth" in ctx
        or ("notation" in ctx and ("property" in ctx or "theta" in ctx or "omega" in ctx))
    ):
        lab = title or "Asymptotic notations"
        return [
            {
                "question": f'In “{lab}”, what does f(n)=O(g(n)) mean in terms of constants c and n₀?',
                "correct_answer": "There exist positive constants c and n₀ such that 0 ≤ f(n) ≤ c·g(n) for all n ≥ n₀.",
                "explanation": "Big-O is an upper bound up to constant factors beyond some threshold.",
                "difficulty": "easy",
                "topic_tag": topic_tag or "Asymptotic Analysis",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'How does Θ notation differ from O notation in “{lab}”?',
                "correct_answer": "Θ gives a tight bound (both upper and lower within constant factors); O only guarantees an upper bound.",
                "explanation": "Θ(f) means f grows at the same rate as the bound; O(f) allows growing strictly slower too.",
                "difficulty": "medium",
                "topic_tag": topic_tag or "Asymptotic Analysis",
                "timestamp_start": timestamp_start,
            },
            {
                "question": f'State one standard property of asymptotic notation (transitivity, reflexivity, or symmetry rules) explained in “{lab}”.',
                "correct_answer": "Example: if f=O(g) and g=O(h) then f=O(h) (transitivity); or f=Θ(f) (reflexivity for Θ).",
                "explanation": "These properties let you combine and compare growth classes algebraically.",
                "difficulty": "hard",
                "topic_tag": topic_tag or "Asymptotic Analysis",
                "timestamp_start": timestamp_start,
            },
        ]

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

    # Never return the old identical "General" trio — ground in this video's title + transcript.
    if len(snippet) >= 40:
        return _snippet_aware_questions(title, snippet, topic_tag, timestamp_start)
    return _title_grounded_pack(title, topic_tag, timestamp_start)


def evaluate_student_answer(question, correct_answer, student_answer, topic_tag, language="en"):
    score = 7 if len(student_answer) > 20 else 3
    return {
        "score": score,
        "feedback": "Good attempt. Review the time complexity derivation more carefully.",
        "weak_concept": topic_tag,
        "is_partially_correct": score > 4,
    }


def translate_content(text, target_language):
    base = (text or "").strip()
    if not base:
        return {"translated": ""}

    # Lightweight deterministic fallback translations for demo mode.
    # This avoids fake placeholder strings in the quiz UI when USE_MOCK_LLM=True.
    phrase_map = {
        "hi": {
            "Explain the main algorithm idea for this topic.": "Is topic ke liye main algorithm ka core idea samjhaiye.",
            "What usually drives the time complexity here?": "Yahan time complexity ko aam taur par kaun si cheezein drive karti hain?",
            "Why does the approach produce correct results?": "Yeh approach sahi result kyon deta hai?",
        },
        "ta": {
            "Explain the main algorithm idea for this topic.": "Indha thalaippukku mukkiyamaana algorithm karuthai vilakkavum.",
            "What usually drives the time complexity here?": "Inge time complexity-ai saadharanamaaga enna thaane nirnayam seigiradhu?",
            "Why does the approach produce correct results?": "Indha murai sariyana mudivai eppadi tharugiradhu?",
        },
        "te": {
            "Explain the main algorithm idea for this topic.": "Ee topic kosam main algorithm idea ni vivarinchandi.",
            "What usually drives the time complexity here?": "Ikkada time complexity ni saadharananga emi prabhavitham chestundi?",
            "Why does the approach produce correct results?": "Ee paddhati enduku sariyana phalitalu istundi?",
        },
    }
    lang_map = phrase_map.get((target_language or "").lower(), {})
    translated = lang_map.get(base)
    if translated:
        return {"translated": translated}
    return {"translated": base}


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

