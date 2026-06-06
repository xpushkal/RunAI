"""Per-candidate structured feature extraction.

Each candidate is reduced to a small set of interpretable components in [0,1]
(plus a behavioral multiplier and penalty/honeypot signals) that the scorer
combines. Every component is grounded in the JD (see src/jd.py) and the M1
findings (Docs/08_M1_Findings.md).

The structured features here are the *whole* ranker at M2 (no embeddings yet);
from M3 a semantic `relevance` term is blended in via src/score.py.
"""
from __future__ import annotations

from datetime import date, datetime

from . import jd

# Reference "today" for recency math (matches the dataset's recent activity window).
REFERENCE_DATE = date(2026, 6, 6)

PROFICIENCY_WEIGHT = {"beginner": 0.3, "intermediate": 0.6, "advanced": 0.85, "expert": 1.0}


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _lower(s) -> str:
    return s.lower() if isinstance(s, str) else ""


def _parse_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _saturate(x: float, cap: float) -> float:
    return min(1.0, x / cap) if cap > 0 else 0.0


def _any_term(text: str, terms) -> bool:
    return any(t in text for t in terms)


# ---------------------------------------------------------------------------
# component features
# ---------------------------------------------------------------------------
def title_fit(c: dict) -> float:
    """How well the candidate's titles match the role. Best over current + history."""
    titles = [_lower(c.get("profile", {}).get("current_title", ""))]
    titles += [_lower(j.get("title", "")) for j in c.get("career_history", [])]
    best = 0.05
    for t in titles:
        if not t:
            continue
        if _any_term(t, jd.STRONG_TITLE_TERMS):
            best = max(best, 1.0)
        elif _any_term(t, jd.ADJACENT_TITLE_TERMS):
            best = max(best, 0.55)
        elif _any_term(t, jd.ENG_TITLE_TERMS):
            best = max(best, 0.30)
    return best


def career_fit(c: dict) -> float:
    """Evidence in free-text that the candidate *built* relevant systems.

    This is what lets a plain-language Tier-5 candidate surface even with a thin
    skills list — and what keyword-stuffers (off-role descriptions) fail.
    """
    blob = _lower(c.get("profile", {}).get("summary", ""))
    for j in c.get("career_history", []):
        blob += " " + _lower(j.get("description", ""))
    hits = sum(1 for term in jd.CAREER_EVIDENCE_TERMS if term in blob)
    return _saturate(hits, 4)  # ~4 distinct evidence terms => full credit


def skill_trust(c: dict) -> tuple[float, list[str]]:
    """Corroborated AI-skill strength. Discounts keyword stuffing (0 endorsements,
    0 duration, no assessment). Returns (trust in [0,1], top corroborated skill names).
    """
    assessments = c.get("redrob_signals", {}).get("skill_assessment_scores", {}) or {}
    scored = []
    for s in c.get("skills", []):
        name = s.get("name", "")
        if _lower(name) not in jd.CORE_AI_SKILLS:
            continue
        prof = PROFICIENCY_WEIGHT.get(s.get("proficiency", ""), 0.3)
        endorse = _saturate(s.get("endorsements", 0), 25)
        dur = _saturate(s.get("duration_months", 0), 36)
        if name in assessments:
            assess = assessments[name] / 100.0
        else:
            assess = 0.55  # neutral when no assessment exists
        corroboration = 0.34 * endorse + 0.33 * dur + 0.33 * assess
        scored.append((prof * corroboration, name))
    if not scored:
        return 0.0, []
    scored.sort(reverse=True)
    # Sum of top corroborated skills, saturating (a coherent handful beats a long stuffed list).
    trust = _saturate(sum(v for v, _ in scored[:5]) * 1.6, 3.0)
    top_names = [n for _, n in scored[:3]]
    return trust, top_names


def experience_fit(c: dict, cfg: dict) -> float:
    yoe = c.get("profile", {}).get("years_of_experience", 0) or 0
    lo = cfg["scoring"]["experience"]["ideal_min"]
    hi = cfg["scoring"]["experience"]["ideal_max"]
    falloff = cfg["scoring"]["experience"]["soft_falloff_years"]
    if lo <= yoe <= hi:
        return 1.0
    dist = (lo - yoe) if yoe < lo else (yoe - hi)
    return max(0.3, 1.0 - dist / falloff)  # YOE is a guideline; keep a floor


def location_fit(c: dict, cfg: dict) -> float:
    loc = cfg["scoring"]["location"]
    country = _lower(c.get("profile", {}).get("country", ""))
    if country == "india":
        return loc["in_country_bonus"]
    if c.get("redrob_signals", {}).get("willing_to_relocate"):
        return loc["relocatable_bonus"]
    return loc["out_of_scope"]


def behavior_modifier(c: dict, cfg: dict) -> float:
    """Bounded availability multiplier. -1 sentinels are treated as missing, not low."""
    b = cfg["behavior_modifier"]
    sig = c.get("redrob_signals", {})
    quality = []

    last = _parse_date(sig.get("last_active_date"))
    if last:
        days = (REFERENCE_DATE - last).days
        if days <= 30:
            quality.append(1.0)
        elif days >= b["stale_days"]:
            quality.append(0.2)
        else:
            quality.append(1.0 - 0.8 * (days - 30) / (b["stale_days"] - 30))

    rr = sig.get("recruiter_response_rate")
    if rr is not None:
        quality.append(min(1.0, rr / 0.6))  # 0.6+ response rate is "good"

    if sig.get("open_to_work_flag") is not None:
        quality.append(1.0 if sig.get("open_to_work_flag") else 0.4)

    notice = sig.get("notice_period_days")
    if notice is not None:
        quality.append(1.0 if notice <= 30 else max(0.4, 1.0 - (notice - 30) / 150))

    icr = sig.get("interview_completion_rate")
    if icr is not None and icr >= 0:
        quality.append(icr)

    if not quality:
        return 1.0
    q = sum(quality) / len(quality)  # in [0,1]
    return b["min"] + (b["max"] - b["min"]) * q


def negative_penalty(c: dict, cfg: dict) -> tuple[float, list[str]]:
    """Multiplicative penalty for JD 'do not want' signals. Expanded in M4.

    Returns (penalty multiplier in (0,1], list of fired flags).
    """
    pen = cfg["penalties"]
    flags = []
    mult = 1.0

    companies = [_lower(j.get("company", "")) for j in c.get("career_history", [])]
    companies.append(_lower(c.get("profile", {}).get("current_company", "")))
    industries = [_lower(j.get("industry", "")) for j in c.get("career_history", [])]
    industries.append(_lower(c.get("profile", {}).get("current_industry", "")))

    # Consulting-only: every employer is a consulting firm, none product.
    nonempty = [x for x in companies if x]
    if nonempty and all(any(f in comp for f in jd.CONSULTING_FIRMS) for comp in nonempty):
        flags.append("consulting_only")
        mult *= pen["consulting_only"]

    # CV/speech/robotics-primary without NLP/IR: skills dominated by vision/speech, no core AI.
    skill_names = [_lower(s.get("name", "")) for s in c.get("skills", [])]
    cv_hits = sum(1 for s in skill_names if _any_term(s, jd.CV_SPEECH_ROBOTICS_TERMS))
    core_hits = sum(1 for s in skill_names if s in jd.CORE_AI_SKILLS)
    if cv_hits >= 3 and core_hits == 0:
        flags.append("cv_speech_only")
        mult *= pen["cv_speech_only"]

    return mult, flags


def honeypot_signal(c: dict, cfg: dict) -> tuple[float, list[str]]:
    """Precision-first logical-consistency checks. Expanded in M4.

    Returns (honeypot_score in [0,1], list of fired checks).
    """
    p = c.get("profile", {})
    yoe = p.get("years_of_experience", 0) or 0
    skills = c.get("skills", [])
    sig = c.get("redrob_signals", {})
    ch = c.get("career_history", [])
    total_career = sum(j.get("duration_months", 0) for j in ch)
    flags = []

    for s in skills:
        if s.get("proficiency") in ("expert", "advanced") and s.get("duration_months", 0) == 0:
            flags.append("expert_0mo")
            break
    if total_career > yoe * 12 + 18:
        flags.append("career_gt_yoe")
    for j in ch:
        if j.get("is_current") and j.get("duration_months", 0) > total_career + 1:
            flags.append("currole_gt_career")
            break
    assessments = sig.get("skill_assessment_scores", {}) or {}
    for s in skills:
        if s.get("proficiency") == "expert" and s.get("name") in assessments \
                and assessments[s["name"]] < 20:
            flags.append("expert_lowassess")
            break
    for j in ch:
        sd, ed = j.get("start_date"), j.get("end_date")
        if sd and ed and sd > ed:
            flags.append("start_gt_end")
            break

    score = min(1.0, 0.5 * len(flags))  # one strong flag = 0.5 (== threshold default)
    return score, flags


# ---------------------------------------------------------------------------
# top-level extraction
# ---------------------------------------------------------------------------
def extract(c: dict, cfg: dict) -> dict:
    """Return all components plus raw facts (for reasoning) for one candidate."""
    p = c.get("profile", {})
    tf = title_fit(c)
    cf = career_fit(c)
    st, top_skills = skill_trust(c)
    ef = experience_fit(c, cfg)
    lf = location_fit(c, cfg)
    bm = behavior_modifier(c, cfg)
    pen, neg_flags = negative_penalty(c, cfg)
    hp_score, hp_flags = honeypot_signal(c, cfg)
    sig = c.get("redrob_signals", {})

    return {
        "candidate_id": c["candidate_id"],
        "title_fit": tf,
        "career_fit": cf,
        "skill_trust": st,
        "experience_fit": ef,
        "location_fit": lf,
        "behavior_mod": bm,
        "penalty": pen,
        "negative_flags": neg_flags,
        "honeypot_score": hp_score,
        "honeypot_flags": hp_flags,
        # raw facts for reasoning / inspection
        "facts": {
            "current_title": p.get("current_title", ""),
            "current_company": p.get("current_company", ""),
            "current_industry": p.get("current_industry", ""),
            "country": p.get("country", ""),
            "years_of_experience": p.get("years_of_experience", 0),
            "top_skills": top_skills,
            "recruiter_response_rate": sig.get("recruiter_response_rate"),
            "last_active_date": sig.get("last_active_date"),
            "open_to_work": sig.get("open_to_work_flag"),
            "notice_period_days": sig.get("notice_period_days"),
            "willing_to_relocate": sig.get("willing_to_relocate"),
        },
    }
