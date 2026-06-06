# Product Requirements Document (PRD)

**Project:** Intelligent Candidate Discovery & Ranking System
**Context:** Redrob Hackathon v4 — Intelligent Candidate Discovery & Ranking Challenge
**Owner:** Pushkal (team lead)
**Status:** Draft v1
**Last updated:** 2026-06-06

---

## 1. Problem statement

Redrob is a Series A talent-intelligence platform. Recruiters need to find the best-fit
candidates for a role from a large pool, but keyword filters surface the wrong people:
candidates who *list* the right skills but aren't actually a fit, and candidates who *are* a
fit but don't use the fashionable vocabulary.

We are given a single job description ("Senior AI Engineer — Founding Team") and a pool of
**100,000 candidate profiles**. We must produce a **ranked shortlist of the 100 best-fit
candidates**, best-first, each with a short, fact-grounded justification.

The system must act as an **AI recruiter**, not a keyword filter:

- **Deep job understanding** — interpret a nuanced, intentionally-honest JD.
- **Contextual relevance** — semantic fit, not keyword overlap.
- **Signal integration** — combine profile attributes, career metadata, and behavioral signals.
- **The output** — a fast, accurate, well-reasoned ranked shortlist.

## 2. Goals & non-goals

### Goals
1. Maximize the official composite score: `0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`.
2. Rank genuine fits highly even when they use plain language (no buzzwords).
3. Avoid the traps: keyword stuffers, honeypots, off-role profiles, unavailable candidates.
4. Produce honest, specific, non-templated reasoning for the top 100.
5. Run the ranking step within hard compute limits (≤5 min, ≤16 GB, CPU-only, no network).
6. Ship a reproducible repo + hosted sandbox that survives Stages 3–5 (reproduction, manual
   review, defend-your-work interview).

### Non-goals
- We do **not** rank candidates 101+; only the top 100 matter.
- We do **not** need to special-case every honeypot — a good ranker should naturally avoid them.
- We are **not** building a production service; this is a robust, defensible Proof of Concept.
- We do **not** call hosted LLMs during ranking (explicitly forbidden, and won't scale).

## 3. Users & stakeholders

- **Primary "user":** the hackathon evaluator / Redrob engineering team.
- **Simulated end user:** a recruiter who wants a trustworthy shortlist.
- **Reviewers:** automated validator (Stage 1), scoring harness (Stage 2), code reviewers
  (Stages 3–4), interviewers (Stage 5).

## 4. Scope

### In scope
- Ingest and parse `candidates.jsonl` (100k records, ~487 MB).
- Interpret the JD into explicit, testable requirements and disqualifiers.
- Feature extraction per candidate (role fit, career evidence, skill trust, behavioral availability, traps).
- A hybrid scoring model (semantic + structured + behavioral modifier + penalties).
- Honeypot / logical-consistency detection.
- Top-100 selection, deterministic tie-breaking, CSV emission.
- Fact-grounded reasoning generation.
- Repo, README, requirements, metadata YAML, sandbox.

### Out of scope (for the PoC)
- Online A/B testing, recruiter feedback loops, index refresh pipelines.
- Multi-JD generalization (we optimize for the one released JD).

## 5. Functional requirements

| ID | Requirement |
|----|-------------|
| FR-1 | Load and stream-parse all 100,000 candidate records without exhausting 16 GB RAM. |
| FR-2 | Encode the JD into structured requirements: must-haves, nice-to-haves, do-not-wants, disqualifiers, location/availability preferences. |
| FR-3 | For each candidate, compute role-fit (title + career history evidence), not just skill-keyword overlap. |
| FR-4 | Apply a skill-trust signal (endorsements × duration × assessment scores) to discount keyword stuffing. |
| FR-5 | Apply a behavioral-availability modifier (recency, response rate, open-to-work, etc.). |
| FR-6 | Detect and demote honeypots / logically-impossible profiles. |
| FR-7 | Apply JD disqualifiers (research-only, LangChain-only <12mo, consulting-only career, CV/speech/robotics-without-NLP, title-chaser). |
| FR-8 | Produce a deterministic top-100 ranking with non-increasing scores and unique ranks. |
| FR-9 | Generate a 1–2 sentence, fact-grounded, non-templated reasoning per ranked candidate. |
| FR-10 | Emit a spec-compliant CSV and pass `validate_submission.py`. |

## 6. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Ranking step completes in ≤ 5 minutes wall-clock on CPU. |
| NFR-2 | Peak memory ≤ 16 GB. |
| NFR-3 | No network calls / hosted-LLM calls during the ranking step. |
| NFR-4 | Reproducible: single command produces the CSV from `candidates.jsonl`. |
| NFR-5 | Deterministic output across runs (fixed seeds, stable sorts). |
| NFR-6 | Pre-computation (embeddings/indexes) may exceed 5 min but must be documented and scripted. |
| NFR-7 | Code is clean, readable, and defensible in a 30-min interview. |

## 7. Success criteria

- **Primary:** strong composite score, especially NDCG@10 (50% weight) — get the top 10 right.
- **Guardrails:** honeypot rate in top 100 **< 10%** (ideally ~0); zero keyword-stuffers in top 10.
- **Reproducibility:** clean reproduction inside the sandboxed container within limits.
- **Review:** reasoning passes the 6 manual-review checks; git history shows real iteration.

## 8. Key risks & mitigations

| Risk | Mitigation |
|------|-----------|
| Embedding-only ranking surfaces keyword stuffers & honeypots → disqualification | Guard semantic score with title/career sanity checks + honeypot detector + skill-trust. |
| Ranking step too slow for 5 min | Precompute embeddings offline; lightweight CPU ranker (e.g. cached vectors + structured features). |
| Reasoning flagged as templated/hallucinated | Generate strictly from extracted facts; vary structure; cite real signals; acknowledge gaps. |
| Flat git history flagged as "single dump" | Commit incrementally with meaningful messages across real iteration. |
| Over-fitting to assumptions with no leaderboard feedback | Validate via internal logic, spot-checks, and held-out reasoning audits, not by submitting. |

## 9. Milestones

1. **M0 — Docs & plan** (this folder). ✅ in progress
2. **M1 — Data exploration:** quantify titles, keyword stuffers, honeypots, genuine-fit cohort.
3. **M2 — Baseline ranker:** structured-feature scorer + CSV + validator passing.
4. **M3 — Hybrid scorer:** add embeddings (precomputed) + behavioral modifier + penalties.
5. **M4 — Honeypot detector & disqualifier rules.**
6. **M5 — Reasoning generator.**
7. **M6 — Packaging:** repo, README, requirements, metadata YAML, sandbox deploy.
8. **M7 — Hardening:** compute-budget check, reproducibility, final validation.

## 10. Open questions

- Which embedding model fits CPU + offline + 5-min-ranking constraints (precompute vs runtime)?
- How aggressive should behavioral down-weighting be vs. relevance (avoid burying true fits)?
- Score scale/calibration: how do we keep scores meaningfully differentiated and non-increasing?
- How many genuine Tier-1/Tier-2 fits actually exist in the pool (informs how to fill ranks 50–100)?

See [07_Architecture.md](07_Architecture.md) for the proposed technical design.
