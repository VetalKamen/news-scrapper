from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from urllib.parse import urlparse
from bs4 import BeautifulSoup

import httpx
import trafilatura

from news_scraper.http_client import HttpFetcher
from news_scraper.io import append_jsonl
from news_scraper.models import ArticleRaw
from news_scraper.io import read_urls_from_file

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
    Extracts title + main text from HTML.

    Primary extraction:
      - trafilatura.extract (main text)
      - trafilatura.extract_metadata (title, if available)

    Fallbacks:
      - <title> via BeautifulSoup

    If extracted text is shorter than min_chars, returns text=None to signal "failed/too short".
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

    # Fallback title from HTML <title>
    if not title:
        try:
            soup = BeautifulSoup(html, "lxml")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
        except Exception:
            pass

    chars = len(text) if text else 0

    if chars < min_chars:
        # Keep title if present, but signal insufficient extraction
        return ExtractedArticle(url=url, source=source, title=title, text=None, chars=chars)

    return ExtractedArticle(url=url, source=source, title=title, text=text, chars=chars)


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
