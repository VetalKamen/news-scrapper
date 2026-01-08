from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, Iterator, Any


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
