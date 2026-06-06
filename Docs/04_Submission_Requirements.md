# Submission Requirements

**Source:** `submission_spec.docx`, `submission_metadata_template.yaml`, `validate_submission.py`,
`sample_submission.csv`.

## 1. The output CSV

- **One file**, named `<participant_id>.csv` (e.g. `team_xxx.csv`). Must end in `.csv`.
- **UTF-8** encoded.
- **Row 1 = header**, exactly: `candidate_id,rank,score,reasoning`
- **Rows 2–101 = exactly 100 data rows.**

### Columns

| Column | Type | Required | Rules |
|--------|------|----------|-------|
| candidate_id | string | ✅ | Must match `^CAND_[0-9]{7}$` and exist in `candidates.jsonl`. Unique (no duplicates). |
| rank | int 1–100 | ✅ | Each integer 1–100 appears exactly once. |
| score | float | ✅ | **Non-increasing** as rank increases (rank1 ≥ rank2 ≥ …). Ties allowed. |
| reasoning | string | ⚠ optional but strongly recommended | 1–2 sentence justification. |

### Ordering & tie-break rules (enforced by validator)
- `score` must be **monotonically non-increasing** by rank.
- On equal scores, **candidate_id must be ascending** (the validator checks this exact tie-break).
- So: sort by score desc, then candidate_id asc, then assign ranks 1..100.

### What the validator (`validate_submission.py`) checks
- `.csv` extension, non-empty filename stem, UTF-8.
- Header is exactly the 4 required columns in order.
- Exactly 100 non-empty data rows.
- Each row has 4 columns; candidate_id matches the pattern; no duplicate ids.
- rank is an integer 1–100, each used exactly once (reports missing ranks).
- score parses as float.
- score non-increasing by rank; equal-score rows ordered by candidate_id ascending.

Run it before every upload:
```
python validate_submission.py <participant_id>.csv
```

## 2. Compute constraints (the ranking step)

| Constraint | Limit |
|------------|-------|
| Total runtime | ≤ 5 minutes wall-clock |
| Memory | ≤ 16 GB RAM |
| Compute | CPU only — no GPU |
| Network | Off — no external/hosted-LLM API calls (OpenAI, Anthropic, Cohere, Gemini, etc.) |
| Disk | ≤ 5 GB intermediate state |

- **Pre-computation** (embeddings, indexes, model weights) **may exceed 5 min**, but must be
  documented/scripted. The **ranking step that emits the CSV** must finish within 5 min.
- Running a per-candidate LLM call over 100k candidates will not fit — use a small ranker over
  precomputed features/indexes/compact local models.
- Enforced at Stage 3 inside a sandboxed Docker container; cannot-reproduce = disqualified.

## 3. The reasoning column (manual review, Stage 4)

10 random rows are sampled and each reasoning is checked for:

| Check | What they want |
|-------|----------------|
| Specific facts | References real profile facts (years, title, named skills, signal values). |
| JD connection | Connects to specific JD requirements, not generic praise. |
| Honest concerns | Acknowledges obvious gaps/concerns where present. |
| No hallucination | Every claim corresponds to something actually in the profile. |
| Variation | The 10 sampled reasonings are substantively different (not templated). |
| Rank consistency | Tone matches rank (no critical rank-5 or glowing rank-95). |

**Penalized:** empty, all-identical, name-insert templates, hallucinated skills, rank-contradicting reasoning.

## 4. Deliverables (the full submission)

Three required parts:

### 4.1 The CSV
Top-100 ranking per Sections 1–2 above.

### 4.2 Portal metadata (have ready at upload)
Team name; primary contact name/email/phone; team member list; GitHub repo URL; sandbox/demo
link; AI tools declared (multi-select, honest, not penalized); compute environment summary;
methodology summary (≤200 words, optional but recommended). Mirror these in a
`submission_metadata.yaml` at repo root (template: `submission_metadata_template.yaml`).

### 4.3 Code repository
- Clear `README.md` with setup + exact reproduce commands.
- Full source that produced the CSV (no hidden steps / manual edits).
- Any precomputed artifacts (embeddings/indexes/weights) **or** a script to produce them.
- `requirements.txt` / `pyproject.toml` with pinned versions.
- `submission_metadata.yaml` at repo root.
- A **single reproduce command**, e.g.:
  `python rank.py --candidates ./candidates.jsonl --out ./submission.csv`

### 4.4 Sandbox / demo link (mandatory)
A hosted environment that runs the ranker on a small sample (≤100 candidates), end-to-end,
within budget. Acceptable: HuggingFace Spaces, Streamlit Cloud, Replit, Google Colab,
`docker pull`+`docker run`, or Binder. Alternatively a self-contained `docker run` recipe in the
README that builds/runs unmodified. Missing sandbox = flagged at Stage 1.

## 5. Submission policy

- **3 submissions max.** Last valid submission counts. No live leaderboard, no per-submission feedback.
- Validate locally; don't burn submissions probing the scorer.

## 6. Pre-submit checklist

- [ ] CSV named `<participant_id>.csv`, UTF-8.
- [ ] Header exactly `candidate_id,rank,score,reasoning`.
- [ ] Exactly 100 data rows.
- [ ] Ranks 1–100 each once; no duplicate candidate_ids; all ids exist in pool.
- [ ] Scores non-increasing; equal scores ordered by candidate_id ascending.
- [ ] `validate_submission.py` passes with no errors.
- [ ] Reasoning is specific, varied, honest, non-hallucinated, rank-consistent.
- [ ] Ranking step runs ≤5 min, ≤16 GB, CPU-only, no network — verified locally.
- [ ] Repo: README + source + requirements + metadata YAML + reproduce command.
- [ ] Working sandbox link (or docker recipe).
- [ ] Honeypot rate in top 100 well under 10%.
- [ ] Git history shows real iteration (not a single dump).
