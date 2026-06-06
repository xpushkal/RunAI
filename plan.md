# Implementation Plan — Redrob Candidate Ranking System

## Context

We're building the submission for the **Redrob Intelligent Candidate Discovery & Ranking
Challenge**: rank the **top 100** candidates out of a **100,000-candidate pool**
(`candidates.jsonl`, 487 MB) against one JD ("Senior AI Engineer — Founding Team"), output a
spec-compliant CSV with fact-grounded reasoning, and ship a reproducible repo + Streamlit demo.

The dataset is adversarial (keyword stuffers, ~80 honeypots, plain-language strong fits) and the
ranking step is constrained: **≤5 min, ≤16 GB RAM, CPU-only, no network**. Full requirements are
already documented in [`Docs/`](../../Downloads/PROJECTSS/RunAI/Docs/) (PRD, data dictionary,
submission requirements, evaluation, traps, architecture).

This plan turns those docs into a concrete, buildable system. Key design decisions (confirmed
with the user):
- **Graph = assisted features**, not the core ranker. The hybrid scorer ranks; the graph derives
  supporting features (skill co-occurrence, company/prestige propagation, candidate similarity).
- **In-memory graph** via `networkx` — no external DB, fully reproducible in the Docker sandbox,
  respects "no network".
- **Precompute offline, light ranking** — embeddings/graph/features built offline and cached;
  the 5-min ranking step just loads artifacts, scores, sorts, writes CSV.
- **Streamlit app with graph visualization** as the mandatory sandbox/demo.

> Note on the plan file: this canonical plan lives here. On execution we'll also save a copy into
> the repo as **`plan.md`** (project root) and link it from `Docs/00_INDEX.md`.

---

## Architecture: two-phase flow

```
┌──────────────────── PHASE A — OFFLINE PRECOMPUTE (unbounded, documented) ─────────────────────┐
│ candidates.jsonl (100k)                                                                        │
│   └─ ingest (stream) ─► clean/normalize ─► build candidate "documents"                         │
│         ├─► EMBED (local CPU sentence-transformer) ──────────► embeddings.npy (float32)        │
│         ├─► STRUCTURED FEATURES (title/role, skill-trust, exp, behavior) ─► features.parquet   │
│         ├─► HONEYPOT FLAGS (logical-consistency checks) ─────► honeypot.parquet                │
│         └─► GRAPH BUILD (networkx) ─────────────────────────► graph.pkl + graph_features.parquet│
│                nodes: candidates, skills, companies, titles, industries                        │
│                edges: has_skill, worked_at, has_title, in_industry, kNN-similar (from FAISS)   │
│                graph features: skill co-occurrence centrality, company-prestige propagation,   │
│                                peer-similarity (does candidate cluster with genuine fits?)     │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │ artifacts/  (gitignored)
                                              ▼
┌──────────────────── PHASE B — RANKING STEP (≤5 min, ≤16 GB, CPU, no net) ─────────────────────┐
│ rank.py --candidates candidates.jsonl --out submission.csv                                     │
│   1. load artifacts (embeddings, features, honeypot flags, graph features)                     │
│   2. encode JD ─► JD query vector + structured requirement checks                              │
│   3. score each candidate (vectorized): relevance × role_gate × skill_trust × graph_boost      │
│                                          × penalties × behavior_mod × (0 if honeypot)          │
│   4. sort by score desc, tie-break candidate_id asc ─► top 100 ─► assign ranks 1..100          │
│   5. generate reasoning (deterministic, fact-grounded, varied)                                 │
│   6. write CSV ─► run validate_submission.py                                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
                                              │
                                              ▼
                         Streamlit demo (sandbox): upload ≤100 sample
                         ─► run pipeline ─► ranked table + interactive graph viz
```

**Why this split:** Phase A does the expensive work once (embeddings over 100k docs won't fit a
5-min budget reliably); Phase B is vectorized numpy math over cached arrays → fast, deterministic,
and reproducible inside the Stage-3 Docker sandbox.

---

## Technology stack

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11 | Matches spec examples; broad ecosystem. |
| JSONL parsing | stdlib `json` streaming (+ `orjson` optional) | Stream 487 MB without loading whole file. |
| Numerics / vectors | `numpy` | Vectorized scoring; `float32` embedding store. |
| Tabular features | `pandas` (or `polars` if speed needed) | Feature tables, parquet I/O. |
| Embeddings | `sentence-transformers` — **BAAI/bge-small-en-v1.5** (or `all-MiniLM-L6-v2`) | Small, strong, CPU-friendly; model weights cached locally so ranking stays offline. |
| ANN / similarity | `faiss-cpu` | Fast kNN to build the similarity graph + retrieval; CPU-only. |
| Graph | `networkx` (igraph as fallback if perf needed) | In-memory, no external service, easy to reason about + visualize. |
| Honeypot/rules | pure Python/numpy | Transparent, defensible logical checks. |
| Reasoning | deterministic templating (no LLM at runtime) | Spec forbids hosted LLMs in ranking; must be reproducible. |
| Demo UI | `streamlit` + `pyvis`/`networkx`+`plotly` | Interactive ranked list + graph viz; deployable to Streamlit Cloud / HF Spaces. |
| Validation | provided `validate_submission.py` | Authoritative format check. |
| Packaging | `requirements.txt` (pinned) + `Dockerfile` | Stage-3 reproduction; sandbox. |
| Config | `config.yaml` (weights, paths, model name) | Tunable scoring without code edits. |

---

## Components (modules under `src/`)

1. **`ingest.py`** — streaming loader for `candidates.jsonl`; light schema sanity check against
   `candidate_schema.json` (on a sample, not all 100k each run); builds the per-candidate text
   document (headline + summary + career descriptions) used for embeddings.

2. **`jd.py`** — encodes the JD into:
   - a curated **query text** for semantic similarity, and
   - **structured requirements**: experience band (5–9y soft), product-vs-services, NLP/IR vs
     CV/speech, location (Noida/Pune/India or relocate), must-haves (retrieval/vector-DB/eval),
     and the disqualifier/negative-signal rules.

3. **`features.py`** — per-candidate structured features:
   - `role_fit_gate` — title + career-history evidence of ML/search/ranking/recsys at product cos.
   - `skill_trust` — endorsements × duration_months × assessment-score corroboration (discounts stuffing).
   - `experience_fit`, `location_fit`.
   - `behavior_mod` — bounded availability multiplier (last_active recency, recruiter_response_rate,
     open_to_work, notice_period, interview_completion). **Handle `-1` sentinels as missing**, not low.
   - `negative_flags` — consulting-only, research-only, LangChain-only, no-code-18mo, title-chaser,
     CV/speech-only, closed-proprietary.

4. **`honeypot.py`** — logical-consistency detector (tenure vs company age, expert+0-months,
   assessment contradicting proficiency, impossible timelines, YOE vs career sum, current-role
   tenure > total career). Emits a `honeypot_score`; high score → hard demotion (force out of top 100).

5. **`graph.py`** — builds the in-memory `networkx` graph and derives **graph-assisted features**:
   - Nodes: candidate, skill, company, title, industry.
   - Edges: has_skill (weighted by trust), worked_at, has_title, in_industry, kNN-similar (FAISS).
   - Features fed to the scorer:
     - **skill co-occurrence coherence** — do a candidate's skills form a coherent AI/ML cluster,
       or a scattered keyword-stuff pattern? (community/clustering signal)
     - **company-prestige / product-signal propagation** — propagate a product-vs-services signal
       across the company nodes.
     - **peer-similarity boost** — does the candidate cluster (via kNN edges) with other genuine
       fits, or with off-role/honeypot nodes? Guards against isolated keyword-stuffers.

6. **`score.py`** — combines everything (vectorized):
   ```
   base   = relevance × role_fit_gate × skill_trust × experience_fit × location_fit × graph_boost
   final  = base × Π(penalties) × behavior_mod × (0 if honeypot else 1)
   ```
   Sort by `final` desc, tie-break `candidate_id` asc, take top 100, assign ranks. Calibrate so
   scores stay differentiated and non-increasing by rank.

7. **`reasoning.py`** — deterministic, **fact-grounded** reasoning generator. Pulls the actual
   driving facts (YOE, current_title, top *corroborated* skills, key signal values, one honest
   gap) into varied sentence structures; rank-consistent tone; never cites a skill absent from the
   profile. Designed to pass the 6 Stage-4 manual-review checks.

8. **`precompute.py`** — offline driver: ingest → embed → features → honeypot → graph → write
   `artifacts/` (embeddings.npy, features.parquet, honeypot.parquet, graph.pkl, graph_features.parquet).

9. **`rank.py`** (root entrypoint) — the single reproduce command. Loads artifacts, runs `score`,
   `reasoning`, writes CSV, optionally invokes the validator. If artifacts are missing it can
   trigger `precompute` (documented as the longer path).

10. **`app.py`** (Streamlit demo) — upload a ≤100-candidate sample → run the pipeline → show the
    ranked shortlist with reasoning + an **interactive graph** (candidate↔skill↔company,
    highlighting honeypots/stuffers and why top picks connect to the JD).

---

## Repo layout

```
RunAI/
├── Docs/                       # existing documentation (+ link to plan.md)
├── plan.md                     # copy of this plan
├── India_runs_data_and_ai_challenge/   # bundle (candidates.jsonl gitignored)
├── artifacts/                  # precomputed (gitignored)
├── src/
│   ├── ingest.py  jd.py  features.py  honeypot.py  graph.py
│   ├── score.py   reasoning.py  precompute.py
├── rank.py                     # single entrypoint → submission.csv
├── app.py                      # Streamlit sandbox/demo
├── config.yaml                 # weights, model name, paths
├── requirements.txt            # pinned deps
├── Dockerfile                  # Stage-3 reproducibility + sandbox
├── submission_metadata.yaml    # mirrors portal metadata
└── README.md                   # setup + exact reproduce command
```

---

## Build milestones (incremental, with real git history)

- **M1 — Data exploration** (notebook/script): quantify titles, keyword-stuffers, locate the ~80
  honeypots, profile the genuine AI-engineer cohort, sanity-check signal distributions. Output
  findings into `Docs/` to ground weights.
- **M2 — Ingest + structured baseline**: `ingest.py`, `features.py` (no embeddings yet),
  `score.py` v0, `rank.py` → valid CSV passing `validate_submission.py`.
- **M3 — Embeddings + relevance**: `precompute.py` embeds pool; add semantic `relevance`;
  precompute/light-rank split working within 5 min.
- **M4 — Honeypot detector + JD disqualifiers**: `honeypot.py`, negative-signal rules; verify
  zero honeypots/stuffers in top 50.
- **M5 — Graph-assisted features**: `graph.py` (networkx + FAISS kNN edges); fold `graph_boost`
  into the scorer; measure effect on top-50 quality.
- **M6 — Reasoning generator**: `reasoning.py`; audit 10 sampled rows against the 6 checks.
- **M7 — Streamlit demo + packaging**: `app.py`, `Dockerfile`, `requirements.txt`,
  `submission_metadata.yaml`, `README.md`; deploy sandbox.
- **M8 — Hardening**: enforce/measure compute budget (time + memory), determinism, final
  validation, methodology summary.

---

## Verification

- **Format:** `python India_runs_data_and_ai_challenge/validate_submission.py submission.csv`
  passes with zero errors (100 rows, ranks unique, non-increasing scores, tie-break correct).
- **Compute budget:** time the ranking step (`/usr/bin/time -l python rank.py ...`) — confirm
  **≤5 min wall-clock and ≤16 GB peak RSS** on CPU with network disabled; repeat inside the
  Dockerfile to mirror Stage-3.
- **Determinism:** run `rank.py` twice → byte-identical CSV (fixed seeds, stable sorts).
- **Quality (no leaderboard → inspection):** manually review top 20 (genuine senior AI/ML at
  product companies?); confirm **0 honeypots and 0 keyword-stuffers in top 50**; confirm
  plain-language fits (recsys/ranking builders with modest skill lists) surface; spot-check that
  behavioral "twins" are separated by the modifier.
- **Reasoning audit:** sample 10 rows → check specific facts, JD connection, honest concerns, no
  hallucination, variation, rank consistency.
- **Sandbox:** Streamlit app runs a ≤100 sample end-to-end within budget and renders the graph.

---

## Open items to decide during build

- Final embedding model (bge-small vs MiniLM) — pick on CPU speed/quality in M3.
- Component weights/calibration — tune by inspection in M1/M4/M5 (no leaderboard feedback).
- How hard to gate on role-fit without dropping genuine plain-language fits.
- Graceful filling of ranks ~50–100 when genuine fits run out (adjacent-candidate fallback).
