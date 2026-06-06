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
