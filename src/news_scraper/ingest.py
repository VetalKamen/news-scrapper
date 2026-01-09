from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional
from typing import Callable, Type, TypeVar

from news_scraper.config import settings
from news_scraper.embeddings_client import EmbeddingsClient
from news_scraper.io import append_jsonl, iter_jsonl, load_seen_urls, normalize_url
from news_scraper.llm_client import LLMClient
from news_scraper.models import ArticleAI, ArticleRaw
from news_scraper.scrape import scrape_single_url_to_jsonl
from news_scraper.vectorstore_chroma import ChromaVectorStore, article_to_vector_doc
from news_scraper.analyze import analyze_one_article_raw, build_failed_ai_from_raw


log = logging.getLogger("news_scraper.ingest")

T = TypeVar("T")  # ArticleRaw or ArticleAI


def _find_latest_by_url(
    jsonl_file: Path,
    url: str,
    model_cls: Type[T],
    is_ok: Callable[[T], bool],
) -> Optional[T]:
    """
    Return the most recent (last) record in JSONL matching URL and predicate.
    """
    if not jsonl_file.exists():
        return None

    target = normalize_url(url)
    latest: Optional[T] = None

    for obj in iter_jsonl(jsonl_file):
        u = obj.get("url")
        if not u:
            continue
        if normalize_url(str(u)) != target:
            continue

        rec = model_cls.model_validate(obj)
        if is_ok(rec):
            latest = rec

    return latest


def ingest_url(
    url: str,
    *,
    min_chars: int = 300,
    scrape_sleep_s: float = 0.0,  # kept for CLI compatibility
) -> Dict[str, Any]:
    """
    Ingest a single URL end-to-end: scrape -> analyze(this URL) -> index(this URL)

    Strict no-duplicates policy:
    - Raw: scrape_single_url_to_jsonl skips if already in raw JSONL
    - AI: we skip if URL already exists in AI JSONL (normalized)
    - Index: Chroma existing_ids prevents duplicates
    """
    settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)

    raw_file = settings.data_raw_dir / "articles_raw.jsonl"
    ai_file = settings.data_processed_dir / "articles_ai.jsonl"

    norm_url = normalize_url(url)

    # 0) If already analyzed, do not duplicate
    ai_seen = load_seen_urls(ai_file)
    if norm_url in ai_seen:
        return {"status": "ok", "url": norm_url, "skipped": True, "reason": "already_analyzed"}

    # 1) SCRAPE (idempotent now)
    scrape_res = scrape_single_url_to_jsonl(
        url=norm_url,
        out_file=raw_file,
        min_chars=min_chars,
    )

    # If scrape was skipped_existing, it's still fine: we can continue and analyze existing raw record
    raw = _find_latest_by_url(
        raw_file,
        norm_url,
        ArticleRaw,
        lambda r: r.status == "ok" and bool(r.text and r.text.strip()),
    )

    if raw is None:
        return {"status": "failed", "stage": "scrape", "url": norm_url, "detail": scrape_res}

    # 2) ANALYZE targeted
    client = LLMClient()
    try:
        enriched = analyze_one_article_raw(client, raw)
        append_jsonl(ai_file, enriched.model_dump(mode="json"))
        analyze_res = {"processed": 1, "failed": 0, "out_file": str(ai_file)}

    except Exception as e:
        failed_rec = build_failed_ai_from_raw(raw, client, e)
        append_jsonl(ai_file, failed_rec.model_dump(mode="json"))
        return {"status": "failed", "stage": "analyze", "url": norm_url, "detail": str(e)}

    # 3) INDEX targeted
    ai = _find_latest_by_url(
        ai_file,
        norm_url,
        ArticleAI,
        lambda a: a.status == "ok" and bool(a.summary and a.summary.strip()),
    )

    if ai is None:
        return {"status": "failed", "stage": "index", "url": norm_url, "detail": "No OK AI record after analysis."}

    store = ChromaVectorStore()
    existing_ids = store.existing_ids()
    if norm_url in existing_ids:
        return {
            "status": "ok",
            "url": norm_url,
            "skipped": False,
            "scrape": scrape_res,
            "analyze": analyze_res,
            "index": {"added": 0, "skipped_existing": 1},
        }

    doc = article_to_vector_doc(ai)
    embedder = EmbeddingsClient()
    vec = embedder.embed_text(doc.text)
    store.add_documents([doc], [vec])

    return {
        "status": "ok",
        "url": norm_url,
        "skipped": False,
        "scrape": scrape_res,
        "analyze": analyze_res,
        "index": {"added": 1, "skipped_existing": 0},
    }
