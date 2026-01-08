from __future__ import annotations

from news_scraper.models import ArticleAI


def build_embedding_text(article: ArticleAI) -> str:
    """
    Build the text that will be embedded for semantic search.
    """
    parts = []

    if article.title:
        parts.append(article.title.strip())

    if article.summary:
        parts.append(article.summary.strip())

    if article.topics:
        parts.append("Topics: " + ", ".join(article.topics))

    return "\n\n".join(parts)
