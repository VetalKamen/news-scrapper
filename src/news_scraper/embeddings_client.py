from __future__ import annotations

import logging
from typing import List

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from news_scraper.config import settings

log = logging.getLogger("news_scraper.embeddings")


class EmbeddingsClient:
    """
    Thin, retry-safe wrapper for generating embeddings.
    """

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def embed_text(self, text: str) -> List[float]:
        """
        Generate a single embedding vector for the given text.
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")

        log.debug("Embedding text (%d chars)", len(text))

        resp = self._client.embeddings.create(
            model=self._model,
            input=text,
        )

        try:
            return resp.data[0].embedding
        except Exception as e:
            raise RuntimeError("Invalid embedding response") from e
