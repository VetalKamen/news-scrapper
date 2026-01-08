from __future__ import annotations

from pathlib import Path
from typing import List


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
