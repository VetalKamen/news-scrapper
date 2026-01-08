from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Set, Iterator

from news_scraper.io import append_jsonl
from news_scraper.io import iter_jsonl
from news_scraper.llm_client import LLMClient
from news_scraper.models import ArticleAI, ArticleRaw
from news_scraper.prompts import build_article_analysis_prompt

log = logging.getLogger("news_scraper.analyze")


def iter_ok_articles(raw_jsonl: Path) -> Iterator[ArticleRaw]:
    """
    Yield ArticleRaw entries that are eligible for LLM analysis:
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


def _load_processed_urls(out_file: Path) -> Set[str]:
    """
    Load already processed URLs from output JSONL so re-runs skip them.
    """
    if not out_file.exists():
        return set()

    urls = set()
    for obj in iter_jsonl(out_file):
        url = obj.get("url")
        if url:
            urls.add(str(url))
    return urls


def analyze_raw_to_ai_jsonl(
        raw_file: Path,
        out_file: Path,
        limit: Optional[int] = None,
) -> dict:
    """
    Read raw JSONL, analyze eligible articles with LLM, write AI-enriched JSONL.
    Returns summary stats.
    """
    client = LLMClient()
    already = _load_processed_urls(out_file)

    processed = 0
    skipped_already = 0
    skipped_ineligible = 0
    failed = 0

    for idx, article in enumerate(iter_ok_articles(raw_file), start=1):
        if limit is not None and processed >= limit:
            break

        url_str = str(article.url)
        if url_str in already:
            skipped_already += 1
            continue

        log.info("Analyzing (%d) %s", idx, url_str)

        try:
            prompt = build_article_analysis_prompt(article)
            analysis = client.analyze_article(prompt)

            enriched = ArticleAI(**article.model_dump(mode="json"))
            enriched.summary = analysis.summary
            enriched.topics = analysis.topics
            enriched.llm_model = client._model  # audit; acceptable for prototype

            append_jsonl(out_file, enriched.model_dump(mode="json"))
            processed += 1

        except Exception as e:
            # Write a failed AI record too (auditable)
            enriched = ArticleAI(**article.model_dump(mode="json"))
            enriched.status = "failed"
            enriched.error = f"llm error: {type(e).__name__}: {e}"
            enriched.llm_model = getattr(client, "_model", None)
            append_jsonl(out_file, enriched.model_dump(mode="json"))
            failed += 1

    # Note: skipped_ineligible is not tracked here because iter_ok_articles filters already.
    summary = {
        "processed": processed,
        "failed": failed,
        "skipped_already": skipped_already,
        "out_file": str(out_file),
    }
    log.info("Analyze finished: %s", summary)
    return summary
