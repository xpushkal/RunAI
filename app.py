"""Streamlit sandbox/demo for the Redrob candidate ranker.

Upload a small candidate sample (≤100, JSONL or JSON array) — or use the bundled
sample — and the app ranks it end-to-end for the 'Senior AI Engineer' JD, showing
the ranked shortlist with reasoning plus an interactive graph of how the top
candidates connect to the JD's key skills.

Run:  streamlit run app.py
Compute: CPU only, embeds the sample at runtime (fine for ≤100 candidates).
"""
from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from src import jd
from src.config import load_config
from src.pipeline import rank_records

st.set_page_config(page_title="Redrob Candidate Ranker", layout="wide")

SAMPLE_PATH = "India_runs_data_and_ai_challenge/sample_candidates.json"


@st.cache_resource
def _load_model(model_name: str, max_seq: int):
    from src import embeddings as emb
    m = emb.load_model(model_name)
    m.max_seq_length = max_seq
    return m


def _parse_upload(raw: bytes) -> list[dict]:
    text = raw.decode("utf-8")
    text_strip = text.lstrip()
    if text_strip.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _build_graph_html(top: list[dict], records_by_id: dict, k: int = 10) -> str:
    """Interactive candidate↔skill graph for the top-k picks (pyvis)."""
    from pyvis.network import Network

    net = Network(height="560px", width="100%", bgcolor="#111", font_color="white", notebook=False)
    net.barnes_hut(gravity=-8000, spring_length=120)

    jd_skills = {s.lower() for s in jd.VECTOR_DB_SKILLS | jd.CORE_AI_SKILLS}
    for f in top[:k]:
        cid = f["candidate_id"]
        rank = f["rank"]
        c = records_by_id[cid]
        title = c["profile"]["current_title"]
        net.add_node(cid, label=f"#{rank} {title}", color="#7c5cff", shape="dot", size=22,
                     title=f["reasoning"])
        for s in c.get("skills", []):
            name = s.get("name", "")
            if name.lower() in jd_skills:
                net.add_node(name, label=name, color="#22c55e", shape="box", size=14)
                net.add_edge(cid, name, color="#444")
    return net.generate_html()


def main():
    cfg = load_config()
    st.title("🔎 Redrob Intelligent Candidate Ranker")
    st.caption("Ranks candidates for the **Senior AI Engineer — Founding Team** JD. "
               "Hybrid scorer: semantic relevance × role/skill gates × behavioural signals × "
               "graph boost, with honeypot & keyword-stuffer defenses.")

    with st.sidebar:
        st.header("Input")
        up = st.file_uploader("Candidate sample (.jsonl or .json, ≤100)", type=["jsonl", "json"])
        use_sample = st.checkbox("Use bundled sample_candidates.json", value=up is None)
        top_n = st.slider("Show top-N", 5, 50, 15)
        use_emb = st.checkbox("Semantic embeddings (slower, better)", value=True)
        run = st.button("Rank candidates", type="primary")

    if not run:
        st.info("Upload a sample or tick the bundled sample, then click **Rank candidates**.")
        return

    if up is not None:
        records = _parse_upload(up.read())
    elif use_sample:
        with open(SAMPLE_PATH) as fh:
            records = json.load(fh)
    else:
        st.warning("Provide an input.")
        return

    records = records[:100]
    records_by_id = {c["candidate_id"]: c for c in records}
    st.success(f"Loaded {len(records)} candidates.")

    model = None
    if use_emb:
        with st.spinner("Loading embedding model + encoding sample…"):
            model = _load_model(cfg["embedding"]["model_name"], cfg["embedding"]["max_seq_length"])

    with st.spinner("Ranking…"):
        top = rank_records(records, cfg, model=model, use_embeddings=use_emb)

    rows = [{
        "rank": f["rank"], "candidate_id": f["candidate_id"], "score": f["score"],
        "title": f["facts"]["current_title"], "company": f["facts"]["current_company"],
        "yoe": f["facts"]["years_of_experience"], "reasoning": f["reasoning"],
    } for f in top[:top_n]]
    df = pd.DataFrame(rows)

    st.subheader("Ranked shortlist")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button("Download full ranking (CSV)",
                       pd.DataFrame([{"candidate_id": f["candidate_id"], "rank": f["rank"],
                                      "score": f["score"], "reasoning": f["reasoning"]}
                                     for f in top]).to_csv(index=False),
                       file_name="submission_sample.csv", mime="text/csv")

    st.subheader("Candidate ↔ JD-skill graph (top picks)")
    st.caption("Purple = candidate (hover for reasoning); green = a JD-relevant skill they hold.")
    try:
        html = _build_graph_html(top, records_by_id, k=min(top_n, 12))
        st.components.v1.html(html, height=580)
    except Exception as e:  # pragma: no cover - viz is best-effort
        st.warning(f"Graph view unavailable: {e}")


if __name__ == "__main__":
    main()
