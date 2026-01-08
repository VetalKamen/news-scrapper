from __future__ import annotations

from news_scraper.models import ArticleAI
from news_scraper.vector_models import VectorDocument
from news_scraper.vector_text import build_embedding_text


def article_to_vector_doc(article: ArticleAI) -> VectorDocument:
    """
    Convert AI-enriched article to a vector-store document.
    Chroma metadata must be scalar values only (no lists/dicts).
    """
    topics_str = ", ".join(article.topics) if article.topics else ""

    return VectorDocument(
        id=str(article.url),
        text=build_embedding_text(article),
        metadata={
            "url": str(article.url),
            "title": article.title or "",
            "source": article.source or "",
            "summary": (article.summary or "")[:2000],
            # Store topics as a single string for Chroma compatibility
            "topics": topics_str,
            "topic_count": len(article.topics) if article.topics else 0,
        },
    )
