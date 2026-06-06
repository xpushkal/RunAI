"""JD encoding — turns the 'Senior AI Engineer' job description into structured,
testable requirements and the lexicons used by feature extraction.

Grounded in Docs/02_Challenge_Brief.md and Docs/06_Traps_and_Honeypots.md.
"""
from __future__ import annotations

# ----------------------------------------------------------------------------
# Role / title lexicons
# ----------------------------------------------------------------------------
# Titles that strongly match the role (the JD wants applied AI/ML engineers).
STRONG_TITLE_TERMS = (
    "machine learning", "ml engineer", "ai engineer", "applied scientist",
    "data scientist", "research engineer", "nlp engineer", "ai research",
    "search engineer", "ranking", "recommendation", "research scientist",
)
# Adjacent eng titles — plausible plain-language fits if their career shows relevant work.
ADJACENT_TITLE_TERMS = (
    "data engineer", "analytics engineer", "backend engineer", "software engineer",
    "full stack", "platform engineer", "data analyst", "big data",
)
# Generic eng signal (used to separate engineers from clearly off-role profiles).
ENG_TITLE_TERMS = ("engineer", "developer", "scientist", "programmer", "architect")

# ----------------------------------------------------------------------------
# Skill / capability lexicons (map to the JD's *real* needs, not buzzword count)
# ----------------------------------------------------------------------------
# Core IR/ranking/retrieval skills — the heart of the role.
CORE_AI_SKILLS = {
    "nlp", "rag", "retrieval", "embeddings", "embedding", "semantic search",
    "vector search", "information retrieval", "ranking", "learning to rank",
    "recommendation", "recommender", "fine-tuning llms", "lora", "qlora", "peft",
    "transformers", "llm", "sentence-transformers", "faiss", "pinecone", "weaviate",
    "qdrant", "milvus", "elasticsearch", "opensearch", "bm25", "ndcg", "mrr",
    "xgboost", "pytorch", "tensorflow",
}
# Vector DB / hybrid-search infra (JD must-have).
VECTOR_DB_SKILLS = {
    "pinecone", "weaviate", "qdrant", "milvus", "faiss", "elasticsearch",
    "opensearch", "vector search", "vector database",
}
# Evaluation-framework signal (JD must-have).
EVAL_SKILLS = {"ndcg", "mrr", "map", "a/b testing", "ab testing", "learning to rank"}

# Career-history evidence: phrases that indicate *building* relevant systems.
# These let plain-language Tier-5 candidates surface even with a thin skills list.
CAREER_EVIDENCE_TERMS = (
    "recommendation system", "recommender", "ranking system", "search system",
    "search engine", "retrieval", "semantic search", "vector search", "embeddings",
    "information retrieval", "personalization", "relevance", "matching system",
    "learning to rank", "rag", "fine-tun", "llm", "nlp", "natural language",
    "elasticsearch", "opensearch", "faiss", "recommendation engine", "ranker",
    "a/b test", "ab test", "ndcg", "click-through", "ctr", "embedding",
)

# ----------------------------------------------------------------------------
# Negative-signal lexicons (JD "do not want" + disqualifiers)
# ----------------------------------------------------------------------------
CONSULTING_FIRMS = {
    "tcs", "tata consultancy", "infosys", "wipro", "accenture", "cognizant",
    "capgemini", "tech mahindra", "hcl", "hcltech", "mindtree", "ltimindtree",
    "ibm", "deloitte", "pwc", "kpmg", "ey", "mphasis", "dxc", "ust", "hexaware",
}
RESEARCH_ONLY_TERMS = ("research scientist", "phd", "postdoc", "research fellow", "academic")
CV_SPEECH_ROBOTICS_TERMS = (
    "computer vision", "image classification", "object detection", "speech recognition",
    "tts", "asr", "robotics", "slam", "autonomous", "gans", "image segmentation",
)
LANGCHAIN_TERMS = ("langchain", "llamaindex", "autogpt", "prompt engineering")

# ----------------------------------------------------------------------------
# Industry classification (product vs services) — JD prefers product companies.
# ----------------------------------------------------------------------------
PRODUCT_INDUSTRIES = {
    "software", "fintech", "e-commerce", "ecommerce", "saas", "ai/ml", "ai",
    "food delivery", "edtech", "gaming", "healthtech", "social media", "internet",
}
SERVICES_INDUSTRIES = {"it services", "consulting", "conglomerate", "staffing", "bpo"}

# ----------------------------------------------------------------------------
# Location preference (Noida/Pune/India or relocatable Tier-1).
# ----------------------------------------------------------------------------
PREFERRED_CITIES = {"noida", "pune", "delhi", "gurgaon", "gurugram", "hyderabad",
                    "mumbai", "bangalore", "bengaluru", "chennai", "ncr"}

# Experience band the JD describes (soft, not a hard cut).
EXP_IDEAL_MIN = 5.0
EXP_IDEAL_MAX = 9.0


# A curated query text used for semantic similarity once embeddings land (M3).
JD_QUERY_TEXT = (
    "Senior AI Engineer for a product company's intelligence layer: builds and ships "
    "embeddings-based retrieval, hybrid and semantic search, ranking and recommendation "
    "systems to real users at scale. Strong Python. Hands-on with vector databases "
    "(FAISS, Pinecone, Weaviate, Qdrant, Milvus, Elasticsearch, OpenSearch). Designs "
    "evaluation frameworks for ranking (NDCG, MRR, MAP, A/B testing, offline-to-online "
    "correlation). LLM fine-tuning (LoRA, QLoRA, PEFT) and learning-to-rank are a plus. "
    "5-9 years experience, applied ML at product companies (not pure research, not "
    "consulting-only). Based in or willing to relocate to Noida or Pune, India."
)
