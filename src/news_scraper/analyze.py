from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional, Set

from news_scraper.io import append_jsonl, iter_jsonl, load_seen_urls, normalize_url
from news_scraper.llm_client import LLMClient
from news_scraper.models import ArticleAI, ArticleRaw
from news_scraper.prompts import build_article_analysis_prompt

log = logging.getLogger("news_scraper.analyze")


def analyze_one_article_raw(client: LLMClient, raw: ArticleRaw) -> ArticleAI:
    """
    Analyze one ArticleRaw with the LLM and return ArticleAI.
    Raises on failure (caller decides how to persist failures).
    """
    prompt = build_article_analysis_prompt(raw)
    analysis = client.analyze_article(prompt)

    enriched = ArticleAI(**raw.model_dump(mode="json"))
    enriched.summary = analysis.summary
    enriched.topics = analysis.topics
    enriched.llm_model = client._model  # prototype audit field
    return enriched


def build_failed_ai_from_raw(raw: ArticleRaw, client: LLMClient, exc: Exception) -> ArticleAI:
    """
    Create a failed ArticleAI record for audit trail.
    """
    enriched = ArticleAI(**raw.model_dump(mode="json"))
    enriched.status = "failed"
    enriched.error = f"llm error: {type(exc).__name__}: {exc}"
    enriched.llm_model = getattr(client, "_model", None)
    return enriched


def iter_ok_articles(raw_jsonl: Path) -> Iterator[ArticleRaw]:
    """
    Yield ArticleRaw eligible for LLM analysis:
    - status == 'ok'
    - non-empty text
    """
    for obj in iter_jsonl(raw_jsonl):
        art = ArticleRaw.model_validate(obj)

        if art.status != "ok":
            continue
        if not art.text or not art.text.strip():
            continue

        yield art


def analyze_raw_to_ai_jsonl(
        raw_file: Path,
        out_file: Path,
        limit: Optional[int] = None,
) -> dict:
    """
    Batch analyze raw JSONL into AI JSONL.

    Strict no-duplicates policy:
    - If normalized URL already exists in out_file, it is skipped.
    """
    client = LLMClient()
    already: Set[str] = load_seen_urls(out_file)

    processed = 0
    skipped_already = 0
    failed = 0

    for idx, article in enumerate(iter_ok_articles(raw_file), start=1):
        if limit is not None and processed >= limit:
            break

        url_key = normalize_url(str(article.url))
        if url_key in already:
            skipped_already += 1
            continue

        log.info("Analyzing (%d) %s", idx, str(article.url))

        try:
            enriched = analyze_one_article_raw(client, article)
            append_jsonl(out_file, enriched.model_dump(mode="json"))
            processed += 1
            already.add(url_key)

        except Exception as e:
            failed_rec = build_failed_ai_from_raw(article, client, e)
            append_jsonl(out_file, failed_rec.model_dump(mode="json"))
            failed += 1
            already.add(url_key)

    summary = {
        "processed": processed,
        "failed": failed,
        "skipped_already": skipped_already,
        "out_file": str(out_file),
    }
    log.info("Analyze finished: %s", summary)
    return summary
