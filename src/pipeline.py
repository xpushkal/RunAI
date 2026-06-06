"""In-memory ranking pipeline for a small candidate sample (the Streamlit demo).

Unlike `rank.py` (which loads cached artifacts for the full 100k pool), this
embeds the uploaded sample at runtime — fine for ≤100 candidates — and computes
graph features on the sample directly. Returns the ranked top-N feature dicts.
"""
from __future__ import annotations

from . import embeddings as emb
from . import features as feat_mod
from . import graph as graph_mod
from . import jd
from . import reasoning as reasoning_mod
from . import score as score_mod
from .ingest import candidate_document


def rank_records(records: list[dict], cfg: dict, model=None, use_embeddings: bool = True) -> list[dict]:
    """Rank candidate dicts end-to-end in memory.

    If `use_embeddings`, encodes the sample (and the JD) with `model` (loaded if
    None) and blends semantic similarity; otherwise falls back to structured-only.
    """
    features = [feat_mod.extract(c, cfg) for c in records]

    if use_embeddings:
        if model is None:
            model = emb.load_model(cfg["embedding"]["model_name"])
            model.max_seq_length = cfg["embedding"]["max_seq_length"]
        docs = [candidate_document(c) for c in records]
        norm = cfg["embedding"]["normalize"]
        vecs = emb.encode_texts(model, docs, cfg["embedding"]["batch_size"], norm)
        jd_vec = emb.encode_texts(model, [jd.JD_QUERY_TEXT], 1, norm)[0]
        sims = emb.rescale_similarity(
            emb.cosine_to_query(vecs, jd_vec),
            cfg["scoring"]["embed_sim_floor"], cfg["scoring"]["embed_sim_ceil"],
        )
        # Graph features on the sample.
        rq, sl, comp, ind = graph_mod._collect_inputs(records)
        peer, coher, prod, boost = graph_mod.compute_boosts(vecs, rq, sl, comp, ind, cfg)
        for i, f in enumerate(features):
            f["embed_sim"] = float(sims[i])
            f["graph_boost"] = float(boost[i])
            f["graph_components"] = {
                "peer_quality": float(peer[i]),
                "skill_coherence": float(coher[i]),
                "company_product": float(prod[i]),
            }

    top = score_mod.rank_candidates(features, cfg)
    for f in top:
        f["reasoning"] = reasoning_mod.generate(f)
    return top
