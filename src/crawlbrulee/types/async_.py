"""Response shapes for the asynchronous scrape job endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Literal

#: Job lifecycle states for an async scrape.
AsyncJobStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class AsyncScrapeResponse:
    """Response body of ``POST /api/scrape/async``."""

    #: Job identifier -- pass it to ``get_scrape_status`` / ``get_scrape_result``.
    job_id: str


@dataclass
class AsyncJobStatusResponse:
    """Response body of ``GET /api/scrape/status/:jobId``.

    The wire format uses camelCase (``jobId``, ``createdAt``) for this one
    endpoint while the rest of the API uses snake_case. The SDK exposes Pythonic
    ``job_id`` / ``created_at`` attributes and maps them via ``__wire_aliases__``.
    """

    #: The job identifier.
    job_id: str
    #: Current state of the job.
    status: AsyncJobStatus
    #: ISO-8601 UTC timestamp when the job was created.
    created_at: str
    #: Error message if the job ended in ``failed``.
    error: str | None = None

    #: Maps SDK field names to their (camelCase) wire keys for (de)serialization.
    __wire_aliases__: ClassVar[dict[str, str]] = {
        "job_id": "jobId",
        "created_at": "createdAt",
    }
