from __future__ import annotations

from pathlib import Path
from typing import Iterator

from news_scraper.jsonl_reader import iter_jsonl
from news_scraper.models import ArticleRaw


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
