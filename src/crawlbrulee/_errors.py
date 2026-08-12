"""Typed error hierarchy and the API-error mapping used by the HTTP layer."""

from __future__ import annotations

from typing import Any

from .types.common import ApiErrorName, UsageAllocationReason


class CrawlbruleeError(Exception):
    """Base error for every failure raised by the SDK.

    Two kinds of failures end up here:

    1. **API errors** -- the server returned a non-2xx response with a
       well-formed JSON body. ``status``, ``error_name`` and (sometimes)
       ``details`` are populated.
    2. **Transport errors** -- the request never produced a structured response
       (network failure, timeout, non-JSON body). ``status`` may be ``0`` and
       ``error_name`` is a synthetic transport name (``request_timeout``,
       ``client_closed_request``) or ``None``.

    Typed subclasses are exported for the most common cases; to branch on more
    specific server-side errors, switch on ``error_name``.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int = 0,
        error_name: ApiErrorName | None = None,
        details: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        #: Human-readable error message.
        self.message = message
        #: HTTP status code; ``0`` for transport-level failures with no response.
        self.status = status
        #: The ``name`` field from the API error body, or ``None`` for transport errors.
        self.error_name: ApiErrorName | None = error_name
        #: Structured detail block from the API error body, if any.
        self.details = details
        #: The original parsed error body, when one was received.
        self.response = response
        if cause is not None:
            self.__cause__ = cause


class AuthenticationError(CrawlbruleeError):
    """Raised for 401 / 403 responses (missing, invalid, or unauthorized key)."""


class NotFoundError(CrawlbruleeError):
    """Raised for 404 responses (e.g. unknown async job ID)."""


class ValidationError(CrawlbruleeError):
    """Raised for 4xx responses caused by an invalid request shape or arguments."""


class RateLimitError(CrawlbruleeError):
    """Raised for HTTP 429 responses.

    ``error_name`` is always normalized to ``too_many_requests`` even when the
    server returns a 429 with a different ``name`` (e.g. a CDN coalescing
    upstream rate limiting). The original body is available on ``response``.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int,
        details: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status=status,
            error_name="too_many_requests",
            details=details,
            response=response,
        )
        #: Suggested delay (ms) before retrying, when the server provided one.
        self.retry_after_ms: int | None = details.get("retry_after_ms") if details else None
        #: Which rate limit was tripped (e.g. ``org``, ``ip``), when provided.
        self.limited_by: str | None = details.get("limited_by") if details else None


class UsageAllocationError(CrawlbruleeError):
    """Raised when the request would exceed the org's plan limits (credit
    limit, concurrency cap, overage hard cap, etc.)."""

    def __init__(
        self,
        message: str,
        *,
        status: int,
        details: dict[str, Any],
        response: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            status=status,
            error_name="usage_allocation_error",
            details=details,
            response=response,
        )
        #: Specific reason the allocation was denied.
        self.reason: UsageAllocationReason = details.get("reason", "internal_error")
        #: Current usage / limit snapshot at the time of the rejection.
        self.usage: dict[str, Any] | None = details.get("details")


class ServiceUnavailableError(CrawlbruleeError):
    """Raised for HTTP 503 responses (``service_unavailable``).

    A transient infrastructure failure on our side -- the request never reached
    a verdict about your key or your page. **Retry it**, ideally with backoff.
    It is *not* a signal that your API key is wrong, so do not rotate a key in
    response to it; a genuinely bad or expired key still returns a 401
    ``invalid_credentials``.
    """


class TransportError(CrawlbruleeError):
    """Raised when a request cannot be sent or no structured response is parsed.

    ``error_name`` discriminates the cause: ``request_timeout`` (the timeout
    fired), ``client_closed_request`` (the request was cancelled), or ``None``
    (generic network error, non-JSON body, etc.).
    """


def is_crawlbrulee_error(err: object) -> bool:
    """Return ``True`` if ``err`` is (a subclass of) ``CrawlbruleeError``."""
    return isinstance(err, CrawlbruleeError)


def _details_for(details: dict[str, Any] | None, expected_error_name: str) -> dict[str, Any] | None:
    """Return ``details`` only if it carries the matching ``error_name``."""
    if details and details.get("error_name") == expected_error_name:
        return details
    return None


def create_api_error(body: dict[str, Any], status: int) -> CrawlbruleeError:
    """Map an API error body + HTTP status to the most specific error class.

    Dispatch is **name-first**: the body's ``name`` field is the most reliable
    signal of what went wrong. Status code is used only as a fallback when the
    name is unrecognized. This avoids miscategorizing e.g. a 403 carrying
    ``name: not_found`` as an auth error.
    """
    name = body.get("name")
    message = body.get("message") or f"HTTP {status}"
    details = body.get("details")
    details = details if isinstance(details, dict) else None

    if name == "too_many_requests":
        return RateLimitError(
            message,
            status=status,
            details=_details_for(details, "too_many_requests"),
            response=body,
        )

    if name == "usage_allocation_error":
        d = _details_for(details, "usage_allocation_error") or {
            "error_name": "usage_allocation_error",
            "reason": "internal_error",
        }
        return UsageAllocationError(message, status=status, details=d, response=body)

    if name in ("invalid_credentials", "access_denied"):
        return AuthenticationError(message, status=status, error_name=name, response=body)

    if name == "service_unavailable":
        return ServiceUnavailableError(
            message, status=status, error_name="service_unavailable", response=body
        )

    if name == "not_found":
        return NotFoundError(message, status=status, error_name="not_found", response=body)

    if name in (
        "validation_error",
        "invalid_url",
        "url_too_long",
        "unsupported_url_schema",
        "url_credentials_not_supported",
        "blocked_url",
        "unsupported_content",
        "unsupported_screenshot_output",
    ):
        return ValidationError(message, status=status, error_name=name, response=body)

    # Name was not specific enough -- fall back to status-based heuristics, but
    # never override what the name said.
    if status == 429:
        return RateLimitError(message, status=status, response=body)
    if status in (401, 403):
        return AuthenticationError(message, status=status, error_name=name, response=body)
    if status == 404:
        return NotFoundError(message, status=status, error_name=name, response=body)
    if status == 503:
        return ServiceUnavailableError(message, status=status, error_name=name, response=body)

    return CrawlbruleeError(message, status=status, error_name=name, details=details, response=body)
