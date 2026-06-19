"""Body shapes for crawlbrulee webhook deliveries.

These mirror the JSON envelope the API POSTs to a configured webhook endpoint
when an async scrape job reaches a terminal state. The fields are snake_case on
the wire, so they map directly to the dataclass fields (no ``__wire_aliases__``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import Usage


@dataclass
class ScrapeCompleteWebhookMeta:
    """The ``data.response_meta`` block of a ``scrape.complete`` webhook delivery."""

    #: Billing + routing usage for the finished job (credits, resolved proxy, cache).
    usage: Usage


@dataclass
class ScrapeCompleteWebhookData:
    """The ``data`` block of a ``scrape.complete`` webhook delivery."""

    #: The async job identifier -- pass it to ``get_scrape_result``.
    job_id: str
    #: Terminal state of the job: ``success`` / ``failed`` / ``cancelled``.
    status: str
    #: The URL that was scraped.
    url: str
    #: ISO-8601 UTC timestamp when the job reached its terminal state.
    completed_at: str
    #: Error message, present when ``status == "failed"``.
    error: str | None = None
    #: Arbitrary metadata echoed back from the original request's
    #: ``webhook.metadata``, when one was supplied.
    metadata: dict[str, Any] | None = None
    #: Billing + routing usage for the finished job.
    response_meta: ScrapeCompleteWebhookMeta | None = None


@dataclass
class ScrapeCompleteWebhook:
    """A ``scrape.complete`` webhook delivery envelope.

    Wire shape::

        {
          "event_id": "...",
          "timestamp": "...",            # ISO-8601
          "event": "scrape.complete",
          "data": { ... }                # ScrapeCompleteWebhookData
        }
    """

    #: Unique identifier for this delivery (useful for idempotency / dedupe).
    event_id: str
    #: ISO-8601 UTC timestamp when the event was emitted.
    timestamp: str
    #: The event type. Always ``"scrape.complete"`` for this envelope.
    event: str
    #: The job-completion payload.
    data: ScrapeCompleteWebhookData
