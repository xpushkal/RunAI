#!/usr/bin/env python3
"""Redrob candidate ranker — single entrypoint that produces the submission CSV.

    python rank.py --candidates ./India_runs_data_and_ai_challenge/candidates.jsonl \
                   --out ./submission.csv

M2: structured-only ranking (no embeddings). The precompute/light-rank split and
semantic relevance arrive in M3. Runs CPU-only, no network.
"""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from src import embeddings as emb
from src import features as feat_mod
from src import reasoning as reasoning_mod
from src import score as score_mod
from src.config import load_config
from src.ingest import stream_candidates

HEADER = ["candidate_id", "rank", "score", "reasoning"]


def _embed_sims(cfg: dict) -> dict | None:
    """Load cached embeddings and return {candidate_id: rescaled_sim} or None.

    Pure numpy — no torch, no network. If artifacts are missing we return None
    and the ranker falls back to the structured-only relevance (M2 behavior).
    """
    if not emb.artifacts_exist(cfg):
        return None
    import numpy as np

    paths = cfg["paths"]
    vecs = np.load(paths["embeddings"])
    ids = np.load(paths["candidate_ids"])
    jd_vec = np.load(Path(paths["artifacts_dir"], "jd_embedding.npy"))
    sim = emb.cosine_to_query(vecs, jd_vec)
    sim = emb.rescale_similarity(
        sim, cfg["scoring"]["embed_sim_floor"], cfg["scoring"]["embed_sim_ceil"]
    )
    return {cid: float(s) for cid, s in zip(ids, sim)}


def build(candidates_path: str, cfg: dict) -> list[dict]:
    """Extract features for every candidate, attach embedding sim, then rank to top-N."""
    sims = _embed_sims(cfg)
    if sims is None:
        print("WARNING: no cached embeddings found — using structured-only relevance "
              "(run `python -m src.precompute` for semantic ranking).")

    features = []
    for c in stream_candidates(candidates_path):
        feat = feat_mod.extract(c, cfg)
        if sims is not None:
            feat["embed_sim"] = sims.get(feat["candidate_id"])
        features.append(feat)

    top = score_mod.rank_candidates(features, cfg)
    for f in top:
        f["reasoning"] = reasoning_mod.generate(f)
    return top


def write_csv(top: list[dict], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        for f in top:
            writer.writerow([f["candidate_id"], f["rank"], f"{f['score']:.4f}", f["reasoning"]])


def main() -> None:
    ap = argparse.ArgumentParser(description="Rank candidates for the Redrob JD.")
    ap.add_argument("--candidates", default=None, help="Path to candidates.jsonl")
    ap.add_argument("--out", default=None, help="Output CSV path")
    ap.add_argument("--config", default=None, help="Path to config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    candidates_path = args.candidates or cfg["paths"]["candidates"]
    out_path = args.out or cfg["paths"]["output"]

    t0 = time.time()
    top = build(candidates_path, cfg)
    write_csv(top, out_path)
    dt = time.time() - t0
    print(f"Wrote {len(top)} rows to {out_path} in {dt:.1f}s")


if __name__ == "__main__":
    main()
