from __future__ import annotations

import logging
from typing import Optional

from openai import OpenAI
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from news_scraper.config import settings
from news_scraper.llm_parser import parse_llm_output
from news_scraper.prompts import SYSTEM_PROMPT

log = logging.getLogger("news_scraper.llm")


class LLMClient:
    """
    Thin, safe wrapper around OpenAI for article analysis.
    """

    def __init__(self) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def analyze_article(self, prompt: str):
        """
        Send prompt to LLM and return validated LLMArticleAnalysis.
        Retries on transient failures.
        """
        log.debug("Sending prompt to LLM (%s chars)", len(prompt))

        response = self._client.responses.create(
            model=self._model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_output_tokens=400,
        )

        # Extract text output safely
        try:
            raw_text = response.output_text
        except Exception:
            raise RuntimeError("LLM response did not contain text output")

        log.debug("Raw LLM output: %s", raw_text)

        # Parse + validate strictly
        return parse_llm_output(raw_text)
