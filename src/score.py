"""Scoring & ranking.

Combines the structured components from src/features.py into a single score,
applies behavioral/penalty/honeypot modifiers, then ranks.

At M2 there is no semantic embedding term yet, so `relevance` is a structured
proxy (title + career evidence + skill trust). From M3, an embedding similarity
is blended into `relevance` (see `relevance_from_features`).

Final score:
    relevance = 0.45*title_fit + 0.40*career_fit + 0.15*skill_trust   (M2 proxy)
    base      = relevance * experience_fit * location_fit * graph_boost
    final     = base * penalty * behavior_mod * (0 if honeypot else 1)
Ranking: sort by final desc, tie-break candidate_id asc, take top N, assign ranks.
Emitted score is rescaled into [score_min, score_max] so it stays differentiated
and non-increasing by rank (satisfies the validator).
"""
from __future__ import annotations


def relevance_from_features(feat: dict) -> float:
    """Structured relevance proxy (M2). Blended with embedding sim in M3."""
    return (
        0.45 * feat["title_fit"]
        + 0.40 * feat["career_fit"]
        + 0.15 * feat["skill_trust"]
    )


def final_score(feat: dict, cfg: dict, graph_boost: float = 1.0) -> float:
    relevance = feat.get("relevance")
    if relevance is None:
        relevance = relevance_from_features(feat)

    base = relevance * feat["experience_fit"] * feat["location_fit"] * graph_boost
    score = base * feat["penalty"] * feat["behavior_mod"]

    if cfg["honeypot"]["hard_demote"] and feat["honeypot_score"] >= cfg["honeypot"]["score_threshold"]:
        score = 0.0
    return score


def rank_candidates(features: list[dict], cfg: dict) -> list[dict]:
    """Score all candidates, sort, take top N, assign ranks and emitted scores.

    Returns the top-N feature dicts, each augmented with `raw_score`, `rank`,
    and `score` (the rescaled, non-increasing emitted score).
    """
    for feat in features:
        feat["raw_score"] = final_score(feat, cfg, feat.get("graph_boost", 1.0))

    # Sort by raw score desc, then candidate_id asc (the validator's required tie-break).
    features.sort(key=lambda f: (-f["raw_score"], f["candidate_id"]))

    top_n = cfg["output"]["top_n"]
    top = features[:top_n]

    # Rescale raw scores into [score_min, score_max], strictly by position so the
    # emitted score column is guaranteed non-increasing with rank.
    smin = cfg["output"]["score_min"]
    smax = cfg["output"]["score_max"]
    n = len(top)
    for i, feat in enumerate(top):
        feat["rank"] = i + 1
        if n > 1:
            feat["score"] = round(smax - (smax - smin) * i / (n - 1), 4)
        else:
            feat["score"] = round(smax, 4)
    return top
