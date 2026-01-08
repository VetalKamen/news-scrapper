from __future__ import annotations

import json

from news_scraper.llm_schema import LLMArticleAnalysis


def parse_llm_output(raw_text: str) -> LLMArticleAnalysis:
    """
    Parse and validate raw LLM output.
    Raises ValueError if JSON or schema is invalid.
    """
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from LLM: {e}") from e

    return LLMArticleAnalysis.model_validate(data)
