"""Small internal helpers shared by the clients."""

from __future__ import annotations

import os
from urllib.parse import quote

from ._errors import CrawlbruleeError


def read_env(name: str) -> str | None:
    """Return a trimmed environment variable, or ``None`` if unset/blank."""
    value = (os.environ.get(name) or "").strip()
    return value or None


def require_api_key(api_key: str | None) -> str:
    """Validate and normalize an API key, raising if missing/blank."""
    key = (api_key or "").strip()
    if not key:
        raise CrawlbruleeError(
            "Missing API key. Pass api_key=... to the client, or use "
            "Crawlbrulee.from_env() to read CRAWLBRULEE_API_KEY.",
            status=0,
            error_name=None,
        )
    return key


def require_job_id(job_id: str) -> str:
    """Validate that ``job_id`` is a non-empty string."""
    if not isinstance(job_id, str) or not job_id.strip():
        raise CrawlbruleeError("job_id must be a non-empty string.", status=0, error_name=None)
    return job_id


def scrape_status_path(job_id: str) -> str:
    """Path for ``GET /api/scrape/status/:job_id`` with ``job_id`` URL-encoded."""
    return f"/api/scrape/status/{quote(job_id, safe='')}"


def scrape_result_path(job_id: str) -> str:
    """Path for ``GET /api/scrape/result/:job_id`` with ``job_id`` URL-encoded."""
    return f"/api/scrape/result/{quote(job_id, safe='')}"
