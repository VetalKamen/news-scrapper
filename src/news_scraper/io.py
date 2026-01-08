from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Iterator, Any


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
