"""Embedding helpers shared by precompute (offline) and ranking (online).

The model is only ever loaded during the *offline* precompute step. The ranking
step loads cached vectors and does pure-numpy similarity, so it needs no torch
and no network — satisfying the compute constraints.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def load_model(model_name: str):
    """Load a sentence-transformers model on CPU (offline-precompute only)."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cpu")
    return model


def encode_texts(model, texts: list[str], batch_size: int, normalize: bool) -> np.ndarray:
    vecs = model.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
        show_progress_bar=True,
    )
    return vecs.astype(np.float32)


def cosine_to_query(embeddings: np.ndarray, query_vec: np.ndarray) -> np.ndarray:
    """Cosine similarity of every row to a single query vector.

    Assumes both are L2-normalized (we normalize at encode time), so cosine is
    just a dot product.
    """
    q = query_vec.reshape(-1).astype(np.float32)
    return embeddings @ q


def rescale_similarity(sim: np.ndarray, floor: float, ceil: float) -> np.ndarray:
    """Map raw cosine in [floor, ceil] -> [0, 1], clipped."""
    out = (sim - floor) / max(1e-6, (ceil - floor))
    return np.clip(out, 0.0, 1.0)


def artifacts_exist(cfg: dict) -> bool:
    p = cfg["paths"]
    return all(Path(p[k]).exists() for k in ("embeddings", "candidate_ids")) \
        and Path(p["artifacts_dir"], "jd_embedding.npy").exists()
