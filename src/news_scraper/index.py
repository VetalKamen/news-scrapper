from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Set

from news_scraper.embeddings_client import EmbeddingsClient
from news_scraper.io import iter_jsonl
from news_scraper.models import ArticleAI
from news_scraper.vector_io import article_to_vector_doc
from news_scraper.vectorstore_chroma import ChromaVectorStore

log = logging.getLogger("news_scraper.index")


def index_ai_jsonl_to_chroma(
    ai_file: Path,
    limit: Optional[int] = None,
) -> dict:
    """
    Load AI-enriched JSONL and index into Chroma vector store.
    Skips records that are not ok or missing summary/topics.
    Skips URLs already indexed.
    """
    store = ChromaVectorStore()
    embeddings_client = EmbeddingsClient()

    existing: Set[str] = store.existing_ids()

    added = 0
    skipped_existing = 0
    skipped_ineligible = 0
    failed = 0

    for obj in iter_jsonl(ai_file):
        if limit is not None and added >= limit:
            break

        try:
            art = ArticleAI.model_validate(obj)

            # Only index successful AI outputs
            if art.status != "ok" or not art.summary:
                skipped_ineligible += 1
                continue

            doc = article_to_vector_doc(art)

            if doc.id in existing:
                skipped_existing += 1
                continue

            vec = embeddings_client.embed_text(doc.text)
            store.add_documents([doc], [vec])

            existing.add(doc.id)
            added += 1

        except Exception as e:
            failed += 1
            log.exception("Failed to index record: %s", e)

    summary = {
        "added": added,
        "skipped_existing": skipped_existing,
        "skipped_ineligible": skipped_ineligible,
        "failed": failed,
        "collection_dir": str(store.persist_dir),
    }
    log.info("Index finished: %s", summary)
    return summary
