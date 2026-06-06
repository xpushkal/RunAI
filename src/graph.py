"""Graph-assisted features (the 'graphify' layer).

The graph does NOT rank — it derives three supporting signals that nudge the
hybrid scorer via a bounded `graph_boost` in [graph_boost.min, graph_boost.max]:

  1. peer_quality      — a FAISS kNN similarity graph over candidate embeddings.
                         Are your nearest-neighbour candidates on-role? Genuine
                         fits cluster with genuine fits; isolated keyword-stuffers
                         and honeypots cluster with off-role/odd profiles.
  2. skill_coherence   — a networkx skill co-occurrence graph. Do a candidate's
                         core-AI skills form a tight, frequently-co-occurring
                         cluster (coherent expertise) or a scattered stuff list?
  3. company_product   — a networkx candidate↔company bipartite graph. What
                         fraction of a company's people sit in product industries
                         (vs IT-services/consulting)? Propagates a product signal.

All of this is computed in the OFFLINE precompute step and cached to
`graph_features.parquet`; the ranking step only loads that table (cheap).

Built with networkx (in-memory, no external DB) + faiss-cpu for kNN — fully
reproducible inside the Stage-3 sandbox, no network.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from . import jd
from .config import load_config
from .features import title_fit
from .ingest import stream_candidates


def _lower(s) -> str:
    return s.lower() if isinstance(s, str) else ""


# ---------------------------------------------------------------------------
# component computations
# ---------------------------------------------------------------------------
def peer_quality(embeddings: np.ndarray, role_quality: np.ndarray, k: int,
                 min_sim: float) -> np.ndarray:
    """For each candidate, the similarity-weighted mean role-quality of its k
    nearest neighbours (excluding itself). Uses a FAISS inner-product index on
    L2-normalised embeddings (so inner product == cosine).
    """
    import faiss

    n, d = embeddings.shape
    index = faiss.IndexFlatIP(d)
    index.add(embeddings)
    sims, idx = index.search(embeddings, k + 1)  # +1 because the top hit is self

    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        neigh_sims, neigh_idx = sims[i], idx[i]
        mask = (neigh_idx != i) & (neigh_sims >= min_sim)
        if not mask.any():
            out[i] = role_quality[i]  # isolated node: fall back to its own quality
            continue
        w = neigh_sims[mask]
        out[i] = float(np.average(role_quality[neigh_idx[mask]], weights=w))
    return out


def skill_coherence(skill_lists: list[list[str]]) -> np.ndarray:
    """Build a networkx co-occurrence graph over core-AI skills, then score each
    candidate by how strongly their AI skills co-occur with each other across the
    pool (coherent expertise vs scattered keyword stuffing).
    """
    import networkx as nx
    from itertools import combinations

    g = nx.Graph()
    ai_lists = []
    for skills in skill_lists:
        ai = [s for s in skills if s in jd.CORE_AI_SKILLS]
        ai_lists.append(ai)
        for a, b in combinations(sorted(set(ai)), 2):
            if g.has_edge(a, b):
                g[a][b]["w"] += 1
            else:
                g.add_edge(a, b, w=1)

    # Normalise edge weights by the global max so coherence is in ~[0,1].
    max_w = max((data["w"] for _, _, data in g.edges(data=True)), default=1)

    out = np.zeros(len(ai_lists), dtype=np.float32)
    for i, ai in enumerate(ai_lists):
        uniq = sorted(set(ai))
        if len(uniq) < 2:
            out[i] = 0.5  # neutral: nothing to (in)cohere; rely on other signals
            continue
        pairs = list(combinations(uniq, 2))
        strength = sum(g[a][b]["w"] for a, b in pairs if g.has_edge(a, b))
        out[i] = min(1.0, (strength / len(pairs)) / max_w * 8.0)
    return out


def company_product_scores(companies: list[str], industries: list[str]) -> np.ndarray:
    """networkx candidate↔company bipartite graph: each company's product-ness is
    the fraction of its people in product industries; propagate back to candidates.
    """
    import networkx as nx

    g = nx.Graph()
    for i, comp in enumerate(companies):
        if not comp:
            continue
        is_prod = industries[i] in jd.PRODUCT_INDUSTRIES
        cnode = ("company", comp)
        g.add_node(cnode)
        g.add_edge(("cand", i), cnode, product=int(is_prod))

    comp_score: dict = {}
    for comp in {("company", c) for c in companies if c}:
        edges = g.edges(comp, data=True)
        vals = [e[2]["product"] for e in edges]
        comp_score[comp] = sum(vals) / len(vals) if vals else 0.5

    out = np.full(len(companies), 0.5, dtype=np.float32)
    for i, comp in enumerate(companies):
        if comp:
            out[i] = comp_score.get(("company", comp), 0.5)
    return out


# ---------------------------------------------------------------------------
# offline driver
# ---------------------------------------------------------------------------
def precompute_graph(cfg: dict) -> None:
    paths = cfg["paths"]
    ids = np.load(paths["candidate_ids"])
    embeddings = np.load(paths["embeddings"])

    role_quality = np.empty(len(ids), dtype=np.float32)
    skill_lists: list[list[str]] = []
    companies: list[str] = []
    industries: list[str] = []

    for i, c in enumerate(stream_candidates(paths["candidates"])):
        if i >= len(ids):
            break
        assert c["candidate_id"] == ids[i], "candidate order must match cached embeddings"
        role_quality[i] = title_fit(c)
        skill_lists.append([_lower(s.get("name", "")) for s in c.get("skills", [])])
        p = c.get("profile", {})
        companies.append(_lower(p.get("current_company", "")))
        industries.append(_lower(p.get("current_industry", "")))

    gcfg = cfg["graph"]
    print("Computing peer_quality (FAISS kNN) ...")
    peer = peer_quality(embeddings, role_quality, gcfg["knn_neighbors"], gcfg["knn_min_similarity"])
    print("Computing skill_coherence (networkx co-occurrence) ...")
    coher = skill_coherence(skill_lists)
    print("Computing company_product (networkx bipartite) ...")
    prod = company_product_scores(companies, industries)

    w = gcfg["boost_weights"]
    raw = w["peer"] * peer + w["skill_coherence"] * coher + w["company_product"] * prod
    bmin = cfg["scoring"]["graph_boost"]["min"]
    bmax = cfg["scoring"]["graph_boost"]["max"]
    boost = bmin + (bmax - bmin) * raw

    df = pd.DataFrame({
        "candidate_id": ids,
        "peer_quality": peer,
        "skill_coherence": coher,
        "company_product": prod,
        "graph_boost": boost.astype(np.float32),
    })
    Path(paths["artifacts_dir"]).mkdir(parents=True, exist_ok=True)
    df.to_parquet(paths["graph_features"], index=False)
    print(f"Saved graph features {df.shape} -> {paths['graph_features']}")
    print(f"graph_boost: min={boost.min():.3f} mean={boost.mean():.3f} max={boost.max():.3f}")


def load_graph_boosts(cfg: dict) -> dict | None:
    path = Path(cfg["paths"]["graph_features"])
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    return dict(zip(df["candidate_id"], df["graph_boost"].astype(float)))


if __name__ == "__main__":
    precompute_graph(load_config())
