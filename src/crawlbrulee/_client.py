"""The synchronous :class:`Crawlbrulee` client."""

from __future__ import annotations

import time
from types import TracebackType
from typing import Any

from ._config import ENV_API_KEY
from ._errors import CrawlbruleeError
from ._http import SyncTransport
from ._serde import from_dict, map_body, scrape_body
from ._util import (
    read_env,
    require_api_key,
    require_job_id,
    scrape_result_path,
    scrape_status_path,
)
from .types.account import UsageResponse, WhoamiResponse
from .types.async_ import AsyncJobStatusResponse, AsyncScrapeResponse
from .types.common import ProxyTier
from .types.map import MapCache, MapLocation, MapResponse, MapTypes
from .types.scrape import ScrapeCache, ScrapeExtract, ScrapeLocation, ScrapeResponse
from .types.webhooks import ScrapeCompleteWebhook


class Crawlbrulee:
    """Synchronous client for the crawlbrulee API.

    Example::

        from crawlbrulee import Crawlbrulee

        with Crawlbrulee(api_key="cble_…") as client:
            page = client.scrape(
                url="https://example.com",
                extract=ScrapeExtract(markdown=True, links=True),
            )
            print(page.markdown)
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str | None = None,
        timeout: float | None = None,
        transport: SyncTransport | None = None,
    ) -> None:
        key = require_api_key(api_key)
        self._transport = transport or SyncTransport(
            api_key=key, base_url=base_url, timeout=timeout
        )
        #: Resolved base URL (trailing slash stripped).
        self.base_url = self._transport.base_url

    @classmethod
    def from_env(cls, **overrides: Any) -> Crawlbrulee:
        """Build a client reading the API key from ``CRAWLBRULEE_API_KEY``.

        Any other constructor option can be passed via keyword arguments.
        """
        api_key = read_env(ENV_API_KEY)
        if not api_key:
            raise CrawlbruleeError(
                f"{ENV_API_KEY} is not set. Export it in your shell, or pass "
                "api_key=... to Crawlbrulee(...).",
                status=0,
                error_name=None,
            )
        return cls(api_key, **overrides)

    def __enter__(self) -> Crawlbrulee:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._transport.close()

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    def scrape(
        self,
        url: str,
        *,
        extract: ScrapeExtract | dict[str, Any] | None = None,
        cache: ScrapeCache | dict[str, Any] | None = None,
        require_js: bool | None = None,
        exclude_selectors: list[str] | None = None,
        proxy: ProxyTier | None = None,
        location: ScrapeLocation | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ScrapeResponse:
        """Scrape a URL synchronously and return the extracted content.

        The request blocks until the scrape finishes. For long-running jobs
        prefer :meth:`scrape_async` so the connection isn't held open.
        """
        body = scrape_body(url, extract, cache, require_js, exclude_selectors, proxy, location)
        data = self._transport.request("POST", "/api/scrape", body=body, timeout=timeout)
        return from_dict(ScrapeResponse, data)

    def scrape_async(
        self,
        url: str,
        *,
        extract: ScrapeExtract | dict[str, Any] | None = None,
        cache: ScrapeCache | dict[str, Any] | None = None,
        require_js: bool | None = None,
        exclude_selectors: list[str] | None = None,
        proxy: ProxyTier | None = None,
        location: ScrapeLocation | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> AsyncScrapeResponse:
        """Submit a background scrape job and return its ``job_id``."""
        body = scrape_body(url, extract, cache, require_js, exclude_selectors, proxy, location)
        data = self._transport.request("POST", "/api/scrape/async", body=body, timeout=timeout)
        return from_dict(AsyncScrapeResponse, data)

    def get_scrape_status(
        self, job_id: str, *, timeout: float | None = None
    ) -> AsyncJobStatusResponse:
        """Look up the current status of an async scrape job."""
        require_job_id(job_id)
        data = self._transport.request("GET", scrape_status_path(job_id), timeout=timeout)
        return from_dict(AsyncJobStatusResponse, data)

    def get_scrape_result(self, job_id: str, *, timeout: float | None = None) -> ScrapeResponse:
        """Fetch the result of a completed async scrape job.

        Raises if the job hasn't finished yet -- call :meth:`get_scrape_status`
        first, or use :meth:`wait_for_scrape` to poll-then-fetch.
        """
        require_job_id(job_id)
        data = self._transport.request("GET", scrape_result_path(job_id), timeout=timeout)
        return from_dict(ScrapeResponse, data)

    def wait_for_scrape(
        self, job_id: str, *, interval: float = 2.0, timeout: float = 300.0
    ) -> ScrapeResponse:
        """Poll an async scrape job until terminal, then return its result.

        Raises :class:`CrawlbruleeError` with ``error_name='job_failed'`` if the
        job fails, or ``error_name='request_timeout'`` if the overall wait
        exceeds ``timeout`` (pass ``timeout=0`` to wait indefinitely).
        """
        require_job_id(job_id)
        deadline = time.monotonic() + timeout if timeout and timeout > 0 else None
        while True:
            if deadline is not None and time.monotonic() >= deadline:
                raise CrawlbruleeError(
                    f"Timed out after {timeout}s waiting for async scrape job {job_id}.",
                    status=0,
                    error_name="request_timeout",
                )
            status = self.get_scrape_status(job_id)
            if status.status == "done":
                return self.get_scrape_result(job_id)
            if status.status == "failed":
                raise CrawlbruleeError(
                    status.error or f"Async scrape job {job_id} failed.",
                    status=0,
                    error_name="job_failed",
                )
            if status.status not in ("pending", "running"):
                raise CrawlbruleeError(
                    f"Async scrape job {job_id} returned unexpected status {status.status!r}.",
                    status=0,
                    error_name="job_failed",
                )
            time.sleep(interval)

    def fetch_scrape_result_from_webhook(
        self,
        webhook: ScrapeCompleteWebhook | dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> ScrapeResponse:
        """Fetch the scrape result referenced by a ``scrape.complete`` webhook.

        Pass the parsed webhook body -- either a :class:`ScrapeCompleteWebhook`
        or the plain ``dict`` you decoded from the request -- and this returns
        the completed scrape via :meth:`get_scrape_result`.

        Verify the delivery's signature with
        :func:`crawlbrulee.verify_webhook_signature` *before* calling this.

        Raises :class:`CrawlbruleeError` when the event isn't ``scrape.complete``,
        or when the job ``failed`` (carrying ``data.error``) or was ``cancelled``.
        HTTP errors from the result fetch propagate unchanged.
        """
        wh = (
            webhook
            if isinstance(webhook, ScrapeCompleteWebhook)
            else from_dict(ScrapeCompleteWebhook, webhook)
        )
        if wh.event != "scrape.complete":
            raise CrawlbruleeError(
                f"Expected a 'scrape.complete' webhook, got {wh.event!r}.",
                status=0,
                error_name=None,
            )
        data = wh.data
        if data.status == "success":
            return self.get_scrape_result(data.job_id, timeout=timeout)
        if data.status == "failed":
            raise CrawlbruleeError(
                data.error or f"Async scrape job {data.job_id} failed.",
                status=0,
                error_name="job_failed",
            )
        if data.status == "cancelled":
            raise CrawlbruleeError(
                f"Async scrape job {data.job_id} was cancelled.",
                status=0,
                error_name=None,
            )
        raise CrawlbruleeError(
            f"Async scrape job {data.job_id} has unexpected status {data.status!r}.",
            status=0,
            error_name=None,
        )

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def map(
        self,
        url: str,
        *,
        proxy: ProxyTier | None = None,
        sitemap_only: bool | None = None,
        types: MapTypes | dict[str, Any] | None = None,
        cache: MapCache | dict[str, Any] | None = None,
        max_urls: int | None = None,
        page: int | None = None,
        limit: int | None = None,
        location: MapLocation | dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> MapResponse:
        """Build (or return a cached) site link-map for a domain."""
        body = map_body(url, proxy, sitemap_only, types, cache, max_urls, page, limit, location)
        data = self._transport.request("POST", "/api/map", body=body, timeout=timeout)
        return from_dict(MapResponse, data)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    def usage(self, *, timeout: float | None = None) -> UsageResponse:
        """Return the current billing-cycle usage snapshot."""
        data = self._transport.request("GET", "/api/usage", timeout=timeout)
        return from_dict(UsageResponse, data)

    def whoami(self, *, timeout: float | None = None) -> WhoamiResponse:
        """Return the organization + token identity behind the API key."""
        data = self._transport.request("GET", "/api/whoami", timeout=timeout)
        return from_dict(WhoamiResponse, data)
