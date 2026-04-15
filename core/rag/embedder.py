from __future__ import annotations

import logging
import numpy as np
import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from config import OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL

logger = logging.getLogger(__name__)

EMBED_URL = f"{OLLAMA_BASE_URL}/api/embeddings"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
def _embed_single(text: str) -> list[float]:
    resp = requests.post(
        EMBED_URL,
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def embed_texts(texts: list[str]) -> np.ndarray:
    if not texts:
        return np.array([])

    embeddings = []
    for i, text in enumerate(texts):
        vec = _embed_single(text[:2000])    # truncate very long texts
        embeddings.append(vec)
        if (i + 1) % 5 == 0:
            logger.info("Embedded %d/%d texts", i + 1, len(texts))

    result = np.array(embeddings, dtype=np.float32)
    logger.info("Embedding complete: shape %s", result.shape)
    return result


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def top_k_indices(
    query_vec: np.ndarray,
    corpus_vecs: np.ndarray,
    k: int,
) -> list[int]:
    scores = [cosine_similarity(query_vec, corpus_vecs[i])
              for i in range(len(corpus_vecs))]
    return sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
