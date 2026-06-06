# Redrob Intelligent Candidate Ranker

Ranks the **top 100** candidates from a **100,000-candidate pool** for the
*Senior AI Engineer — Founding Team* job description, with fact-grounded reasoning —
the submission for the Redrob *Intelligent Candidate Discovery & Ranking Challenge*.

The system is an **AI recruiter, not a keyword filter**: it reads *beyond* titles and
skill lists. Keyword-stuffers (off-role profiles with stuffed AI skills) and ~impossible
"honeypot" profiles are pushed out; plain-language fits (people who *built* ranking/recsys
systems at product companies but don't use the buzzwords) are surfaced.

> Full design docs are in [`Docs/`](Docs/) and the approved plan in [`plan.md`](plan.md).
> Per-milestone build history is in [`Docs/09_Build_Log.md`](Docs/09_Build_Log.md).

## Architecture (two phases)

```
OFFLINE precompute (one-time, ~15 min CPU, may exceed budget — allowed by spec)
  candidates.jsonl ──▶ embed 100k docs (bge-small)        ──▶ artifacts/embeddings.npy
                   └─▶ graph features (networkx + FAISS)   ──▶ artifacts/graph_features.parquet

ONLINE ranking step (~12s, CPU only, NO network — the reproduce command)
  rank.py ─▶ load cached vectors + graph (pure numpy)
          ─▶ score = relevance × experience × location × graph_boost
                     × behaviour × penalties × (0 if honeypot)
          ─▶ top 100 ─▶ fact-grounded reasoning ─▶ submission.csv
```

**Scoring** (all components interpretable, see [`config.yaml`](config.yaml)):
- `relevance = 0.55·semantic-similarity-to-JD + 0.45·structured-proxy`
  (structured-proxy = title-fit + career-evidence + corroborated-skill-trust)
- `× experience_fit` (soft 5–9y band) `× location_fit` (Noida/Pune/India or relocatable)
- `× graph_boost ∈ [0.85,1.15]` — kNN peer-quality + skill co-occurrence + company product-ness
- `× behaviour_modifier` — last-active recency, recruiter response, open-to-work, notice period
- `× penalties` — consulting-only, CV/speech-without-NLP, LangChain-only, title-chaser
- honeypots (logically-impossible profiles) are **hard-demoted to 0**

## Quickstart

Requires Python 3.11 and [uv](https://github.com/astral-sh/uv) (or plain `pip`).

```bash
# 1. environment
uv venv --python 3.11
uv pip install -r requirements.txt

# 2. one-time precompute (embeddings + graph features -> artifacts/)
python -m src.precompute        # embeds 100k candidate docs (CPU)
python -m src.graph             # builds graph features

# 3. produce the ranked submission (the reproduce command; ~12s, CPU, no network)
python rank.py --candidates ./India_runs_data_and_ai_challenge/candidates.jsonl \
               --out ./submission.csv

# 4. validate the output format
python India_runs_data_and_ai_challenge/validate_submission.py submission.csv
```

`rank.py` falls back to structured-only ranking if `artifacts/` is absent (so it always runs);
run the precompute steps for full semantic + graph quality.

> `candidates.jsonl` (487 MB) is **not** in the repo (gitignored) — download it from the
> hackathon bundle and place it under `India_runs_data_and_ai_challenge/`.

## Demo / sandbox

Interactive Streamlit app — upload a ≤100-candidate sample (or use the bundled one), see the
ranked shortlist + an interactive candidate↔JD-skill graph:

```bash
streamlit run app.py
```

Or via Docker (the embedding model is baked in for offline use):

```bash
docker build -t redrob-ranker .
docker run -p 8501:8501 redrob-ranker                 # demo at http://localhost:8501
docker run -v $PWD/India_runs_data_and_ai_challenge:/data redrob-ranker \
    python rank.py --candidates /data/candidates.jsonl --out /data/submission.csv
```

## Repo layout

```
rank.py                  # single entrypoint -> submission.csv (ranking step)
app.py                   # Streamlit sandbox/demo
config.yaml              # all tunable weights / paths
src/
  ingest.py  jd.py  features.py     # ingest, JD lexicons, features + honeypot/penalty rules
  embeddings.py  precompute.py      # offline embedding
  graph.py                          # graph-assisted features (networkx + FAISS)
  score.py  reasoning.py  pipeline.py
scripts/explore.py       # M1 data exploration
Docs/                    # PRD, data dictionary, eval, traps, architecture, build log
```

## Compute constraints (met)

| Constraint | Limit | This system |
|------------|-------|-------------|
| Ranking runtime | ≤ 5 min | ~12 s |
| Memory | ≤ 16 GB | well under |
| Compute | CPU only | CPU only |
| Network during ranking | none | none (vectors + model cached) |

## AI tools

Built with Claude (Claude Code) for architecture, implementation, and review. No candidate data
was sent to any hosted LLM; the ranking step is fully offline. See `submission_metadata.yaml`.
