# Data Dictionary

**Sources:** `candidate_schema.json`, `redrob_signals_doc.docx`, `candidates.jsonl`,
plus our own scan of the pool.

## Files

| File | Size | Description |
|------|------|-------------|
| `candidates.jsonl` | ~487 MB | 100,000 candidates, one JSON object per line. The pool to rank. |
| `sample_candidates.json` | 300 KB | First ~50 candidates, pretty-printed (note: this file is a JSON array, while the full pool is JSONL). |
| `candidate_schema.json` | 8.8 KB | JSON Schema (draft-07) for one candidate record. |

> Note: the README references `candidates.jsonl.gz` (gzipped). In this bundle the file is already
> uncompressed as `candidates.jsonl` (100,000 lines confirmed).

## Candidate record structure

Top-level required fields: `candidate_id`, `profile`, `career_history`, `education`, `skills`,
`redrob_signals`. Optional: `certifications`, `languages`.

### `candidate_id`
- String, pattern `^CAND_[0-9]{7}$` (e.g. `CAND_0000001`). Unique.

### `profile` (object)
| Field | Type | Notes |
|-------|------|-------|
| anonymized_name | string | |
| headline | string | One-line professional headline. |
| summary | string | Multi-sentence summary (free text — rich signal). |
| location | string | City, region. |
| country | string | |
| years_of_experience | number | 0–50. |
| current_title | string | **Key role signal.** |
| current_company | string | |
| current_company_size | enum | `1-10 … 10001+` (8 buckets). |
| current_industry | string | |

### `career_history` (array, 1–10 items)
Each job:
| Field | Type | Notes |
|-------|------|-------|
| company | string | |
| title | string | |
| start_date / end_date | date / null | `end_date` null when current. |
| duration_months | integer ≥ 0 | |
| is_current | boolean | |
| industry | string | |
| company_size | enum | same 8 buckets. |
| description | string | **Free text — primary evidence of what they actually built.** |

### `education` (array, 0–5 items)
| Field | Type | Notes |
|-------|------|-------|
| institution, degree, field_of_study | string | |
| start_year / end_year | integer | 1970–2035. |
| grade | string / null | GPA/percentage/class. |
| tier | enum | `tier_1…tier_4`, `unknown` (institution prestige). |

### `skills` (array, 0+)
| Field | Type | Notes |
|-------|------|-------|
| name | string | |
| proficiency | enum | beginner/intermediate/advanced/expert. |
| endorsements | integer ≥ 0 | Social proof. |
| duration_months | integer ≥ 0 | **Months used — key for skill-trust / honeypot detection.** |

### `certifications` (array, optional)
- name, issuer, year.

### `languages` (array, optional)
- language; proficiency ∈ basic/conversational/professional/native.

## The 23 behavioral signals (`redrob_signals`)

These describe whether a candidate is actually *available and hireable*, not just qualified.
The signals doc says to use them as a **multiplier/modifier** on top of skill-match scoring.

| # | Signal | Range / type | Meaning |
|---|--------|--------------|---------|
| 1 | profile_completeness_score | 0–100 | How complete the profile is. |
| 2 | signup_date | date | When they signed up. |
| 3 | last_active_date | date | **Last login — recency = availability.** |
| 4 | open_to_work_flag | bool | Marked available. |
| 5 | profile_views_received_30d | int ≥ 0 | Recruiter views in 30d. |
| 6 | applications_submitted_30d | int ≥ 0 | Roles applied to recently. |
| 7 | recruiter_response_rate | 0.0–1.0 | **Fraction of recruiter messages replied to.** |
| 8 | avg_response_time_hours | number ≥ 0 | Median response time. |
| 9 | skill_assessment_scores | dict[str→0–100] | Per-skill platform assessment scores. |
| 10 | connection_count | int ≥ 0 | Redrob connections. |
| 11 | endorsements_received | int ≥ 0 | Total endorsements. |
| 12 | notice_period_days | 0–180 | Stated notice period (JD prefers ≤30). |
| 13 | expected_salary_range_inr_lpa.min/.max | number ≥ 0 | Salary expectation (LPA). |
| 14 | preferred_work_mode | enum | onsite/hybrid/remote/flexible. |
| 15 | willing_to_relocate | bool | Relocation willingness (matters for Noida/Pune). |
| 16 | github_activity_score | -1–100 | Commits/PRs/stars in 12mo; **-1 = no GitHub linked.** |
| 17 | search_appearance_30d | int ≥ 0 | Times in recruiter searches. |
| 18 | saved_by_recruiters_30d | int ≥ 0 | Bookmarked by recruiters. |
| 19 | interview_completion_rate | 0.0–1.0 | Fraction of interviews attended. |
| 20 | offer_acceptance_rate | -1–1.0 | Past offer acceptance; **-1 = no history.** |
| 21 | verified_email | bool | |
| 22 | verified_phone | bool | |
| 23 | linkedin_connected | bool | |

> Watch the sentinel values: `github_activity_score = -1` and `offer_acceptance_rate = -1` mean
> "no data," **not** "bad." Treat them as missing, not as low scores.

## Observed pool statistics (scan of first 20,000 candidates)

### Current title distribution (top)
Non-AI roles dominate the pool. AI/ML/Data titles are a small minority.

```
Mechanical Engineer  1216      Software Engineer    658
HR Manager           1194      Mobile Developer     603
Content Writer       1165      DevOps Engineer      568
Business Analyst     1164      Frontend Engineer    565
Sales Executive      1158      Full Stack Developer 555
Customer Support     1153      QA Engineer          541
Accountant           1152      Java Developer       539
Civil Engineer       1137      Cloud Engineer       523
Graphic Designer     1132      .NET Developer       517
Operations Manager   1119      Data Engineer        159
Project Manager      1114      Senior Data Engineer 158
Marketing Manager    1087      Analytics Engineer   151
                               Data Analyst         148
```

**Implication:** the genuine "Senior AI Engineer" cohort is rare. Many top-skill-keyword
profiles are attached to off-role titles (HR Manager, Content Writer) — these are the traps.

### Country distribution (top)
```
India 15006   USA 2013   Canada 527   Australia 527
Singapore 487   UK 484   UAE 479   Germany 477
```
~75% India. The JD strongly prefers Noida/Pune (or relocatable-to-India Tier-1 cities).

### Industry distribution (top)
```
IT Services 5935   Software 4604   Manufacturing 4349   Conglomerate 1479
Paper Products 1477   Fintech 592   Food Delivery 507   E-commerce 316
Consulting 266   EdTech 130   SaaS 70   AI/ML 63
```
**Implication:** "product company" vs "services/consulting" is a meaningful, learnable split
(IT Services + Consulting + Conglomerate lean services; Software/Fintech/E-commerce/SaaS lean product).
