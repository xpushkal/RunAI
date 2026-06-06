# Challenge Brief

**Source:** `README.docx`, `job_description.docx` (official bundle).

## The mission

Develop a robust, workable Proof of Concept that doesn't just *filter* but *intelligently
ranks* candidates. The system should act as the ultimate AI recruiter, capable of:

- **Deep Job Understanding** — interpreting complex, nuanced job descriptions.
- **Contextual Relevance** — seeing beyond keywords to understand semantic fit.
- **Signal Integration** — leveraging all data: profile attributes, career metadata, and
  crucial activity/behavioral signals.
- **The Output** — delivering a fast, highly accurate, expertly ranked shortlist of best-fit
  candidates.

No fixed architecture is mandated.

## The job description we rank against

**Role:** Senior AI Engineer — Founding Team
**Company:** Redrob AI (Series A, AI-native talent-intelligence platform)
**Location:** Pune/Noida, India (hybrid, flexible) — open to relocation from Tier-1 Indian cities.
**Experience:** 5–9 years (a guideline, not a hard rule).

### What the role actually needs
A blend of two modes in one person:
1. **Deep technical depth in modern ML systems** — embeddings, retrieval, ranking, LLMs, fine-tuning.
2. **Scrappy product-engineering attitude** — ships a working ranker in a week; tilts toward
   "shipper" over "researcher."

The mandate: own the **intelligence layer** (ranking, retrieval, matching). First 90 days:
audit current BM25 + rule-based system → ship a v2 (embeddings, hybrid retrieval, LLM re-ranking)
→ build evaluation infra (offline benchmarks, A/B testing, recruiter feedback).

### Things you absolutely need (must-haves)
- **Production embeddings-based retrieval** (sentence-transformers, OpenAI embeddings, BGE, E5,
  or similar) deployed to real users — handled drift, index refresh, retrieval-quality regression.
- **Production vector DB / hybrid search** (Pinecone, Weaviate, Qdrant, Milvus, OpenSearch,
  Elasticsearch, FAISS, or similar) — operational experience.
- **Strong Python** (code quality matters).
- **Evaluation frameworks for ranking** — NDCG, MRR, MAP, offline↔online correlation, A/B tests.

### Nice-to-have (won't reject for)
- LLM fine-tuning (LoRA/QLoRA/PEFT); learning-to-rank (XGBoost/neural); HR-tech/marketplace
  exposure; distributed systems / large-scale inference; open-source AI/ML contributions.

### Things they explicitly do NOT want (negative signals)
- **Title-chasers** — job-hop every ~1.5 years optimizing for titles.
- **Framework enthusiasts** — GitHub full of LangChain tutorials / "how I used [hot framework]" demos.
- **Consulting-firm-only careers** — entire career at TCS/Infosys/Wipro/Accenture/Cognizant/
  Capgemini etc. (prior product-company experience makes it fine).
- **CV / speech / robotics primary expertise without significant NLP/IR exposure.**
- **5+ years entirely on closed proprietary systems** with no external validation (papers/talks/OSS).

### Hard disqualifiers (stated)
- Pure research / academic-only with **no production deployment**.
- "AI experience" that is mostly recent (<12 months) **LangChain-calling-OpenAI**, unless
  substantial pre-LLM ML production experience.
- Senior who **hasn't written production code in 18+ months** (moved to "architecture"/"tech lead").

### The "ideal candidate" (reading between the lines)
- ~6–8 years total, of which 4–5 in **applied ML/AI at product companies** (not services).
- Shipped ≥1 end-to-end **ranking / search / recommendation** system to real users at scale.
- Strong, defensible opinions on retrieval, evaluation, and LLM integration.
- In or willing to relocate to **Noida/Pune**.
- **Active on the platform** / clearly in the job market (so they can actually be contacted).

## The explicit note to hackathon participants (most important)

> The "right answer" is **not** "find candidates whose skills section contains the most AI
> keywords." That's a trap built into the dataset.
>
> The right answer involves reasoning about the gap between what the JD *says* and what it
> *means*. A "Tier 5" candidate may never write "RAG" or "Pinecone," but if their career history
> shows they built a recommendation system at a product company, they're a fit. A candidate with
> all the AI keywords as skills but whose title is "Marketing Manager" is **not** a fit.
>
> Weigh behavioral signals: a perfect-on-paper candidate who hasn't logged in for 6 months with a
> 5% recruiter response rate is, for hiring purposes, **not actually available** — down-weight them.

See [06_Traps_and_Honeypots.md](06_Traps_and_Honeypots.md) for how this maps to concrete rules.
