from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
import trafilatura
from bs4 import BeautifulSoup

from news_scraper.http_client import HttpFetcher
from news_scraper.io import append_jsonl, load_seen_urls, normalize_url
from news_scraper.io import read_urls_from_file
from news_scraper.models import ArticleRaw

log = logging.getLogger("news_scraper.scrape")


@dataclass(frozen=True)
class ExtractedArticle:
    url: str
    source: Optional[str]
    title: Optional[str]
    text: Optional[str]
    chars: int


def _domain(url: str) -> Optional[str]:
    try:
        netloc = urlparse(url).netloc
        return netloc or None
    except Exception:
        return None


def extract_article(url: str, html: str, min_chars: int = 500) -> ExtractedArticle:
    """
    Extract title + main text from HTML using trafilatura (primary) and BeautifulSoup (fallback for title).
    """
    source = _domain(url)

    # Title from metadata, if possible
    title: Optional[str] = None
    try:
        meta = trafilatura.extract_metadata(html)
        if meta and getattr(meta, "title", None):
            title = meta.title
    except Exception:
        pass

    # Main text extraction
    text: Optional[str] = None
    try:
        extracted = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,
            output_format="txt",
        )
        if extracted:
            text = extracted.strip() or None
    except Exception:
        text = None

    # Fallback title
    if not title:
        try:
            soup = BeautifulSoup(html, "lxml")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
        except Exception:
            pass

    chars = len(text) if text else 0
    if chars < min_chars:
        return ExtractedArticle(url=url, source=source, title=title, text=None, chars=chars)

    return ExtractedArticle(url=url, source=source, title=title, text=text, chars=chars)


def _scrape_one_url(fetcher: HttpFetcher, url: str, *, min_chars: int) -> ArticleRaw:
    """
    Core scraping logic for a single URL. No file IO here.
    Always returns ArticleRaw with status 'ok' or 'failed'.
    """
    url_norm = normalize_url(url)
    record = ArticleRaw(url=url_norm)

    try:
        result = fetcher.fetch(url_norm)
        record.http_status = result.status_code
        record.content_type = result.content_type

        if not result.html:
            record.status = "failed"
            record.error = "Empty HTML response"
            return record

        extracted = extract_article(result.final_url, result.html, min_chars=min_chars)

        record.source = extracted.source
        record.title = extracted.title
        record.text = extracted.text
        record.chars = extracted.chars

        if extracted.text is None:
            record.status = "failed"
            record.error = f"Extraction too short (<{min_chars} chars)"
        else:
            record.status = "ok"

        return record

    except httpx.HTTPError as e:
        record.status = "failed"
        record.error = f"http error: {type(e).__name__}: {e}"
        return record

    except Exception as e:
        record.status = "failed"
        record.error = f"unexpected error: {type(e).__name__}: {e}"
        return record


def scrape_urls_to_jsonl(
    urls_file: Path,
    out_file: Path,
    limit: Optional[int] = None,
    sleep_s: float = 0.0,
    min_chars: int = 500,
) -> dict:
    """
    Batch scrape URLs from file into raw JSONL.

    Strict no-duplicates policy:
    - If URL already exists in out_file (normalized), it is skipped and NOT written again.
    """
    urls = read_urls_from_file(urls_file)
    urls = [normalize_url(u) for u in urls]

    if limit is not None:
        urls = urls[:limit]

    seen = load_seen_urls(out_file)
    fetcher = HttpFetcher(timeout_s=20.0, follow_redirects=True)

    ok = 0
    failed = 0
    skipped_existing = 0

    try:
        total = len(urls)
        for idx, url in enumerate(urls, start=1):
            if url in seen:
                skipped_existing += 1
                log.info("(%d/%d) Skipping already-scraped URL: %s", idx, total, url)
                continue

            log.info("(%d/%d) Processing %s", idx, total, url)

            record = _scrape_one_url(fetcher, url, min_chars=min_chars)
            append_jsonl(out_file, record.model_dump(mode="json"))

            # mark as seen regardless of success/failure to prevent duplicates
            seen.add(url)

            if record.status == "ok":
                ok += 1
            else:
                failed += 1

            if sleep_s > 0:
                time.sleep(sleep_s)

    finally:
        fetcher.close()

    summary = {
        "total_input": len(urls),
        "added": ok + failed,
        "ok": ok,
        "failed": failed,
        "skipped_existing": skipped_existing,
        "out_file": str(out_file),
    }
    log.info("Scraping finished: %s", summary)
    return summary


def scrape_single_url_to_jsonl(
    url: str,
    out_file: Path,
    *,
    min_chars: int = 500,
) -> dict:
    """
    Single URL scrape into raw JSONL.

    Strict no-duplicates policy:
    - If URL already exists in out_file (normalized), it is skipped and NOT written again.
    """
    url_norm = normalize_url(url)
    seen = load_seen_urls(out_file)
    if url_norm in seen:
        return {"total": 1, "ok": 0, "failed": 0, "skipped_existing": 1, "out_file": str(out_file)}

    fetcher = HttpFetcher(timeout_s=20.0, follow_redirects=True)
    try:
        record = _scrape_one_url(fetcher, url_norm, min_chars=min_chars)
        append_jsonl(out_file, record.model_dump(mode="json"))

        ok = 1 if record.status == "ok" else 0
        failed = 1 - ok
        return {"total": 1, "ok": ok, "failed": failed, "skipped_existing": 0, "out_file": str(out_file)}
    finally:
        fetcher.close()
