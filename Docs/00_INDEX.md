# Documentation Index — Redrob Candidate Ranking Challenge

This folder contains the planning and reference documentation for our submission to the
**Intelligent Candidate Discovery & Ranking Challenge** (Redrob Hackathon v4).

All documents are derived from the official challenge bundle in
[`../India_runs_data_and_ai_challenge/`](../India_runs_data_and_ai_challenge/) plus our own
analysis of the candidate pool.

## Documents

| # | Document | Purpose |
|---|----------|---------|
| 01 | [PRD.md](01_PRD.md) | Product Requirements Document — what we are building, scope, goals, success criteria, milestones. |
| 02 | [Challenge_Brief.md](02_Challenge_Brief.md) | The challenge, the job description we rank against, and what "good" means. |
| 03 | [Data_Dictionary.md](03_Data_Dictionary.md) | Full candidate schema, the 23 behavioral signals, and observed pool statistics. |
| 04 | [Submission_Requirements.md](04_Submission_Requirements.md) | Output format, compute constraints, deliverables, and a pre-submit checklist. |
| 05 | [Evaluation_and_Scoring.md](05_Evaluation_and_Scoring.md) | Scoring metrics, tiebreaks, and the 5-stage evaluation pipeline. |
| 06 | [Traps_and_Honeypots.md](06_Traps_and_Honeypots.md) | The adversarial dataset: keyword stuffers, Tier-5 fits, honeypots, disqualifiers. |
| 07 | [Architecture.md](07_Architecture.md) | Proposed system architecture and the ranking pipeline (living document). |
| — | [../plan.md](../plan.md) | Approved implementation plan: phased flow, tech stack, milestones, verification. |
| 08 | [08_M1_Findings.md](08_M1_Findings.md) | M1 data-exploration findings from the full 100k scan (grounds scoring weights). |

## Quick facts

- **Task:** rank the **top 100** candidates out of a **100,000** pool against one JD.
- **JD:** "Senior AI Engineer — Founding Team" at a Series A talent-intelligence startup.
- **Output:** a CSV (`candidate_id,rank,score,reasoning`) with exactly 100 rows.
- **Compute:** ranking step ≤ 5 min, ≤ 16 GB RAM, CPU-only, no network.
- **Scoring:** `0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`.
- **The catch:** dataset is adversarial — keyword stuffers, ~80 honeypots, plain-language strong fits.
- **Deliverables:** code repo + docs + ranked CSV + hosted sandbox link.

## Status

- [x] Read all challenge materials
- [x] Initial pool exploration (20k-row scan)
- [x] Documentation drafted
- [x] Data exploration deep-dive (M1 — see [08_M1_Findings.md](08_M1_Findings.md))
- [ ] Ranking pipeline implementation (M2–M6)
- [ ] Demo + submission packaging (M7–M8)
