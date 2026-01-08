from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
}


@dataclass(frozen=True)
class FetchResult:
    final_url: str
    status_code: Optional[int]
    content_type: Optional[str]
    html: Optional[str]
    error: Optional[str] = None


class HttpFetcher:
    """
    Thin wrapper around httpx.Client with retries for transient network failures.
    """

    def __init__(self, timeout_s: float = 20.0, follow_redirects: bool = True) -> None:
        self._client = httpx.Client(
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(timeout_s),
            follow_redirects=follow_redirects,
        )

    def close(self) -> None:
        self._client.close()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.TransportError)),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=6),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def fetch(self, url: str) -> FetchResult:
        """
        Fetch a URL and return decoded HTML text (if any).
        Retries on network/timeout exceptions.
        """
        resp = self._client.get(url)
        content_type = resp.headers.get("content-type")
        html = resp.text if resp.text else None

        return FetchResult(
            final_url=str(resp.url),
            status_code=resp.status_code,
            content_type=content_type,
            html=html,
        )
