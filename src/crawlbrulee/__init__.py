"""Official Python SDK for the crawlbrulee web-scraping API.

Most usage starts with :class:`Crawlbrulee` (sync) or :class:`AsyncCrawlbrulee`::

    from crawlbrulee import Crawlbrulee

    client = Crawlbrulee(api_key="cwbl_…")
    # or read CRAWLBRULEE_API_KEY from the environment:
    client = Crawlbrulee.from_env()

    page = client.scrape(url="https://example.com")
    print(page.markdown)
"""

from __future__ import annotations

from . import types as types
from ._async_client import AsyncCrawlbrulee
from ._client import Crawlbrulee
from ._config import DEFAULT_BASE_URL, ENV_API_KEY, USER_AGENT, __version__
from ._errors import (
    AuthenticationError,
    CrawlbruleeError,
    NotFoundError,
    RateLimitError,
    TransportError,
    UsageAllocationError,
    ValidationError,
    is_crawlbrulee_error,
)
from ._webhooks import WebhookVerificationResult, verify_webhook_signature
from .types import *  # noqa: F403  (re-export the public DTOs)
from .types import __all__ as _TYPES_ALL

__all__ = [
    "__version__",
    "types",
    # clients
    "Crawlbrulee",
    "AsyncCrawlbrulee",
    # errors
    "CrawlbruleeError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "TransportError",
    "UsageAllocationError",
    "ValidationError",
    "is_crawlbrulee_error",
    # webhooks
    "verify_webhook_signature",
    "WebhookVerificationResult",
    # config
    "DEFAULT_BASE_URL",
    "ENV_API_KEY",
    "USER_AGENT",
]
# Re-export every public DTO from ``crawlbrulee.types`` so the top-level package
# and the types module stay in sync automatically.
__all__ += _TYPES_ALL  # pyright: ignore[reportUnsupportedDunderAll]
