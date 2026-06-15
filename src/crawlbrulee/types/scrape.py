"""Request and response shapes for ``POST /api/scrape`` (and its async variant)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .common import ScreenshotRequest, ScreenshotType

# --------------------------------------------------------------------------
# Request shapes (nested; top-level fields are method keyword arguments)
# --------------------------------------------------------------------------


@dataclass
class ScrapeExtract:
    """Which content formats to extract. The default request extracts
    ``metadata + cleaned_html``."""

    #: Extract page metadata (title, description, OG/Twitter tags). Default ``True``.
    metadata: bool | None = None
    #: Extract cleaned HTML (main content only). Default ``True``.
    cleaned_html: bool | None = None
    #: Extract the page as clean Markdown. Default ``False``.
    markdown: bool | None = None
    #: Return the raw, unprocessed HTML. Default ``False``.
    raw_html: bool | None = None
    #: Extract all links found on the page. Default ``False``.
    links: bool | None = None
    #: Extract all inline images found on the page. Default ``False``.
    images: bool | None = None
    #: Capture a screenshot. Omit to skip; set a ``ScreenshotRequest`` to enable.
    screenshot: ScreenshotRequest | None = None


@dataclass
class ScrapeCache:
    """Cache settings for a scrape request."""

    #: Maximum cache age: a number of seconds (non-negative int) or an ISO-8601
    #: datetime cutoff. Defaults to 2 days when omitted.
    max_age: int | str | None = None
    #: Treat URLs with different query params as the same entry. Default ``False``.
    ignore_query_params: bool | None = None


@dataclass
class ScrapeLocation:
    """Optional locale + country emulation for the scrape."""

    #: BCP-47 locale (e.g. ``en-US``). Sent as ``Accept-Language``.
    locale: str | None = None
    #: ISO 3166-1 alpha-2 country code (e.g. ``US``). Drives the emulated timezone.
    country: str | None = None


@dataclass
class ScrapeWebhook:
    """Per-job completion webhook for an **async** scrape (``scrape_async`` only).

    When set, the API sends a single signed ``scrape.complete`` POST to ``url``
    once the job reaches a terminal state. Verify deliveries with
    :func:`crawlbrulee.verify_webhook_signature` using your organization webhook
    secret (configured in the dashboard); there is no per-request secret.

    The sync :meth:`~crawlbrulee.Crawlbrulee.scrape` does **not** accept a
    webhook -- its response *is* the result -- so this is async-only.
    """

    #: Endpoint to receive the signed completion POST. http/https URL, max 2048
    #: chars. **HTTPS is required in production.**
    url: str
    #: Opaque correlation object echoed verbatim in the webhook payload's
    #: ``data.metadata``. Max 2048 bytes when JSON-serialized. Use it to route
    #: deliveries without keeping your own ``job_id`` mapping.
    metadata: dict[str, Any] | None = None


# --------------------------------------------------------------------------
# Response shapes
# --------------------------------------------------------------------------


@dataclass
class ScreenshotViewportInfo:
    """Viewport metadata returned alongside a captured screenshot."""

    width: int
    height: int
    device_scale_factor: int


@dataclass
class ScreenshotProperties:
    """Image-level properties of a captured screenshot (or tile)."""

    file_name: str
    mime: str
    width: int
    height: int
    viewport: ScreenshotViewportInfo


@dataclass
class ScreenshotSlice:
    """One horizontal tile of a sliced full-page screenshot."""

    row_nr: int
    url: str
    properties: ScreenshotProperties
    type: Literal["slice"] = "slice"


@dataclass
class ScreenshotResult:
    """Result block returned when a screenshot was requested."""

    url: str
    type: ScreenshotType
    properties: ScreenshotProperties
    #: Tile slices, present only when the ``slice`` after-action was requested.
    slices: list[ScreenshotSlice] | None = None


@dataclass
class PageInlineImage:
    """A single inline image discovered on the page."""

    url: str
    #: Alt text of the image, or ``None`` if not set.
    alt: str | None = None


@dataclass
class PageLink:
    """A single link discovered on the page."""

    text: str
    href: str
    #: Whether the link points to the same domain as the scraped page.
    internal: bool


@dataclass
class ScrapeMetadata:
    """Structured page metadata extracted from ``<head>``."""

    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    canonical: str | None = None

    og_url: str | None = None
    og_title: str | None = None
    og_description: str | None = None
    og_type: str | None = None
    og_site_name: str | None = None
    og_locale: str | None = None
    og_locale_alternate: list[str] | None = None
    og_image: str | None = None

    author: str | None = None
    date_modified: str | None = None
    date_published: str | None = None

    twitter_site: str | None = None
    twitter_card: str | None = None
    twitter_description: str | None = None
    twitter_title: str | None = None
    twitter_image: str | None = None

    robots: str | None = None
    favicon_url: str | None = None


@dataclass
class ScrapeResponse:
    """Successful response from ``POST /api/scrape`` and
    ``GET /api/scrape/result/:jobId``."""

    #: The URL that was actually scraped (after any redirects).
    url: str
    #: ``Content-Type`` header returned by the origin.
    content_type: str | None = None
    #: Requested extract fields that aren't supported for this content type.
    unsupported_fields: list[str] | None = None
    #: Page content as clean Markdown (when ``extract.markdown``).
    markdown: str | None = None
    #: Cleaned HTML of the main page content (when ``extract.cleaned_html``).
    cleaned_html: str | None = None
    #: Raw, unprocessed HTML (when ``extract.raw_html``).
    raw_html: str | None = None
    #: Inline images discovered on the page (when ``extract.images``).
    images: list[PageInlineImage] | None = None
    #: Links discovered on the page (when ``extract.links``).
    links: list[PageLink] | None = None
    #: Captured screenshot (when ``extract.screenshot``).
    screenshot: ScreenshotResult | None = None
    #: Extracted page metadata (when ``extract.metadata``, on by default).
    metadata: ScrapeMetadata | None = None
    #: Non-error notices about the scrape (stable codes -- safe to switch on).
    warnings: list[str] | None = None
