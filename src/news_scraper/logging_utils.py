from __future__ import annotations

import logging
import sys
from typing import Literal


def setup_logging(level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO") -> None:
    """
    Configure a simple, consistent console logger for the project.
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # overwrite any prior logging config (useful in notebooks/IDE runs)
    )
