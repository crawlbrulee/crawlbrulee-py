"""The asynchronous :class:`AsyncCrawlbrulee` client."""

from __future__ import annotations

import asyncio
import time
from types import TracebackType
from typing import Any

from ._config import ENV_API_KEY
from ._errors import CrawlbruleeError
from ._http import AsyncTransport
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


class AsyncCrawlbrulee:
    """Asynchronous client for the crawlbrulee API.

    Example::

        from crawlbrulee import AsyncCrawlbrulee

        async with AsyncCrawlbrulee(api_key="cble_…") as client:
            page = await client.scrape(
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
        transport: AsyncTransport | None = None,
    ) -> None:
        key = require_api_key(api_key)
        self._transport = transport or AsyncTransport(
            api_key=key, base_url=base_url, timeout=timeout
        )
        #: Resolved base URL (trailing slash stripped).
        self.base_url = self._transport.base_url

    @classmethod
    def from_env(cls, **overrides: Any) -> AsyncCrawlbrulee:
        """Build a client reading the API key from ``CRAWLBRULEE_API_KEY``."""
        api_key = read_env(ENV_API_KEY)
        if not api_key:
            raise CrawlbruleeError(
                f"{ENV_API_KEY} is not set. Export it in your shell, or pass "
                "api_key=... to AsyncCrawlbrulee(...).",
                status=0,
                error_name=None,
            )
        return cls(api_key, **overrides)

    async def __aenter__(self) -> AsyncCrawlbrulee:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._transport.aclose()

    # ------------------------------------------------------------------
    # Scraping
    # ------------------------------------------------------------------

    async def scrape(
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
        """Scrape a URL and return the extracted content. Awaits until done."""
        body = scrape_body(url, extract, cache, require_js, exclude_selectors, proxy, location)
        data = await self._transport.request("POST", "/api/scrape", body=body, timeout=timeout)
        return from_dict(ScrapeResponse, data)

    async def scrape_async(
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
        data = await self._transport.request(
            "POST", "/api/scrape/async", body=body, timeout=timeout
        )
        return from_dict(AsyncScrapeResponse, data)

    async def get_scrape_status(
        self, job_id: str, *, timeout: float | None = None
    ) -> AsyncJobStatusResponse:
        """Look up the current status of an async scrape job."""
        require_job_id(job_id)
        data = await self._transport.request("GET", scrape_status_path(job_id), timeout=timeout)
        return from_dict(AsyncJobStatusResponse, data)

    async def get_scrape_result(
        self, job_id: str, *, timeout: float | None = None
    ) -> ScrapeResponse:
        """Fetch the result of a completed async scrape job."""
        require_job_id(job_id)
        data = await self._transport.request("GET", scrape_result_path(job_id), timeout=timeout)
        return from_dict(ScrapeResponse, data)

    async def wait_for_scrape(
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
            status = await self.get_scrape_status(job_id)
            if status.status == "done":
                return await self.get_scrape_result(job_id)
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
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    async def map(
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
        data = await self._transport.request("POST", "/api/map", body=body, timeout=timeout)
        return from_dict(MapResponse, data)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def usage(self, *, timeout: float | None = None) -> UsageResponse:
        """Return the current billing-cycle usage snapshot."""
        data = await self._transport.request("GET", "/api/usage", timeout=timeout)
        return from_dict(UsageResponse, data)

    async def whoami(self, *, timeout: float | None = None) -> WhoamiResponse:
        """Return the organization + token identity behind the API key."""
        data = await self._transport.request("GET", "/api/whoami", timeout=timeout)
        return from_dict(WhoamiResponse, data)
