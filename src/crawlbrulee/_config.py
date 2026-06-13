"""Static configuration: base URL, env var names, and the User-Agent string."""

from __future__ import annotations

__version__ = "0.2.0"

#: Production base URL of the crawlbrulee API. Used by default when the caller
#: doesn't pass a ``base_url``. Local development and staging callers point at
#: their own host via that option.
DEFAULT_BASE_URL = "https://api.crawlbrulee.com"

#: Environment variable read by ``Crawlbrulee.from_env()`` to source the API key.
ENV_API_KEY = "CRAWLBRULEE_API_KEY"

#: Identifies the SDK in the ``User-Agent`` header. Kept in one place for easy bumping.
USER_AGENT = f"crawlbrulee-python/{__version__} (httpx)"
