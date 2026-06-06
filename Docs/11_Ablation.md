# Ablation & Robustness Analysis

Reproducible via `python scripts/ablation.py`. Computes features once, then re-scores the full
100k pool with each scoring layer disabled, and under perturbed weights. Overlap = fraction of
top-K shared with the full ranker.

## Ablation — disable one layer at a time

| Variant | top10 | top50 | top100 | honeypots | off-role |
|---------|------:|------:|-------:|----------:|---------:|
| **FULL (reference)** | 1.00 | 1.00 | 1.00 | 0 | 0 |
| structured-only (no embeddings) | 1.00 | 0.96 | 0.92 | 0 | 0 |
| embeddings-only relevance (no structured proxy) | 0.90 | 0.76 | 0.79 | 0 | 0 |
| no graph_boost | 0.50 | 0.52 | 0.71 | 0 | 0 |
| no behavior_modifier | **0.00** | 0.54 | 0.56 | 0 | 0 |
| no penalties | 1.00 | 0.98 | 0.97 | 0 | 0 |
| no honeypot demote | 1.00 | 1.00 | 1.00 | 0 | 0 |

### What each row tells us
- **Structured vs embeddings are complementary.** Structured-only already reproduces the top-10
  (1.00) and most of the top-50 (0.96) — the structured signal carries the *head*. Embeddings-only
  relevance keeps the top-10 mostly (0.90) but diverges in the tail (0.76–0.79) — embeddings add
  *recall* (plain-language fits) at ranks 50–100. Blending both is the point.
- **graph_boost is a real head re-orderer** (top-10 overlap 0.50): among many similarly-relevant AI
  engineers, the kNN peer-quality + company-product signal meaningfully decides ordering.
- **behavior_modifier is the decisive differentiator at the very top** (top-10 overlap 0.00).
  When relevance is near-saturated for the strongest candidates, *availability* (recency, recruiter
  response, open-to-work, notice period) determines who leads — exactly what the JD and signals doc
  say it should ("more predictive of whether a candidate can actually be hired"). This is a
  deliberate design choice (behavior multiplier spans [0.6, 1.1]).
- **penalties shape the tail, not the head** (top-10 1.00, top-100 0.97): genuine fits aren't
  penalized; the disqualifier penalties mostly filter borderline candidates lower down.
- **honeypot demote is a safety net, not load-bearing** (all 1.00): honeypots never reach the
  top-100 on score alone, so hard-demoting them changes nothing here — but it guarantees the
  Stage-3 honeypot gate even if weights change.

### Defense-in-depth (the key robustness finding)
**Every ablation keeps honeypots = 0 and off-role/keyword-stuffers = 0 in the top-100.** Even with
*pure-embedding relevance and no structured gating*, the remaining multiplicative layers
(experience, location, graph_boost, penalties) keep traps out. Trap rejection does not depend on
any single rule — it is over-determined by independent signals.

## Robustness — perturb the relevance blend

| embed / structured weight | top10 | top50 | top100 | honeypots | off-role |
|---------------------------|------:|------:|-------:|----------:|---------:|
| 0.40 / 0.60 | 1.00 | 1.00 | 0.97 | 0 | 0 |
| **0.55 / 0.45 (default)** | 1.00 | 1.00 | 1.00 | 0 | 0 |
| 0.70 / 0.30 | 1.00 | 0.94 | 0.98 | 0 | 0 |

Across a ±0.15 swing in the main blend weight, the top-10 is **identical** and the top-50 moves by
≤6%, with traps still fully excluded. The ranking is **not fragile to the exact weights** — i.e.
not overfit to a hand-tuned constant (important given there is no leaderboard to fit against).

## Takeaways for the interview
1. The system is **layered and complementary**: structured carries the head, embeddings add tail
   recall, graph + behavior decide ordering among near-equals.
2. **Trap defense is over-determined** (defense-in-depth), not a single brittle filter.
3. The result is **stable to weight perturbation**, so the choices are principled, not fitted.
