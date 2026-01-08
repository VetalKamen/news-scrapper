from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

import httpx

from news_scraper.extract import extract_article
from news_scraper.http_client import HttpFetcher
from news_scraper.io import append_jsonl
from news_scraper.models import ArticleRaw
from news_scraper.io import read_urls_from_file

log = logging.getLogger("news_scraper.scrape")


def scrape_urls_to_jsonl(
    urls_file: Path,
    out_file: Path,
    limit: Optional[int] = None,
    sleep_s: float = 0.0,
    min_chars: int = 500,
) -> dict:
    """
    Scrape URLs from a text file and write ArticleRaw records to JSONL.

    Always writes one JSONL record per URL (ok or failed).
    Returns a summary dict for logging / CLI output.
    """
    urls = read_urls_from_file(urls_file)
    if limit is not None:
        urls = urls[:limit]

    fetcher = HttpFetcher(timeout_s=20.0, follow_redirects=True)

    ok = 0
    failed = 0

    try:
        for idx, url in enumerate(urls, start=1):
            log.info("(%d/%d) Processing %s", idx, len(urls), url)

            record = ArticleRaw(url=url)

            try:
                result = fetcher.fetch(url)
                record.http_status = result.status_code
                record.content_type = result.content_type

                if not result.html:
                    record.status = "failed"
                    record.error = "Empty HTML response"
                    append_jsonl(out_file, record.model_dump(mode="json"))
                    failed += 1
                    continue

                extracted = extract_article(
                    result.final_url,
                    result.html,
                    min_chars=min_chars,
                )

                record.source = extracted.source
                record.title = extracted.title
                record.text = extracted.text
                record.chars = extracted.chars

                if extracted.text is None:
                    record.status = "failed"
                    record.error = f"Extraction too short (<{min_chars} chars)"
                    append_jsonl(out_file, record.model_dump(mode="json"))
                    failed += 1
                else:
                    append_jsonl(out_file, record.model_dump(mode="json"))
                    ok += 1

            except httpx.HTTPError as e:
                record.status = "failed"
                record.error = f"http error: {type(e).__name__}: {e}"
                append_jsonl(out_file, record.model_dump(mode="json"))
                failed += 1

            except Exception as e:
                record.status = "failed"
                record.error = f"unexpected error: {type(e).__name__}: {e}"
                append_jsonl(out_file, record.model_dump(mode="json"))
                failed += 1

            if sleep_s > 0:
                time.sleep(sleep_s)

    finally:
        fetcher.close()

    summary = {
        "total": ok + failed,
        "ok": ok,
        "failed": failed,
        "out_file": str(out_file),
    }
    log.info("Scraping finished: %s", summary)
    return summary
