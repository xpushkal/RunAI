"""Offline precompute step — embeds the candidate pool and the JD query.

This may exceed the 5-minute ranking budget (the spec allows unbounded
pre-computation). It writes cached artifacts that the light ranking step loads:

    artifacts/embeddings.npy      (N x D float32, L2-normalized)
    artifacts/candidate_ids.npy   (N,) candidate_id strings, aligned to rows
    artifacts/jd_embedding.npy    (D,) the JD query vector

Usage:
    python -m src.precompute            # uses config.yaml paths
    python -m src.precompute --limit 2000   # quick smoke test on a subset
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from . import embeddings as emb
from . import jd
from .config import load_config
from .ingest import candidate_document, stream_candidates


def run(cfg: dict, limit: int | None = None) -> None:
    paths = cfg["paths"]
    art_dir = Path(paths["artifacts_dir"])
    art_dir.mkdir(parents=True, exist_ok=True)

    ids: list[str] = []
    docs: list[str] = []
    for i, c in enumerate(stream_candidates(paths["candidates"])):
        if limit and i >= limit:
            break
        ids.append(c["candidate_id"])
        docs.append(candidate_document(c))
    print(f"Loaded {len(docs)} candidate documents.")

    ecfg = cfg["embedding"]
    model = emb.load_model(ecfg["model_name"])
    model.max_seq_length = ecfg["max_seq_length"]

    print(f"Embedding with {ecfg['model_name']} ...")
    vecs = emb.encode_texts(model, docs, ecfg["batch_size"], ecfg["normalize"])
    jd_vec = emb.encode_texts(model, [jd.JD_QUERY_TEXT], 1, ecfg["normalize"])[0]

    np.save(paths["embeddings"], vecs)
    np.save(paths["candidate_ids"], np.array(ids))
    np.save(art_dir / "jd_embedding.npy", jd_vec)
    print(f"Saved embeddings {vecs.shape} -> {paths['embeddings']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Precompute candidate embeddings.")
    ap.add_argument("--config", default=None)
    ap.add_argument("--limit", type=int, default=None, help="Embed only the first N (smoke test)")
    args = ap.parse_args()
    run(load_config(args.config), args.limit)


if __name__ == "__main__":
    main()
