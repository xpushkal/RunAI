"""Streaming ingestion of candidates.jsonl.

Streams the 487 MB pool line-by-line so we never hold the raw file in memory.
Also builds the per-candidate text 'document' used for semantic similarity (M3).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator


def stream_candidates(path: str | Path) -> Iterator[dict]:
    """Yield one candidate dict per non-empty line."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def candidate_document(c: dict) -> str:
    """Concatenate the evidence-bearing free text for embeddings/relevance.

    Uses headline + summary + each role's title and description — i.e. what the
    candidate actually *did*, which is where plain-language fits reveal themselves.
    """
    p = c.get("profile", {})
    parts = [
        p.get("headline", ""),
        p.get("current_title", ""),
        p.get("summary", ""),
    ]
    for job in c.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("description", ""))
    # A compact skill list helps the encoder but is not the dominant signal.
    skills = ", ".join(s.get("name", "") for s in c.get("skills", []))
    if skills:
        parts.append("Skills: " + skills)
    return "\n".join(part for part in parts if part)
