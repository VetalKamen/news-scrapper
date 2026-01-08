from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


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
