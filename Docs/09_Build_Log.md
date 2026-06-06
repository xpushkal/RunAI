# Build Log

Per-milestone record of what was built, results, and decisions. One section per milestone.

---

## M2 — Ingest + structured baseline ranker

**Branch:** `M2` (off `M1`). **Status:** ✅ valid CSV, strong baseline.

### What was built
- `src/config.py` — loads `config.yaml`.
- `src/ingest.py` — streaming JSONL loader + `candidate_document()` text builder.
- `src/jd.py` — JD encoded as lexicons (titles, core-AI skills, vector-DB, eval, career-evidence
  phrases, consulting firms, CV/speech terms, product vs services industries, preferred cities)
  plus a curated `JD_QUERY_TEXT` for M3 embeddings.
- `src/features.py` — per-candidate components: `title_fit`, `career_fit`, `skill_trust`
  (endorsement×duration×assessment-corroborated), `experience_fit`, `location_fit`,
  `behavior_modifier` (-1 sentinels treated as missing), `negative_penalty` (consulting-only,
  cv/speech-only), `honeypot_signal` (precision-first checks).
- `src/score.py` — structured relevance proxy `0.45·title + 0.40·career + 0.15·skill_trust`;
  `base = relevance·experience·location·graph_boost`; `final = base·penalty·behavior·(0 if honeypot)`;
  sort by raw score desc, tie-break candidate_id asc, top-100, rescaled non-increasing scores.
- `src/reasoning.py` — deterministic fact-grounded 1–2 sentence justifications, rank-aware tone,
  honest-concern surfacing.
- `rank.py` — single entrypoint → `submission.csv`.

### Results (full 100k pool)
- Runtime **6.2s** (well under the 5-min budget; no embeddings yet).
- `validate_submission.py`: **valid**.
- Top-100 audit: **0 honeypots, 0 off-role/keyword-stuffers**; YOE 4.9–9.0 (mean 6.3);
  100% India; all product industries (AI/ML, Fintech, Food Delivery, HealthTech, SaaS,
  Conversational AI, Software); titles dominated by Recommendation Systems Engineer,
  AI Research Engineer, ML Engineer, Data Scientist, NLP Engineer.
- Top picks: Senior Data Scientist @ Razorpay, Lead AI Engineer @ Razorpay, ML/Search engineers
  @ CRED, Zomato, Meesho, Sarvam AI, Microsoft — exactly the JD's target profile.

### Observations / carry-forward
- The structured baseline already nails the *obvious* cohort. The top 100 is entirely AI-titled
  with corroborated skills — good, but the JD also wants **plain-language Tier-5 fits** (built a
  recsys, no buzzwords). M3 embeddings + M5 graph should surface those and add ordering nuance.
- Honeypot detection still precision-first (catches ~45/80). **M4** expands it and the negative
  signals (research-only, LangChain-only, no-code-18mo, title-chaser).
- Reasoning is solid but somewhat templated; **M6** adds variation + sharper honest concerns.

---

## M3 — Embeddings + semantic relevance (precompute / light-rank split)

**Branch:** `M3` (off `M2`). **Status:** ✅ blended ranking, within budget.

### What was built
- `src/embeddings.py` — load model (offline only), encode, cosine-to-query, rescale, artifact check.
- `src/precompute.py` — offline embedder: streams pool → `candidate_document()` → embeds with
  **BAAI/bge-small-en-v1.5** (CPU) → saves `artifacts/embeddings.npy` (100000×384 float32, L2-norm),
  `candidate_ids.npy`, `jd_embedding.npy`. The JD query vector is cached so the ranking step needs
  **no torch and no model load** — only numpy.
- `src/score.py` — `relevance = 0.55·embed_sim + 0.45·structured_proxy` (blend configurable);
  rescales cosine via `[embed_sim_floor=0.30, embed_sim_ceil=0.75] → [0,1]`. Falls back to
  structured-only if artifacts are absent.
- `rank.py` — loads cached vectors (pure numpy), attaches `embed_sim` per candidate, then ranks.
- Config: `embedding.max_seq_length` trimmed 384→256 for precompute speed; `scoring.relevance_blend`,
  `structured_proxy`, `embed_sim_floor/ceil` added.

### Results (full 100k pool)
- Precompute: ~14 min offline (one-time, allowed to exceed budget). 100000×384 vectors cached.
- **Ranking step: 6.3s** (loads ~150 MB of vectors + numpy dot product); validator: **valid**.
- Top-100 audit: still **0 honeypots, 0 off-role/stuffers**; YOE 4.9–9.0 (mean 6.3); 100% India.
- Embeddings added recall: surfaced **Senior Applied Scientists** (Swiggy, Sarvam AI, Niramai)
  that structured-only ranked lower — the "plain-language fit" behavior we wanted.

### Carry-forward to M4
- **CV-primary leakage:** 5 "Computer Vision Engineer" profiles entered ranks 42–95. The JD names
  CV/speech/robotics-without-NLP as a do-not-want. The current `cv_speech_only` penalty (needs ≥3
  CV skills AND 0 core-AI skills) is too narrow. **M4** strengthens CV/speech detection (title +
  career + skill mix) and adds the remaining negative signals (research-only, LangChain-only,
  no-code-18mo, title-chaser) and a richer honeypot detector (target ~80, currently ~45).

---

## M4 — Honeypot detector + JD disqualifier rules

**Branch:** `M4` (off `M3`). **Status:** ✅ traps demoted, genuine fits preserved.

### Calibration (full-pool scan)
- Tested candidate honeypot checks. **Rejected as noise**: `skill_gt_career` (9,231 hits) and
  `active_before_signup` (7,496) — far too common to be "impossible," they're dataset quirks.
- **Kept (precision-first, logically impossible):** `dur_vs_dates` (duration_months disagrees with
  start/end by >6mo, 33), `career_gt_yoe` (24), `expert_0mo` (21), plus `currole_gt_career`,
  `expert_lowassess`, `start_gt_end`. **Clean union = 59 honeypots**, **0 in the top 100**.
- The spec's ~80 includes "tenure at a company founded later" cases needing founding-year data we
  don't have; the spec says natural avoidance is fine and the DQ gate is >10% in top 100 → clear at 0%.

### What was built (`src/features.py`)
- `honeypot_signal()` rewritten: dropped the noisy checks, added the date-vs-duration check;
  hard-demotes (`score → 0`) any candidate with a flag.
- `negative_penalty()` expanded with: **cv_speech_only** (CV/speech-primary AND no core IR/NLP
  skill AND no NLP/IR career evidence), **research_only**, **langchain_only**, **title_chaser**
  (≥4 roles, avg tenure <18mo). All multiplicative, all precision-first.

### Results
- Ranking step 8.7s; validator **valid**; top-100 still **0 honeypots, 0 stuffers**, YOE 4.9–9.0.
- Pool-wide flags: honeypot 59, consulting_only 13,049, langchain_only 2,801, cv_speech_only 1,331
  (down from 1,948 — now spares CV-titled people who have NLP/IR), title_chaser 623.
- **Key validation:** the 4 "Computer Vision Engineer" profiles remaining in the top 100 are
  genuine retrieval/ranking engineers with CV titles (RAG/NLP/pgvector/Learning-to-Rank skills,
  "built recommendation/ranking systems" in career text). The penalty **correctly** does not fire
  on them — the system reads beyond the title, exactly the JD's intent.

---

## M5 — Graph-assisted features (networkx + FAISS kNN)

**Branch:** `M5` (off `M4`). **Status:** ✅ graph reinforces role/quality, traps still excluded.

### What was built (`src/graph.py`)
The graph does not rank; it derives a bounded `graph_boost ∈ [0.85, 1.15]` from three signals,
all precomputed offline into `artifacts/graph_features.parquet` (ranking just loads it):
- **peer_quality** — FAISS `IndexFlatIP` kNN (k=15) over the candidate embeddings; each
  candidate's score is the similarity-weighted mean `title_fit` of its neighbours. *Are the people
  most like you on-role?*
- **skill_coherence** — a `networkx` co-occurrence graph over core-AI skills; measures whether a
  candidate's AI skills co-occur tightly across the pool.
- **company_product** — a `networkx` candidate↔company bipartite graph; a company's product-ness
  is the fraction of its people in product industries, propagated back to the candidate.
- `graph_boost = min + (max-min)·(0.50·peer + 0.25·coherence + 0.25·product)`.
- `rank.py` loads the boosts (cheap dict lookup); `src/score.py` already multiplies `base` by it.

### Results
- Graph precompute ~12s offline; ranking step **12.7s**; validator **valid**; top-100 **0 honeypots**.
- **Discrimination:** top-100 `graph_boost` 1.066–1.150 (mean 1.125, above the pool's p99 of 1.075);
  keyword-stuffers (Ops Manager w/ AI skills) get ~0.94 driven by **peer_quality 0.10–0.17**
  (their neighbours are off-role) and **company_product 0.00** (services employers).
- `skill_coherence` alone does not catch stuffers (their stuffed AI skills *do* co-occur in the
  corpus) — by design it's a secondary signal; peer_quality + company_product do the separating.
- Net effect: a ±15% reinforcement/tie-break nudge that strengthens genuine fits without letting
  semantic relevance get overridden.
