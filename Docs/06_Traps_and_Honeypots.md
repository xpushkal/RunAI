# Traps & Honeypots

The dataset is **adversarial by design**. The JD and submission spec both warn about this. This
document catalogs the trap types and the concrete detection/handling rules we'll implement.

**Sources:** `job_description.docx` (participant note), `submission_spec.docx` (Section 7),
`redrob_signals_doc.docx`, our pool scan.

## Trap taxonomy

### 1. Keyword stuffers (the headline trap)
Candidates whose **skills list is packed with AI keywords** (NLP, LoRA, GANs, Fine-tuning LLMs,
RAG, etc.) but whose **actual role is unrelated** (HR Manager, Content Writer, Marketing Manager,
Graphic Designer, Accountant…).

- The provided `sample_submission.csv` deliberately ranks these #1 (HR Manager "with 9 AI core
  skills") — that is the **wrong** answer, shown as bait.
- **Tell-tale:** high AI-skill count but `current_title` / `career_history` show no ML/eng work;
  skills have low `duration_months`, low/zero `endorsements`, or no matching
  `skill_assessment_scores`.
- **Rule:** role-fit (title + career evidence) must **gate** semantic/keyword score. A skill only
  "counts" if backed by tenure, endorsements, assessments, or corroborating job descriptions
  (a **skill-trust** multiplier).

### 2. Plain-language strong fits ("Tier 5s")
Genuine fits who **don't use the buzzwords**. E.g. someone who "built a recommendation system at a
product company" but never writes "RAG" or "Pinecone."

- **Tell-tale:** career_history `description` text describes building search / ranking /
  recommendation / retrieval / matching systems at **product companies**, with relevant tenure —
  even if the `skills` array is modest.
- **Rule:** mine the free-text `summary` and job `description` fields semantically; reward
  evidence of *building* relevant systems, not just listing skills. These should rank **high**.

### 3. Honeypots (~80, forced to tier 0)
Subtly **logically impossible** profiles. Examples from the spec:
- 8 years of experience at a company **founded 3 years ago**.
- "Expert" proficiency in 10 skills with **0 years/months used**.

- **Detection (logical-consistency checks):**
  - Sum/overlap of `career_history.duration_months` or a single role's tenure **exceeds**
    plausible bounds vs `years_of_experience` or company plausibility.
  - `skills[].proficiency = expert/advanced` with `duration_months = 0` (or tiny).
  - `skill_assessment_scores` contradicting claimed proficiency (e.g. expert but assessment ~0).
  - Education `end_year` / work `start_date` timeline impossibilities (e.g. working before graduating implausibly, or `start_date` after `end_date`).
  - `years_of_experience` inconsistent with career timeline (e.g. 8 YOE but earliest job 2 years ago).
  - Current role tenure longer than the candidate's total career.
- **Rule:** compute a `honeypot_score`; hard-demote (force to bottom / exclude from top 100).
- **Stakes:** >10% honeypots in top 100 = **disqualified**. Ranking them in top 10 = red flag.

### 4. Behavioral twins
Two profiles near-identical on paper but differing on **behavioral signals** (one active &
responsive, one dormant & unresponsive). The intent: the ranker must use behavioral signals to
separate otherwise-equal candidates.

- **Rule:** the behavioral-availability modifier (below) is the deciding signal between twins.

### 5. JD-stated negative signals & disqualifiers
The JD names cohorts to **down-rank or exclude**. Encode each:

| Signal | Detection heuristic | Action |
|--------|--------------------|--------|
| **Consulting-firm-only career** | All `career_history.company` ∈ {TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, …} with no product-company role | Strong down-weight (the JD says no). Prior product-company role → OK. |
| **Pure research-only, no production** | Academic/research-only titles & descriptions; no deployment language | Disqualify per JD. |
| **LangChain-only <12mo** | "AI experience" only recent LangChain/OpenAI wrapper work, no pre-LLM ML production | Strong down-weight unless deeper ML history. |
| **No code in 18+ months** | Senior whose recent roles are pure "architect"/"tech lead," no hands-on | Down-weight. |
| **Title-chaser** | Job-hopping ~every ≤1.5 yrs chasing senior titles | Down-weight. |
| **CV/speech/robotics primary, no NLP/IR** | Skills/career centered on vision/speech/robotics without NLP/retrieval | Down-weight. |
| **Closed proprietary 5+ yrs, no external validation** | No OSS/papers/talks signal, long closed tenure | Mild down-weight. |

### 6. Off-target geography / availability
JD wants Noida/Pune or relocatable-to-India Tier-1. Outside India without relocation willingness
is weaker fit (case-by-case; no visa sponsorship).

## The behavioral-availability modifier

Per the signals doc: behavioral signals are a **multiplier/modifier** on skill-match — a
qualified-but-unavailable candidate is, for hiring, not actually available.

Down-weight when:
- `last_active_date` is stale (e.g. dormant for months).
- `recruiter_response_rate` is very low (e.g. ~5%).
- `open_to_work_flag = false`.
- High `notice_period_days` (JD prefers ≤30; can buy out ≤30).
- Low `interview_completion_rate`.

Up-weight (mildly) when: active recently, high response rate, open to work, saved by recruiters,
healthy GitHub activity (for an eng role).

**Watch sentinels:** `github_activity_score = -1` and `offer_acceptance_rate = -1` mean "no
data," not "bad." Don't penalize them as low scores.

> Calibration risk: the modifier must **separate** candidates without **burying genuine fits**.
> Keep it a bounded multiplier, not a dominant term.

## Scoring composition (how the pieces combine)

A working mental model for the scorer (to be refined in [07_Architecture.md](07_Architecture.md)):

```
relevance      = semantic_fit(JD, profile+career text)        # contextual, not keyword
role_fit_gate  = title/career evidence of relevant work        # gates relevance
skill_trust    = f(endorsements, duration_months, assessments) # discounts stuffing
base_score     = relevance × role_fit_gate × skill_trust
penalties      = disqualifier/negative-signal multipliers (≤1)
behavior_mod   = bounded availability multiplier
honeypot       = hard demotion if honeypot_score high

final_score    = base_score × penalties × behavior_mod × (0 if honeypot else 1)
```

Then: sort by `final_score` desc, tie-break by candidate_id asc, take top 100, assign ranks.

## Validation strategy (no leaderboard)

Since there's no feedback signal, we validate the ranker by **logic and inspection**:
- Manually inspect the top 20 — are they genuinely senior AI/ML engineers at product companies?
- Confirm **zero** keyword-stuffers and **zero** honeypots in the top 50.
- Spot-check that plain-language fits surface (search for recsys/ranking builders with modest skills).
- Audit reasoning rows for the 6 manual-review checks before submitting.
