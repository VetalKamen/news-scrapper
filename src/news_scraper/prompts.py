from __future__ import annotations

from news_scraper.models import ArticleRaw


SYSTEM_PROMPT = """You are a precise information extraction system.
You must return ONLY valid JSON.
Do not include explanations, markdown, or extra text.
"""


def build_article_analysis_prompt(article: ArticleRaw) -> str:
    """
    Build a strict prompt instructing the LLM to output JSON
    matching LLMArticleAnalysis schema.
    """
    return f"""
Analyze the following news article and return a JSON object with this exact structure:

{{
  "summary": "3–5 sentence concise summary",
  "topics": ["topic1", "topic2", "topic3"]
}}

Rules:
- Output ONLY JSON
- No markdown
- No trailing text
- Topics must be 3–7 short lowercase strings

Article title:
{article.title}

Article text:
{article.text}
""".strip()
