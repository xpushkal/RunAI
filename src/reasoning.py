"""Fact-grounded reasoning generation.

Builds a 1-2 sentence justification per ranked candidate strictly from facts in
the candidate's own profile — never inventing skills or employers. The generator
targets the six Stage-4 manual-review checks (Docs/04_Submission_Requirements.md):

  specific facts · JD connection · honest concerns · no hallucination ·
  variation (across rows) · rank consistency (tone tracks rank)

Variation comes from (a) rotating sentence skeletons by a stable per-candidate
hash and (b) selecting whichever JD-connected evidence each candidate actually
has. No network / no LLM at runtime — pure deterministic templating.
"""
from __future__ import annotations

import zlib

# Display normalisation for career-evidence tokens (lexicon stems -> readable text).
_PRETTY = {
    "rag": "RAG", "llm": "LLM", "nlp": "NLP", "ctr": "click-through",
    "ndcg": "NDCG", "fine-tun": "fine-tuning", "a/b test": "A/B testing",
    "ab test": "A/B testing", "recommender": "recommender systems",
    "natural language": "NLP",
}


def _pretty(term: str) -> str:
    return _PRETTY.get(term, term)


def _exp_phrase(yoe) -> str:
    try:
        return f"{float(yoe):.1f} yrs"
    except (TypeError, ValueError):
        return "unspecified tenure"


def _join(items: list[str]) -> str:
    items = [i for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _cap(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


def _fit_clause(facts: dict, feat: dict) -> str:
    """JD-connected evidence the candidate actually has. Picks the strongest few."""
    bits: list[str] = []
    if facts.get("career_evidence"):
        bits.append("career history shows " + _join([_pretty(t) for t in facts["career_evidence"]]) + " work")
    if facts.get("vector_db_skills"):
        bits.append("hands-on with " + _join(facts["vector_db_skills"]))
    if facts.get("eval_skills"):
        bits.append("ranking-evaluation exposure (" + _join(facts["eval_skills"]) + ")")
    if facts.get("top_skills") and len(bits) < 2:
        bits.append("corroborated skills in " + _join(facts["top_skills"]))
    if facts.get("is_product") and facts.get("current_industry") and len(bits) < 3:
        bits.append(f"product-company background ({facts['current_industry']})")
    if not bits:
        bits.append("adjacent experience relevant to the role")
    return "; ".join(bits[:3])


def _first_concern(facts: dict, feat: dict) -> str | None:
    rr = facts.get("recruiter_response_rate")
    if rr is not None and rr < 0.2:
        return f"low recruiter response rate ({rr:.0%})"
    np_ = facts.get("notice_period_days")
    if np_ is not None and np_ > 60:
        return f"{np_}-day notice period"
    if facts.get("open_to_work") is False:
        return "not currently flagged open-to-work"
    if facts.get("country", "").lower() != "india" and not facts.get("willing_to_relocate"):
        return "based outside India and not marked willing to relocate"
    yoe = facts.get("years_of_experience") or 0
    if yoe and yoe < 5:
        return f"only {yoe:.1f} yrs (below the JD's 5-9 band)"
    if yoe and yoe > 9:
        return f"{yoe:.1f} yrs (above the JD's 5-9 band)"
    if feat.get("skill_trust", 1) < 0.2 and feat.get("career_fit", 0) >= 0.5:
        return "few corroborated AI skills listed, though the roles show relevant work"
    return None


def _tail_sentence(facts: dict, feat: dict, rank: int) -> str:
    """A closing sentence: an honest concern, or a behavioural positive, or ''."""
    concern = _first_concern(facts, feat)
    if concern:
        return "Concern: " + concern + "."
    rr = facts.get("recruiter_response_rate")
    if rank <= 25 and rr is not None and rr >= 0.5 and facts.get("open_to_work"):
        return f"Active and responsive ({rr:.0%} recruiter response, open to work)."
    gh = facts.get("github_activity_score")
    if rank <= 25 and gh is not None and gh >= 40:
        return f"Healthy GitHub activity ({gh:.0f}/100)."
    return ""


def generate(feat: dict) -> str:
    facts = feat["facts"]
    rank = feat.get("rank", 0)
    title = facts.get("current_title", "Candidate")
    company = facts.get("current_company", "")
    yoe = _exp_phrase(facts.get("years_of_experience"))

    at = f" at {company}" if company else ""
    lead = f"{title}{at} with {yoe}"
    fit = _fit_clause(facts, feat)
    tail = _tail_sentence(facts, feat, rank)

    # Stable per-candidate skeleton choice -> variation across sampled rows.
    # zlib.crc32 is deterministic across runs (unlike built-in hash()).
    variant = zlib.crc32(feat["candidate_id"].encode()) % 3

    hedge = ", though a more adjacent than exact match" if rank > 50 else ""

    if variant == 0:
        main = f"{lead}. {_cap(fit)}{hedge}."
    elif variant == 1:
        main = f"{lead} — {fit}{hedge}."
    else:
        main = f"{_cap(fit)}. {lead}{hedge}."

    text = main + (" " + tail if tail else "")
    return " ".join(text.split())  # collapse incidental double spaces
