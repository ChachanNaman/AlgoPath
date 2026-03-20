from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


# Downloads once (~80MB) then runs locally.
model = SentenceTransformer("all-MiniLM-L6-v2")


def get_embedding(text: str) -> list[float]:
    return model.encode(text).tolist()


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    v1, v2 = np.array(vec1), np.array(vec2)
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

