"""Scoring & ranking.

Combines the structured components from src/features.py into a single score,
applies behavioral/penalty/honeypot modifiers, then ranks.

At M2 there is no semantic embedding term yet, so `relevance` is a structured
proxy (title + career evidence + skill trust). From M3, an embedding similarity
is blended into `relevance` (see `relevance_from_features`).

Final score:
    relevance = 0.45*title_fit + 0.40*career_fit + 0.15*skill_trust   (M2 proxy)
    role_gate = floor + (1-floor) * max(title_fit, career_fit)
    base      = relevance * role_gate * experience_fit * location_fit * graph_boost
    final     = base * penalty * behavior_mod * (0 if honeypot else 1)

`role_gate` is a hard multiplier that keeps off-role keyword-stuffers (high
semantic embed_sim from an AI-flavoured summary, but no title/career evidence of
relevant work) from floating up on the additive embedding term alone. It uses
`max(title_fit, career_fit)` so genuine plain-language "Tier-5" fits — modest
title but career history that shows they *built* relevant systems — pass the gate.
skill_trust is deliberately NOT a hard gate: real plain-language fits often list
no AI skills, so gating on it would bury them (it stays a soft term in relevance).
Ranking: sort by final desc, tie-break candidate_id asc, take top N, assign ranks.
Emitted score is rescaled into [score_min, score_max] so it stays differentiated
and non-increasing by rank (satisfies the validator).
"""
from __future__ import annotations


def structured_proxy(feat: dict, cfg: dict) -> float:
    """Structured relevance proxy (the M2 signal): title + career + skill trust."""
    w = cfg["scoring"]["structured_proxy"]
    return (
        w["title"] * feat["title_fit"]
        + w["career"] * feat["career_fit"]
        + w["skill"] * feat["skill_trust"]
    )


def relevance(feat: dict, cfg: dict) -> float:
    """Blend semantic embedding similarity with the structured proxy.

    `embed_sim` (rescaled cosine to the JD query, in [0,1]) is attached by rank.py
    when cached embeddings are available; if absent we fall back to structured-only.
    """
    proxy = structured_proxy(feat, cfg)
    embed_sim = feat.get("embed_sim")
    if embed_sim is None:
        return proxy
    blend = cfg["scoring"]["relevance_blend"]
    return blend["embed"] * embed_sim + blend["structured"] * proxy


def role_gate(feat: dict, cfg: dict) -> float:
    """Hard role-fit multiplier in [floor, 1]. Off-role profiles (no title or
    career evidence of relevant work) are gated down so a high semantic embed_sim
    alone can't surface them; plain-language fits pass via their career evidence.
    """
    floor = cfg["scoring"]["role_gate"]["floor"]
    role_quality = max(feat["title_fit"], feat["career_fit"])
    return floor + (1.0 - floor) * role_quality


def final_score(feat: dict, cfg: dict, graph_boost: float = 1.0) -> float:
    rel = relevance(feat, cfg)
    base = rel * role_gate(feat, cfg) * feat["experience_fit"] * feat["location_fit"] * graph_boost
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
