"""Client-side resilient fetch utility for Python scripts calling Cloud Run.

Usage:
    from scripts.utils.resilient_fetch import resilient_fetch

    response = await resilient_fetch("https://agent-data-test-xxx.a.run.app/health")
    data = response.json()

    # With POST and custom config
    response = await resilient_fetch(
        "https://agent-data-test-xxx.a.run.app/chat",
        method="POST",
        json={"message": "hello"},
        headers={"X-API-Key": api_key},
        retries=5,
        timeout=60,
    )
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {503, 504, 429}


class RetryableStatusError(Exception):
    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {detail}")


async def resilient_fetch(
    url: str,
    *,
    method: str = "GET",
    retries: int = 3,
    backoff_base: float = 1.0,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    json: Any = None,
    data: Any = None,
) -> httpx.Response:
    """Fetch a URL with automatic retry on transient errors.

    Args:
        url: Full URL to fetch.
        method: HTTP method (GET, POST, PUT, DELETE).
        retries: Max number of attempts.
        backoff_base: Base delay for exponential backoff (1s -> 2s -> 4s).
        timeout: Request timeout in seconds.
        headers: Optional HTTP headers.
        json: Optional JSON body (for POST/PUT).
        data: Optional form data body.

    Returns:
        httpx.Response on success.

    Raises:
        httpx.TimeoutException: After all retries exhausted on timeout.
        httpx.ConnectError: After all retries exhausted on connection error.
        RetryableStatusError: After all retries exhausted on 503/504/429.
    """

    @retry(
        stop=stop_after_attempt(retries),
        wait=wait_exponential(multiplier=backoff_base, min=1, max=backoff_base * 4),
        retry=retry_if_exception_type(
            (httpx.TimeoutException, httpx.ConnectError, RetryableStatusError)
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _do_fetch() -> httpx.Response:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json,
                data=data,
            )
        elapsed_ms = (time.monotonic() - t0) * 1000

        if response.status_code in RETRYABLE_STATUS_CODES:
            raise RetryableStatusError(
                response.status_code,
                f"after {elapsed_ms:.0f}ms",
            )

        logger.debug(
            "Fetch %s %s -> %d (%.0fms)",
            method,
            url,
            response.status_code,
            elapsed_ms,
        )
        return response

    return await _do_fetch()
