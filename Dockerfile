# Reproducibility + sandbox image for the Redrob candidate ranker.
#
# Build:  docker build -t redrob-ranker .
# Demo:   docker run -p 8501:8501 redrob-ranker                # Streamlit sandbox
# Rank:   docker run -v $PWD/data:/data redrob-ranker \
#             python rank.py --candidates /data/candidates.jsonl --out /data/submission.csv
#
# The embedding model is baked into the image at build time so the ranking step
# needs NO network (satisfies the Stage-3 constraint).

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    HF_HUB_OFFLINE=0 \
    TOKENIZERS_PARALLELISM=false

WORKDIR /app

# System deps kept minimal; faiss-cpu / torch ship manylinux wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model into the image (offline ranking afterwards).
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('BAAI/bge-small-en-v1.5')"

COPY src/ ./src/
COPY rank.py app.py config.yaml ./
COPY India_runs_data_and_ai_challenge/validate_submission.py ./India_runs_data_and_ai_challenge/

EXPOSE 8501
# Default: launch the sandbox demo. Override with `python rank.py ...` to reproduce the CSV.
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
