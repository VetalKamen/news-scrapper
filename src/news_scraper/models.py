from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from typing import List

from pydantic import BaseModel, Field, HttpUrl, field_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ArticleRaw(BaseModel):
    """
    One JSONL record per URL. Always written, even if extraction fails,
    so runs are auditable and reproducible.
    """

    url: HttpUrl
    source: Optional[str] = None

    title: Optional[str] = None
    text: Optional[str] = None

    fetched_at: str = Field(default_factory=utc_now_iso)

    status: str = Field(default="ok", description="ok|failed")
    error: Optional[str] = None

    http_status: Optional[int] = None
    content_type: Optional[str] = None
    chars: int = 0


class ArticleAI(ArticleRaw):
    """
    AI-enriched article record. Inherits raw fields, adds summary + topics.
    Written to data/processed/articles_ai.jsonl
    """

    summary: Optional[str] = None
    topics: List[str] = Field(default_factory=list)

    # Optional: keep the prompt/model metadata for auditability
    llm_model: Optional[str] = None


class VectorDocument(BaseModel):
    """
    Single document stored in the vector database.
    """

    id: str = Field(..., description="Stable unique ID (usually URL)")
    text: str = Field(..., description="Text used for embedding")
    metadata: dict = Field(default_factory=dict)


class LLMArticleAnalysis(BaseModel):
    """
    Strict schema for LLM output.
    The LLM MUST return JSON that conforms to this model.
    """

    summary: str = Field(
        ...,
        description="Concise summary of the article in 3–5 sentences."
    )

    topics: List[str] = Field(
        ...,
        description="3–7 short topic tags, lowercase, no duplicates."
    )

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary must not be empty")
        return v.strip()

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, v: List[str]) -> List[str]:
        cleaned = []
        for t in v:
            t = t.strip().lower()
            if t and t not in cleaned:
                cleaned.append(t)

        if not (3 <= len(cleaned) <= 7):
            raise ValueError("topics must contain between 3 and 7 items")

        return cleaned