from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """
    Append one JSON object as one JSONL line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
