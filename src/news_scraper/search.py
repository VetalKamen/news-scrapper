from __future__ import annotations

import logging
from typing import List, Dict, Any

from news_scraper.embeddings_client import EmbeddingsClient
from news_scraper.vectorstore_chroma import ChromaVectorStore

log = logging.getLogger("news_scraper.search")


def semantic_search(
    query: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    Perform semantic search over indexed articles.
    Returns top-k results with metadata and distance score.
    """
    if not query or not query.strip():
        raise ValueError("Query must not be empty")

    store = ChromaVectorStore()
    embedder = EmbeddingsClient()

    query_vec = embedder.embed_text(query)

    results = store._collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        include=["metadatas", "documents", "distances"],
    )

    hits: List[Dict[str, Any]] = []

    for i in range(len(results["ids"][0])):
        hit = {
            "rank": i + 1,
            "score": results["distances"][0][i],
            "document": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
        }
        hits.append(hit)

    log.info("Search returned %d results", len(hits))
    return hits
