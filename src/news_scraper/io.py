from __future__ import annotations
from __future__ import annotations

import json
from typing import List

from pathlib import Path
from typing import Iterator, Any, Dict, Set
from urllib.parse import urlsplit, urlunsplit


def normalize_url(url: str) -> str:
    """
    Normalize URL to avoid trivial duplicates:
    - trim whitespace
    - drop fragment (#...)
    - remove trailing slash for non-root paths
    """
    url = url.strip()
    parts = urlsplit(url)
    parts = parts._replace(fragment="")
    normalized = urlunsplit(parts)
    if normalized.endswith("/") and parts.path not in ("", "/"):
        normalized = normalized[:-1]
    return normalized


def load_seen_urls(jsonl_path: Path) -> Set[str]:
    """
    Return set of normalized URLs present in a JSONL file (if it exists).
    Expects objects to have a 'url' field.
    """
    if not jsonl_path.exists():
        return set()

    seen: Set[str] = set()
    for obj in iter_jsonl(jsonl_path):
        u = obj.get("url")
        if not u:
            continue
        seen.add(normalize_url(str(u)))
    return seen


def contains_url(jsonl_path: Path, url: str) -> bool:
    """
    Fast(ish) membership check for normalized URL in JSONL file.
    """
    target = normalize_url(url)
    if not jsonl_path.exists():
        return False
    for obj in iter_jsonl(jsonl_path):
        u = obj.get("url")
        if u and normalize_url(str(u)) == target:
            return True
    return False


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """
    Append one JSON object as one JSONL line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()


def iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    """
    Iterate JSONL as dictionaries.
    Skips empty lines.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def read_urls_from_file(path: Path) -> List[str]:
    """
    Read URLs from a text file:
    - one URL per line
    - ignores empty lines
    - ignores comments that start with '#'
    - deduplicates while preserving order
    """
    if not path.exists():
        raise FileNotFoundError(f"URLs file not found: {path}")

    seen = set()
    urls: List[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line not in seen:
            seen.add(line)
            urls.append(line)

    return urls
