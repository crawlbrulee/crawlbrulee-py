"""Small internal helpers shared by the clients."""

from __future__ import annotations

import os

from ._errors import CrawlbruleeError


def read_env(name: str) -> str | None:
    """Return a trimmed environment variable, or ``None`` if unset/blank."""
    value = os.environ.get(name)
    if value is None:
        return None
    value = value.strip()
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
