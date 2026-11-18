"""Shared retry policy for individual HTTP calls in clients.

tenacity is already a runtime dependency. Only single HTTP calls are
retried — never the whole ingest pipeline.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

import httpx
from tenacity import retry as _tenacity_retry
from tenacity import retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

F = TypeVar("F", bound=Callable[..., Awaitable[Any]])

_RETRY_POLICY = _tenacity_retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    wait=wait_exponential_jitter(initial=1, max=20, jitter=1),
    stop=stop_after_attempt(4),
    reraise=True,
)


def RETRY(func: F) -> F:
    """Typed decorator applying the shared retry policy to an async function.

    Retries on httpx.HTTPStatusError (raised by ``raise_for_status()``, e.g.
    429 rate-limit / 5xx) and httpx.TransportError (connection failures),
    with exponential backoff + jitter, up to 4 attempts, then re-raises.
    """
    return cast(F, _RETRY_POLICY(func))


__all__ = ["RETRY"]
