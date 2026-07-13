"""Response shapes for the asynchronous scrape job endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .common import Usage

#: Job lifecycle states for an async scrape.
AsyncJobStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class AsyncScrapeResponse:
    """Response body of ``POST /api/scrape/async``."""

    #: Job identifier -- pass it to ``get_scrape_status`` / ``get_scrape_result``.
    job_id: str


@dataclass
class AsyncStatusMeta:
    """Request-level metadata on an async status response (``response_meta``)."""

    #: Billing + routing usage for the finished job (credits, resolved proxy, cache).
    usage: Usage


@dataclass
class AsyncJobStatusResponse:
    """Response body of ``GET /api/scrape/status/:job_id``.

    Field names mirror the snake_case wire format 1:1 (``job_id``,
    ``created_at``), like the rest of the API.
    """

    #: The job identifier.
    job_id: str
    #: Current state of the job.
    status: AsyncJobStatus
    #: ISO-8601 UTC timestamp when the job was created.
    created_at: str
    #: Error message if the job ended in ``failed``.
    error: str | None = None
    #: Billing + routing usage, present only once the job reaches ``done``.
    response_meta: AsyncStatusMeta | None = None
