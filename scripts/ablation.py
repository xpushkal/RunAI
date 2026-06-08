#!/usr/bin/env python3
"""Ablation + robustness analysis for the ranker.

Computes features once, then re-scores the whole pool under (a) each scoring
layer disabled and (b) perturbed weights, reporting how the top-K changes and
whether traps (honeypots / off-role keyword-stuffers) leak back in.

Usage:  python scripts/ablation.py
"""
from __future__ import annotations

import copy
import json
import sys

sys.path.insert(0, ".")
from src import embeddings as emb               # noqa: E402
from src import features as feat_mod            # noqa: E402
from src import graph as graph_mod              # noqa: E402
from src import jd                              # noqa: E402
from src.config import load_config              # noqa: E402
from src.ingest import stream_candidates        # noqa: E402
from src.score import structured_proxy          # noqa: E402

OFF_ROLE_OK = ("engineer", "developer", "scientist", "ai", "ml", "research",
               "analyst", "architect", "specialist")


def is_off_role(title: str) -> bool:
    t = title.lower()
    return not any(k in t for k in OFF_ROLE_OK)


def load_features(cfg):
    import numpy as np
    paths = cfg["paths"]
    vecs = np.load(paths["embeddings"]); ids = np.load(paths["candidate_ids"])
    jd_vec = np.load(f"{paths['artifacts_dir']}/jd_embedding.npy")
    sim = emb.rescale_similarity(emb.cosine_to_query(vecs, jd_vec),
                                 cfg["scoring"]["embed_sim_floor"], cfg["scoring"]["embed_sim_ceil"])
    sims = {cid: float(s) for cid, s in zip(ids, sim)}
    boosts = graph_mod.load_graph_boosts(cfg)
    feats = []
    for c in stream_candidates(paths["candidates"]):
        f = feat_mod.extract(c, cfg)
        f["embed_sim"] = sims.get(f["candidate_id"])
        f["graph_boost"] = boosts.get(f["candidate_id"], 1.0)
        feats.append(f)
    return feats


def raw_score(feat, cfg, *, use_embed=True, use_graph=True, use_behavior=True,
              use_penalty=True, use_honeypot=True, use_role_gate=True, embed_only=False):
    proxy = structured_proxy(feat, cfg)
    es = feat.get("embed_sim")
    if embed_only and es is not None:
        rel = es
    elif use_embed and es is not None:
        b = cfg["scoring"]["relevance_blend"]
        rel = b["embed"] * es + b["structured"] * proxy
    else:
        rel = proxy
    gb = feat.get("graph_boost", 1.0) if use_graph else 1.0
    if use_role_gate:
        floor = cfg["scoring"]["role_gate"]["floor"]
        rg = floor + (1.0 - floor) * max(feat["title_fit"], feat["career_fit"])
    else:
        rg = 1.0
    base = rel * rg * feat["experience_fit"] * feat["location_fit"] * gb
    s = base * (feat["penalty"] if use_penalty else 1.0) * (feat["behavior_mod"] if use_behavior else 1.0)
    if use_honeypot and feat["honeypot_score"] >= cfg["honeypot"]["score_threshold"]:
        s = 0.0
    return s


def topk_ids(feats, cfg, k=100, **kw):
    scored = [(raw_score(f, cfg, **kw), f["candidate_id"]) for f in feats]
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [cid for _, cid in scored[:k]]


def trap_counts(feats, ids):
    by_id = {f["candidate_id"]: f for f in feats}
    hp = sum(1 for cid in ids if by_id[cid]["honeypot_flags"])
    off = sum(1 for cid in ids if is_off_role(by_id[cid]["facts"]["current_title"]))
    return hp, off


def overlap(a, b, k):
    return len(set(a[:k]) & set(b[:k])) / k


def main():
    cfg = load_config()
    print("Loading features (one pass over 100k)…")
    feats = load_features(cfg)

    full = topk_ids(feats, cfg)
    print("\n=== ABLATION: disable one layer at a time (overlap vs full) ===")
    print(f"{'variant':<22}{'top10':>8}{'top50':>8}{'top100':>8}{'honeypots':>11}{'off-role':>10}")
    variants = {
        "FULL (reference)": {},
        "structured-only": {"use_embed": False},
        "embeddings-only-rel": {"embed_only": True},
        "no role_gate": {"use_role_gate": False},
        "no graph_boost": {"use_graph": False},
        "no behavior_mod": {"use_behavior": False},
        "no penalties": {"use_penalty": False},
        "no honeypot demote": {"use_honeypot": False},
    }
    for name, kw in variants.items():
        ids = topk_ids(feats, cfg, **kw)
        hp, off = trap_counts(feats, ids)
        if name.startswith("FULL"):
            print(f"{name:<22}{'1.00':>8}{'1.00':>8}{'1.00':>8}{hp:>11}{off:>10}")
        else:
            print(f"{name:<22}{overlap(ids,full,10):>8.2f}{overlap(ids,full,50):>8.2f}"
                  f"{overlap(ids,full,100):>8.2f}{hp:>11}{off:>10}")

    print("\n=== ROBUSTNESS: perturb relevance blend (top-50 overlap vs full) ===")
    for embed_w in (0.40, 0.55, 0.70):
        c2 = copy.deepcopy(cfg)
        c2["scoring"]["relevance_blend"] = {"embed": embed_w, "structured": round(1 - embed_w, 2)}
        ids = topk_ids(feats, c2)
        hp, off = trap_counts(feats, ids)
        tag = "  (default)" if embed_w == 0.55 else ""
        print(f"  embed={embed_w:.2f}/struct={1-embed_w:.2f}: top10={overlap(ids,full,10):.2f} "
              f"top50={overlap(ids,full,50):.2f} top100={overlap(ids,full,100):.2f} "
              f"honeypots={hp} off-role={off}{tag}")


if __name__ == "__main__":
    main()
