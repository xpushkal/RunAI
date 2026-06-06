# M1 — Data Exploration Findings

**Scope:** full scan of all **100,000** candidates in `candidates.jsonl`.
**Scripts:** `scripts/explore.py` (reproducible). **Purpose:** ground the scoring weights and
trap-handling in real distribution evidence before building the ranker.

## Headline findings

1. **Genuine AI-engineer fits are extremely rare** — exactly as the JD warned ("not expecting
   many matches in a 100K pool").
   - Only **726** candidates (0.73%) carry an AI/ML/DS-style title (ML Engineer, Data Scientist,
     AI Research Engineer, NLP Engineer, etc.).
   - **434** of those are at product-industry companies (Software/Fintech/E-commerce/SaaS/AI-ML/
     EdTech/Food-Delivery).
   - **222** are product-industry **and** in the 5–9y experience band — this is roughly the
     ceiling of "obvious" strong fits. The other ~ranks (50–100) will need plain-language fits
     and adjacent-role engineers (Software/Data/Backend engineers who built relevant systems).

2. **The keyword-stuffer trap is large and blatant.**
   - **2,216** candidates (2.2%) have **≥6 core-AI skills but a non-engineering title**.
   - Examples: `Operations Manager` listing RAG/FAISS/Pinecone/Embeddings; `Graphic Designer`
     with Semantic Search/Pinecone/Fine-tuning LLMs; `Customer Support` with FAISS/RAG/Pinecone;
     `Content Writer`, `Marketing Manager`, `HR Manager` similarly stuffed.
   - **Confirms the JD's explicit trap.** A skills-only or naive-embedding ranker will surface
     these. Role-fit gating + skill-trust must neutralize them.

3. **AI skills are sparse across the pool** (so raw AI-skill count is a weak, gameable signal):
   - 76.7% of candidates have **0** core-AI skills; mean is **0.58**.
   - The right tail (8–11 AI skills) is tiny (≈284 people) and heavily overlaps the stuffers.

4. **Honeypots need richer detection than simple heuristics.**
   - Conservative logical checks flag **45** so far (spec says ~80):
     `career_gt_yoe` (24) and `expert_0mo` (21).
   - The classic "8 yrs at a company founded 3 yrs ago" needs company-age inference we don't have
     directly — **M4 must add** more checks (e.g. tenure vs. plausible company timeline, skill
     `duration_months` vs `years_of_experience`, education/work timeline conflicts, assessment-vs-
     proficiency contradictions at finer thresholds).

## Distributions

### Core-AI skill count per candidate
```
0 skills: 76,707     4: 1,441     8:   265
1 skills: 11,022     5: 1,634     9:    14
2 skills:  4,788     6: 1,681    10:     4
3 skills:  1,460     7:   983    11:     1
mean: 0.58
```

### Titles
- engineer/developer/scientist titles: **41,814** (the broad eng pool to mine for plain-language fits).
- AI/ML/DS titles: **726** (the narrow obvious-fit pool).
- Dominant non-eng titles (each ~1.1–1.2k): Mechanical Engineer, HR Manager, Content Writer,
  Business Analyst, Sales Executive, Customer Support, Accountant, Civil Engineer, Graphic
  Designer, Operations Manager, Project Manager, Marketing Manager.

### Geography
- **India ~75%** (15,006 of first 20k); then USA, Canada, Australia, Singapore, UK, UAE, Germany.
- JD prefers Noida/Pune/India or relocatable Tier-1 — out-of-India-without-relocation is a soft
  down-weight, not a hard cut.

### Industry (product vs services)
- Services-leaning: IT Services (5,935), Consulting, Conglomerate, Paper Products, Manufacturing.
- Product-leaning: Software (4,604), Fintech, E-commerce, SaaS, AI/ML, Food Delivery, EdTech.
- The product-vs-services split is **learnable from `current_industry` + company names** and maps
  directly to the JD's "product over services" preference and the consulting-firm negative signal.

## Behavioral signals (sanity)
- `github_activity_score == -1` (no GitHub linked): **64.6%** → treat `-1` as **missing**, not low.
  For an engineering role, a *present* high GitHub score is a positive, but absence shouldn't
  heavily penalize (most of the pool lacks it).
- `offer_acceptance_rate == -1` (no history): **59.6%** → same; treat as missing.
- `recruiter_response_rate` mean **0.437** — wide spread; a strong separator for behavioral twins.
- `last_active_date` clusters in the last ~8 months (Oct 2025 – May 2026), reference "today" =
  2026-06-06. Staleness should be measured relative to the pool's recency, not absolute.

## Implications for scoring (feeds M2–M5)

| Observation | Design response |
|-------------|-----------------|
| Genuine fits are scarce (222 ideal) | Don't over-gate; mine the 41.8k eng pool via career-history text for plain-language fits to fill ranks ~30–100. |
| 2,216 obvious keyword-stuffers | `role_fit_gate` (title+career) and `skill_trust` (endorsements×duration×assessment) must be hard multipliers, not additive. |
| AI-skill count is gameable/sparse | Never rank on raw skill-keyword count; require corroboration. |
| Only 45/~80 honeypots caught by simple rules | Expand honeypot detector in M4; keep it precision-first to avoid nuking real candidates. |
| `-1` sentinels common | Mask sentinels as missing in `behavior_mod`; never treat as 0/low. |
| Most candidates lack GitHub | GitHub is a bonus when present, not a penalty when absent. |

## Reproduction
```
.venv/bin/python scripts/explore.py
```
(Outputs the distributions and example stuffers/honeypots/genuine-fits above.)
