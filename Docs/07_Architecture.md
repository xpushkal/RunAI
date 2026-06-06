# System Architecture (Proposed)

**Status:** Draft / living document. Will evolve as we build and explore the data.
This is the technical design that satisfies the [PRD](01_PRD.md) under the
[submission constraints](04_Submission_Requirements.md).

## Design principles

1. **Semantic, but gated.** Contextual fit drives ranking, but title/career sanity and
   skill-trust gate it so keyword stuffers and honeypots can't float to the top.
2. **Two phases.** Heavy work (embeddings) is **precomputed offline**; the **ranking step is
   light** and runs ≤5 min CPU-only on precomputed artifacts.
3. **Deterministic & reproducible.** Fixed seeds, stable sorts, single reproduce command.
4. **Explainable.** Every score decomposes into named components → powers honest reasoning and
   the Stage-5 interview.

## Two-phase pipeline

```
                 ┌────────────────────── OFFLINE (precompute, may exceed 5 min) ─────────────────────┐
candidates.jsonl │  parse → build candidate text → embed (local CPU model) → cache embeddings/index   │
                 │  also: precompute structured features, honeypot flags                              │
                 └────────────────────────────────────────────────────────────────────────────────────┘
                                                  │  artifacts (embeddings.npy, features.parquet)
                                                  ▼
                 ┌────────────────────── RANKING STEP (≤5 min, ≤16 GB, CPU, no net) ─────────────────┐
   JD encoding → │  load artifacts → score each candidate → penalties/modifiers → sort → top 100      │
                 │  → generate reasoning → write submission.csv → validate                            │
                 └────────────────────────────────────────────────────────────────────────────────────┘
```

> If we keep the model small enough, embedding 100k short docs may fit in the ranking budget too;
> otherwise embeddings are a documented precompute artifact (allowed by the spec).

## Components

### 1. Data ingestion
- Stream `candidates.jsonl` line-by-line (don't load 487 MB as one object).
- Validate against `candidate_schema.json` (sample-level, not all 100k each run).

### 2. JD interpretation
- Encode the JD into: must-haves, nice-to-haves, do-not-wants, hard disqualifiers,
  location/availability preferences (see [Challenge Brief](02_Challenge_Brief.md)).
- Build a JD "query" representation: a curated text for semantic similarity **plus** structured
  requirement checks (experience band, product-vs-services, NLP/IR vs CV/speech, etc.).

### 3. Candidate representation
- **Text view:** concatenate headline + summary + career_history descriptions (the evidence of
  what they *built*), used for semantic similarity.
- **Structured view:** title, YOE, company sizes/industries, education tier, skills with
  endorsements/duration/assessment, behavioral signals.

### 4. Feature extraction (per candidate)
- `relevance` — semantic similarity(JD query, candidate text) via local embeddings (e.g. a small
  sentence-transformer / BGE-small / E5-small, CPU-friendly). Candidate for evaluation in M3.
- `role_fit_gate` — title + career-history evidence of ML/search/ranking/recsys at product cos.
- `skill_trust` — endorsements × duration_months × assessment-score corroboration.
- `experience_fit` — closeness to the 5–9y band (soft).
- `location_fit` — Noida/Pune/India or relocatable.
- `behavior_mod` — bounded availability multiplier (recency, response rate, open-to-work, notice).
- `negative_flags` — consulting-only, research-only, LangChain-only, title-chaser, CV/speech-only.
- `honeypot_score` — logical-consistency violations (see [Traps doc](06_Traps_and_Honeypots.md)).

### 5. Scoring & ranking
```
base   = relevance × role_fit_gate × skill_trust × experience_fit × location_fit
final  = base × Π(penalties) × behavior_mod × (0 if honeypot else 1)
```
- Sort by `final` desc, tie-break candidate_id asc → take top 100 → assign ranks 1..100.
- Calibrate `final` so it stays differentiated and (after sort) non-increasing by rank.

### 6. Reasoning generation
- Deterministic, **fact-grounded** template engine that pulls the actual driving facts per
  candidate (YOE, title, top corroborated skills, key signal values, and any acknowledged gap).
- Vary sentence structure; ensure rank-consistent tone; never mention a skill not in the profile.
- **No hosted LLM at ranking time** (forbidden + won't scale) — small local generation or
  structured templating with enough variation to pass the manual-review checks.

### 7. Output & validation
- Write `<participant_id>.csv` per spec; run `validate_submission.py` in-process or as a step.

## Compute budget plan

| Phase | Work | Budget |
|-------|------|--------|
| Offline | Embed 100k candidate docs; cache vectors; precompute features | unbounded (documented) |
| Ranking | Load artifacts, score, sort, reason, write CSV | **≤ 5 min, ≤ 16 GB, CPU, no net** |

## Candidate tech stack (to confirm in M1/M3)

- Python 3.11.
- Parsing: stdlib `json` (streaming) / `orjson`.
- Embeddings: a small CPU sentence-transformer (BGE-small/E5-small/MiniLM) — choose for
  speed/quality on CPU; vectors stored as `float32` numpy.
- Similarity / ANN: numpy / FAISS (CPU) if needed for speed.
- Structured features: numpy / pandas / polars.
- Reasoning: deterministic templating (no network).
- Packaging: `requirements.txt`, single `rank.py` entrypoint, Dockerfile for sandbox.

## Open design questions

- Embedding model choice under CPU + 5-min ranking (precompute vs runtime tradeoff).
- Exact weights/calibration of components (tune via inspection, no leaderboard).
- How hard to gate on role-fit without dropping genuine plain-language fits.
- Filling ranks ~50–100 when genuine fits run out (graceful degradation to "adjacent" candidates).

## Repo layout (proposed)

```
RunAI/
├── Docs/                      # this documentation
├── data/                      # candidates.jsonl (gitignored), artifacts
├── src/
│   ├── ingest.py              # streaming loader
│   ├── jd.py                  # JD encoding / requirements
│   ├── features.py            # feature extraction
│   ├── honeypot.py            # logical-consistency detector
│   ├── score.py               # scoring & ranking
│   ├── reasoning.py           # reasoning generator
│   └── precompute.py          # offline embeddings/features
├── rank.py                    # single entrypoint → submission.csv
├── requirements.txt
├── Dockerfile                 # sandbox reproducibility
├── submission_metadata.yaml
└── README.md
```
