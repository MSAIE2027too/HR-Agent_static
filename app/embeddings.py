"""Embedding provider interface. MiniLM when installed, labeled fallback otherwise.

The fallback is a deterministic hashed bag-of-words vector. It keeps the full
pipeline runnable CPU-only with zero downloads; retrieval quality is lower and
the active provider is always reported (see vector_store.build_index return and
evaluation output). Eval numbers are honest about which provider ran.
"""
from __future__ import annotations

import hashlib
import math
import re

DIM = 384
NAME_MINILM = "all-MiniLM-L6-v2"
NAME_FALLBACK = "hash-fallback-384"


def _normalize(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / n for x in vec]


class MiniLMProvider:
    name = NAME_MINILM

    def __init__(self) -> None:
        # Auth, if ever needed for gated models, comes from the environment
        # (HF_TOKEN / HUGGINGFACE_HUB_TOKEN) read by huggingface_hub itself.
        # This module never reads, logs, or transmits key material.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(NAME_MINILM)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True).tolist()
        return [list(map(float, v)) for v in vecs]


class HashFallbackProvider:
    name = NAME_FALLBACK

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * DIM
            for tok in re.findall(r"[a-z0-9]+", text.lower()):
                vec[int(hashlib.sha256(tok.encode()).hexdigest(), 16) % DIM] += 1.0
            out.append(_normalize(vec))
        return out


def get_provider():
    try:
        provider = MiniLMProvider()
        return provider
    except Exception:
        return HashFallbackProvider()
