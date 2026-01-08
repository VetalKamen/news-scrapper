from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError


def _project_root() -> Path:
    """
    Resolve project root assuming this file lives in: <root>/src/news_scraper/config.py
    """
    return Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    # --- Required ---
    openai_api_key: str = Field(..., min_length=10, description="OpenAI API key")

    # --- Optional / defaults ---
    openai_model: str = Field(default="gpt-4o-mini")
    openai_embedding_model: str = Field(default="text-embedding-3-small")

    chroma_dir: Path = Field(default_factory=lambda: _project_root() / "data" / "vectorstore")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Helpful for consistent storage
    data_raw_dir: Path = Field(default_factory=lambda: _project_root() / "data" / "raw")
    data_processed_dir: Path = Field(default_factory=lambda: _project_root() / "data" / "processed")


def load_settings(env_file: Optional[Path] = None) -> Settings:
    """
    Loads environment variables (optionally from .env) and validates Settings.

    IMPORTANT:
    - Do NOT hardcode secrets here.
    - Only fill variables in .env.
    """
    if env_file is None:
        env_file = _project_root() / ".env"

    # Load .env if present; environment variables override .env by default
    if env_file.exists():
        load_dotenv(env_file, override=False)

    # Map environment variables -> Settings fields
    data = {
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "openai_embedding_model": os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "chroma_dir": os.getenv("CHROMA_DIR", str(_project_root() / "data" / "vectorstore")),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "data_raw_dir": os.getenv("DATA_RAW_DIR", str(_project_root() / "data" / "raw")),
        "data_processed_dir": os.getenv("DATA_PROCESSED_DIR", str(_project_root() / "data" / "processed")),
    }

    try:
        settings = Settings(**data)
    except ValidationError as e:
        # Provide a clean error message for missing required vars
        raise RuntimeError(
            "Invalid configuration. Ensure required environment variables are set.\n"
            "Required: OPENAI_API_KEY\n"
            f"Details:\n{e}"
        ) from e

    # Ensure directories exist (safe, idempotent)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.data_raw_dir.mkdir(parents=True, exist_ok=True)
    settings.data_processed_dir.mkdir(parents=True, exist_ok=True)

    return settings


# Convenience singleton-style access (lazy load)
settings = load_settings()
