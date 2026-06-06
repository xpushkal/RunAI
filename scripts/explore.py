#!/usr/bin/env python3
"""M1 data exploration — full scan of candidates.jsonl.

Reports the distributions and trap/honeypot/genuine-fit cohorts documented in
Docs/08_M1_Findings.md. Read-only; stdlib only (no deps needed).

Usage:
    python scripts/explore.py [path/to/candidates.jsonl]
"""
import json
import statistics
import sys
from collections import Counter

DEFAULT_PATH = "India_runs_data_and_ai_challenge/candidates.jsonl"

# Core AI/IR/ML vocabulary that maps to the JD's real needs (retrieval, ranking, embeddings, LLMs).
AI_CORE = {
    "nlp", "rag", "retrieval", "embeddings", "embedding", "semantic search", "vector search",
    "information retrieval", "ranking", "learning to rank", "recommendation", "recommender",
    "fine-tuning llms", "lora", "qlora", "peft", "transformers", "llm", "sentence-transformers",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus", "elasticsearch", "opensearch", "bm25",
    "ndcg", "mrr", "xgboost", "pytorch", "tensorflow",
}
PRODUCT_INDS = {"software", "fintech", "e-commerce", "saas", "ai/ml", "food delivery", "edtech"}


def is_eng(title: str) -> bool:
    return any(k in title.lower() for k in ("engineer", "developer", "scientist"))


def is_ai_title(title: str) -> bool:
    return any(k in title.lower() for k in (
        "ai engineer", "ml engineer", "machine learning", "data scientist",
        "applied scientist", "research engineer", "nlp engineer", "ai research",
    ))


def count_ai_skills(skills) -> int:
    return sum(1 for s in skills if s.get("name", "").lower() in AI_CORE)


def honeypot_flags(c) -> set:
    """Precision-first logical-consistency checks (refined further in M4)."""
    p = c["profile"]
    yoe = p.get("years_of_experience", 0)
    skills = c.get("skills", [])
    sig = c["redrob_signals"]
    ch = c.get("career_history", [])
    total_career = sum(j.get("duration_months", 0) for j in ch)
    flags = set()
    for s in skills:
        if s.get("proficiency") in ("expert", "advanced") and s.get("duration_months", 0) == 0:
            flags.add("expert_0mo")
            break
    if total_career > yoe * 12 + 18:
        flags.add("career_gt_yoe")
    for j in ch:
        if j.get("is_current") and j.get("duration_months", 0) > total_career + 1:
            flags.add("currole_gt_career")
    sa = sig.get("skill_assessment_scores", {})
    for s in skills:
        if s.get("proficiency") == "expert" and s.get("name") in sa and sa[s["name"]] < 20:
            flags.add("expert_lowassess")
            break
    for j in ch:
        if j.get("start_date") and j.get("end_date") and j["start_date"] > j["end_date"]:
            flags.add("start_gt_end")
            break
    return flags


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    n = 0
    titles = Counter()
    countries = Counter()
    industries = Counter()
    ai_counts = []
    resp_rates = []
    gh_missing = offer_missing = 0
    stuffers = 0
    ai_title = ai_title_product = ai_title_5_9 = 0
    honey = Counter()
    honey_any = 0
    stuffer_ex, honey_ex, genuine_ex = [], [], []

    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            c = json.loads(line)
            n += 1
            p = c["profile"]
            t = p["current_title"]
            yoe = p.get("years_of_experience", 0)
            ind = p.get("current_industry", "").lower()
            skills = c.get("skills", [])
            sig = c["redrob_signals"]
            titles[t] += 1
            countries[p["country"]] += 1
            industries[p["current_industry"]] += 1
            aic = count_ai_skills(skills)
            ai_counts.append(aic)
            resp_rates.append(sig.get("recruiter_response_rate", 0))
            gh_missing += sig.get("github_activity_score", 0) == -1
            offer_missing += sig.get("offer_acceptance_rate", 0) == -1

            if aic >= 6 and not is_eng(t):
                stuffers += 1
                if len(stuffer_ex) < 8:
                    stuffer_ex.append((c["candidate_id"], t, aic))
            if is_ai_title(t):
                ai_title += 1
                if ind in PRODUCT_INDS:
                    ai_title_product += 1
                    if 5 <= yoe <= 9:
                        ai_title_5_9 += 1
                        if len(genuine_ex) < 10:
                            genuine_ex.append((c["candidate_id"], t, yoe, p["current_company"], ind))
            fl = honeypot_flags(c)
            if fl:
                honey_any += 1
                for x in fl:
                    honey[x] += 1
                if len(honey_ex) < 10:
                    honey_ex.append((c["candidate_id"], t, yoe, sorted(fl)))

    print(f"TOTAL: {n}\n")
    print("AI-skill count: mean", round(statistics.mean(ai_counts), 3),
          "| zero:", sum(1 for x in ai_counts if x == 0))
    print("keyword_stuffers (>=6 AI skills, non-eng title):", stuffers)
    print("AI/ML/DS titled:", ai_title, "| at product:", ai_title_product,
          "| product & 5-9y:", ai_title_5_9)
    print("honeypot-flagged (any):", honey_any, dict(honey))
    print("github==-1:", f"{100*gh_missing/n:.1f}%", "| offer==-1:", f"{100*offer_missing/n:.1f}%",
          "| resp_rate mean:", round(statistics.mean(resp_rates), 3))
    print("\nstuffer examples:", *stuffer_ex, sep="\n  ")
    print("\nhoneypot examples:", *honey_ex, sep="\n  ")
    print("\ngenuine-fit examples:", *genuine_ex, sep="\n  ")
    print("\ntop titles:", *titles.most_common(15), sep="\n  ")


if __name__ == "__main__":
    main()
