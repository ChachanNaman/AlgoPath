from __future__ import annotations

import hashlib
import os
import numpy as np

# We lazy-load sentence-transformers to avoid worker startup crashes on some macOS
# forked multiprocessing setups. In mock mode, we use deterministic lightweight
# embeddings instead (good enough for demo ranking/scoring).
_model = None
_EMBED_DIM_FALLBACK = 128


def _use_lightweight_embeddings() -> bool:
    return os.getenv("USE_MOCK_LLM", "True").lower() == "true"


def _simple_embedding(text: str, dim: int = _EMBED_DIM_FALLBACK) -> list[float]:
    """
    Deterministic fallback embedding with no heavy dependencies.
    Converts SHA-256 digest bytes to a normalized float vector.
    """
    text = text or ""
    out = []
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    # Expand deterministically by hashing prior digest with index.
    current = seed
    while len(out) < dim:
        current = hashlib.sha256(current + text.encode("utf-8") + bytes([len(out) % 251])).digest()
        # Map first 8 bytes chunks into [-1, 1]
        for i in range(0, len(current), 4):
            if len(out) >= dim:
                break
            chunk = current[i : i + 4]
            if len(chunk) < 4:
                break
            val = int.from_bytes(chunk, "big", signed=False)
            out.append((val / 0xFFFFFFFF) * 2.0 - 1.0)
    v = np.array(out, dtype=np.float32)
    norm = float(np.linalg.norm(v)) or 1e-12
    return (v / norm).tolist()


def _get_model():
    global _model
    if _model is not None:
        return _model
    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_embedding(text: str) -> list[float]:
    if _use_lightweight_embeddings():
        return _simple_embedding(text)
    try:
        model = _get_model()
        return model.encode(text).tolist()
    except Exception:
        # Fallback in case model load/runtime fails.
        return _simple_embedding(text)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    # Handle mixed-dimension vectors safely by truncating to common length.
    n = min(len(vec1), len(vec2))
    if n == 0:
        return 0.0
    v1, v2 = np.array(vec1[:n]), np.array(vec2[:n])
    denom = (np.linalg.norm(v1) * np.linalg.norm(v2)) or 1e-12
    return float(np.dot(v1, v2) / denom)


def find_top_chunks(query: str, transcript_chunks: list[dict], top_k: int = 3) -> list[dict]:
    query_embedding = get_embedding(query)
    scored: list[tuple[float, dict]] = []
    for chunk in transcript_chunks:
        if "embedding" in chunk:
            sim = cosine_similarity(query_embedding, chunk["embedding"])
            scored.append((sim, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


# Quick manual test:
# - Run in a Python shell:
#   from app.services.embedding_service import get_embedding, cosine_similarity
#   cosine_similarity(get_embedding("test1"), get_embedding("test2"))

