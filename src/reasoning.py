"""Fact-grounded reasoning generation (M2 baseline; refined in M6).

Builds a 1-2 sentence justification per ranked candidate strictly from facts in
the candidate's own profile — never inventing skills or employers. Tone tracks
the rank, and an honest concern is surfaced when the profile shows one. Designed
to satisfy the Stage-4 manual-review checks (Docs/04_Submission_Requirements.md).

No network / no LLM at runtime — pure deterministic templating.
"""
from __future__ import annotations


def _exp_phrase(yoe) -> str:
    try:
        return f"{float(yoe):.1f} yrs"
    except (TypeError, ValueError):
        return "experience n/a"


def _concerns(feat: dict) -> list[str]:
    """Honest concerns drawn from real signals."""
    facts = feat["facts"]
    out = []
    rr = facts.get("recruiter_response_rate")
    if rr is not None and rr < 0.2:
        out.append(f"low recruiter response rate ({rr:.0%})")
    np_ = facts.get("notice_period_days")
    if np_ is not None and np_ > 60:
        out.append(f"{np_}-day notice period")
    if facts.get("open_to_work") is False:
        out.append("not flagged open-to-work")
    if facts.get("country", "").lower() != "india" and not facts.get("willing_to_relocate"):
        out.append("outside India and not marked willing to relocate")
    yoe = facts.get("years_of_experience") or 0
    if yoe and yoe < 5:
        out.append(f"only {yoe:.1f} yrs experience (below the 5-9 band)")
    elif yoe and yoe > 9:
        out.append(f"{yoe:.1f} yrs experience (above the 5-9 band)")
    if feat["skill_trust"] < 0.2 and feat["career_fit"] >= 0.5:
        out.append("relevant work shown in roles but few corroborated AI skills listed")
    return out


def generate(feat: dict) -> str:
    """One reasoning string for a ranked candidate."""
    facts = feat["facts"]
    title = facts.get("current_title", "candidate")
    company = facts.get("current_company", "")
    industry = facts.get("current_industry", "")
    yoe = _exp_phrase(facts.get("years_of_experience"))
    top_skills = facts.get("top_skills") or []
    rank = feat.get("rank", 0)

    # Lead clause: who they are.
    at = f" at {company}" if company else ""
    lead = f"{title}{at} with {yoe}"

    # Evidence clause: why they fit (career evidence and/or corroborated skills).
    evidence = []
    if feat["career_fit"] >= 0.5:
        evidence.append("career history shows building search/ranking/ML systems")
    if top_skills:
        evidence.append("corroborated skills in " + ", ".join(top_skills))
    if industry:
        evidence.append(f"{industry} background")
    evidence_str = "; ".join(evidence) if evidence else "adjacent experience"

    concerns = _concerns(feat)
    # Tone tracks rank: top ranks lead with strength; lower ranks hedge.
    if rank <= 10:
        sentence = f"{lead}; {evidence_str}."
    elif rank <= 50:
        sentence = f"{lead} — {evidence_str}."
    else:
        sentence = f"{lead}; {evidence_str}, but a weaker overall match."

    if concerns:
        sentence += " Concern: " + concerns[0] + "."
    return sentence
