from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from typing import List

from pydantic import BaseModel, Field, HttpUrl


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
