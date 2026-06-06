# Evaluation & Scoring

**Source:** `submission_spec.docx` (Sections 4–5, 7).

## How scoring works

Your top-100 ranking is scored against a **hidden ground truth** that assigns each candidate a
**relevance tier**. Scoring happens **once**, after submissions close — no public partition, no
live leaderboard, no per-submission feedback.

## The composite metric

```
Final composite =
    0.50 × NDCG@10
  + 0.30 × NDCG@50
  + 0.15 × MAP
  + 0.05 × P@10
```

| Metric | Weight | Measures | Implication for us |
|--------|--------|----------|--------------------|
| NDCG@10 | 0.50 | Quality + ordering of top 10 | **Dominant.** Getting the top 10 right (and well-ordered) is half the score. |
| NDCG@50 | 0.30 | Quality of top 50 | The next 40 still matter a lot. |
| MAP | 0.15 | Precision across all relevance levels | Reward putting all relevant candidates high. |
| P@10 | 0.05 | Fraction of top 10 that are "relevant" (tier 3+) | A floor signal — at minimum, top 10 should be tier 3+. |

### What this means strategically
- **Optimize the head of the list.** 80% of the weight is on the top 50, and 50% on the top 10.
- **Ordering matters** (NDCG is position-discounted), so calibrate scores, don't just bucket.
- A single honeypot or off-role keyword-stuffer in the top 10 is very costly (and risks the
  Stage-3 honeypot disqualifier).

## Relevance tiers (ground truth)

- The ground truth uses tiers; **"relevant" = tier 3+** (per the P@10 definition).
- **Honeypots are forced to tier 0** regardless of how good they look.
- We never see the tiers — we must infer fit from the JD + profile reasoning.

## Tiebreaks (between submissions)

If two submissions have identical composites:
1. Higher **P@5** wins.
2. Higher **P@10** wins.
3. Earlier submission timestamp wins.

→ Extra reason to nail the very top of the list (P@5, P@10).

## The honeypot filter

- ~80 honeypots with subtly impossible profiles, forced to tier 0.
- **Honeypot rate > 10% in your top 100 → disqualified** at Stage 3.
- Ranking honeypots in the top 10 signals a keyword/embedding-only system.
- We should detect & demote them (see [06_Traps_and_Honeypots.md](06_Traps_and_Honeypots.md)).

## The 5-stage evaluation pipeline

| Stage | What happens | Eliminated if… |
|-------|--------------|----------------|
| **1. Format validation** | Auto-validator on every submission | Any spec violation (Section 3 / `validate_submission.py`). |
| **2. Scoring** | Composite computed once on full hidden ground truth | Final score below the advancement cutoff. |
| **3. Code reproduction + honeypot check** | Top-N repos requested; ranking reproduced in sandbox (5min/16GB/no-GPU/no-net); honeypot rate computed | Can't reproduce within limits; honeypot rate >10% in top 100; missing/fabricated repo. |
| **4. Manual review** | Reasoning quality (6 checks), methodology coherence, git-history authenticity, code quality | Failed reasoning checks; flat git history; codebase is just LLM API calls. |
| **5. Defend-your-work interview** | 30-min video call with Redrob engineering | Can't explain architecture; contradicts submitted code; clearly didn't build it. |

### Design intent
The pipeline is built so **AI-assisted work with real human engineering succeeds**, while
**AI-only "paste-and-pray" submissions fail** at Stages 3–5. The compute constraint + repo
reproduction + interview together filter for genuine engineering, not for absence of AI use.

## Takeaways for our system

1. **Front-load quality into the top 10, then top 50** — that's where the weight is.
2. **Calibrate scores** so ordering is meaningful (NDCG rewards correct ordering).
3. **Zero tolerance for honeypots/stuffers in the head** — both score-costly and disqualifying.
4. **Make reasoning audit-proof** — specific, varied, honest, grounded.
5. **Reproducibility is a gate, not a nicety** — design for the sandbox from day one.
6. **Real git iteration + a defensible design** — we must be able to explain every choice.
