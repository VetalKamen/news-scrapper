from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import trafilatura
from bs4 import BeautifulSoup


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
