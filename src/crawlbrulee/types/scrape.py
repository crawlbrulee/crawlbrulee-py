"""Request and response shapes for ``POST /api/scrape`` (and its async variant)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from .common import ScreenshotRequest, ScreenshotType, Usage

# --------------------------------------------------------------------------
# Request shapes (nested; top-level fields are method keyword arguments)
# --------------------------------------------------------------------------


@dataclass
class ScrapeExtract:
    """Which content formats to extract. The default request extracts
    ``metadata + cleaned_html``.

    ``extract`` only selects what is returned. Changing it does not change
    whether a request is served from cache.
    """

    #: Extract page metadata (title, description, OG/Twitter tags). Default ``True``.
    #: Read from at most 2 000 000 characters of serialized ``<head>`` HTML per
    #: page; past that the head is truncated (tags after the cut are not parsed)
    #: and a ``metadata_truncated`` warning is returned.
    metadata: bool | None = None
    #: Extract cleaned HTML (main content only). Default ``True``.
    cleaned_html: bool | None = None
    #: Extract the page as clean Markdown. Default ``False``.
    markdown: bool | None = None
    #: Return the raw, unprocessed HTML. Default ``False``. The serialized body
    #: HTML is capped at 10 000 000 characters per page; a longer document is
    #: truncated at a tag boundary (never mid-tag) and a ``raw_html_truncated``
    #: warning is returned.
    raw_html: bool | None = None
    #: Extract all links found on the page. Default ``False``. At most 30 000
    #: links per page; beyond that the list is truncated and a
    #: ``links_truncated`` warning is returned.
    links: bool | None = None
    #: Extract all inline images found on the page. Default ``False``. Image URLs
    #: preserve their query string, and document-relative ``src``s are resolved
    #: against the full page URL (browser parity) -- the same rules as ``links``.
    #: At most 10 000 images per page; beyond that the list is truncated and an
    #: ``inline_images_truncated`` warning is returned.
    images: bool | None = None
    #: Capture a screenshot. Omit to skip; set a ``ScreenshotRequest`` to enable.
    screenshot: ScreenshotRequest | None = None


@dataclass
class ScrapeCleanup:
    """What is removed from the page before any output is built.

    Applies to ``markdown``, ``cleaned_html``, ``links`` and ``images`` on every
    engine, and to the screenshot. It never applies to ``raw_html`` — that is
    always the page as it arrived, before anything was removed.
    """

    #: Remove ads, cookie banners, consent dialogs and chat widgets. Defaults to
    #: ``True`` server-side. Set it to ``False`` to capture the page as-is, or to
    #: get past a site that refuses to serve an ad-blocking client.
    ads_and_popups: bool | None = None
    #: CSS selectors whose elements are removed before anything is captured. Use
    #: it for a banner or widget ``ads_and_popups`` does not recognise. At most
    #: 100 selectors, each at most 500 characters. Sending any selector here
    #: makes the request skip the cache, so it always costs a live fetch.
    exclude_selectors: list[str] | None = None


@dataclass
class ScrapeCache:
    """Cache settings for a scrape request.

    ``max_age`` is the only cache control. ``cleanup.exclude_selectors`` and a
    non-zero ``actions_before`` wait or scroll disable the cache for that
    request.
    """

    #: Maximum cache age: a number of seconds (non-negative int) or an ISO-8601
    #: datetime cutoff. Defaults to 2 days when omitted.
    max_age: int | str | None = None


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
    #: Opaque metadata object echoed verbatim in the webhook payload's
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
    #: Device pixel ratio used for the capture (may be fractional).
    device_scale_factor: float


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

    #: Absolute URL of the image, query string preserved. Document-relative
    #: ``src``s are resolved against the full page URL (browser parity).
    url: str
    #: Alt text of the image, or ``None`` if not set.
    alt: str | None = None


@dataclass
class PageLink:
    """A single link discovered on the page."""

    text: str
    #: The link URL as written on the page, resolved to an absolute URL --
    #: verbatim otherwise (query string, fragment, and duplicates preserved).
    #: Non-http(s) hrefs (``mailto:``, ``tel:``, ...) are dropped.
    href: str
    #: Whether the link points to the same domain as the scraped page. ``www``
    #: and the bare domain count as the same; other subdomains are external.
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
class ScrapeResponseMeta:
    """Request-level metadata on a scrape response (``response_meta``)."""

    #: Billing + routing usage for this request (credits, resolved proxy, cache).
    usage: Usage


#: Stable codes that can appear in ``ScrapeResponse.warnings``, in two families.
#:
#: Truncation -- the output was capped, loudly rather than silently, so the
#: payload is partial but still usable:
#:
#: - ``screenshot_truncated`` -- a scrolling full-page capture exceeded the height cap.
#: - ``links_truncated`` -- the page had more than 30 000 links.
#: - ``inline_images_truncated`` -- the page had more than 10 000 inline images.
#: - ``raw_html_truncated`` -- the serialized body HTML exceeded 10 000 000 characters.
#: - ``metadata_truncated`` -- the serialized head HTML exceeded 2 000 000 characters.
#:
#: Unavailability -- that section's extraction failed, so the field is omitted or
#: empty while the rest of the scrape succeeded. These distinguish "the page had
#: none" from "we couldn't read them":
#:
#: - ``links_unavailable`` -- link extraction failed.
#: - ``inline_images_unavailable`` -- image extraction failed.
#: - ``metadata_unavailable`` -- metadata extraction failed.
#:
#: The page body has no such code: if it can't be extracted the scrape fails
#: outright rather than returning a hollow 200, and isn't billed.
#:
#: ``warnings`` itself stays a plain ``list[str]`` so a code added later still
#: deserializes; use this alias when you want to match the known codes exhaustively.
ScrapeWarningCode = Literal[
    "screenshot_truncated",
    "links_truncated",
    "inline_images_truncated",
    "raw_html_truncated",
    "metadata_truncated",
    "links_unavailable",
    "inline_images_unavailable",
    "metadata_unavailable",
]


@dataclass
class ScrapeResponse:
    """Successful response from ``POST /api/scrape`` and
    ``GET /api/scrape/result/:job_id``."""

    #: The URL that was actually scraped, after any redirects, in normalized
    #: form -- the base that ``links``, ``images``, and ``internal`` labels are
    #: computed against.
    url: str
    #: The URL you requested, echoed verbatim -- before any redirects.
    requested_url: str
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
    #: Captured screenshot (when ``extract.screenshot``). In rare cases a screenshot
    #: can't be captured; when you also requested other outputs, those still arrive
    #: and this is simply left out, so it reads back as ``None``. A screenshot-**only**
    #: request that can't deliver fails instead -- 422 ``unsupported_screenshot_output``
    #: when the content type can't be screenshotted, 500 on a capture failure -- and
    #: isn't billed.
    screenshot: ScreenshotResult | None = None
    #: Extracted page metadata (when ``extract.metadata``, on by default).
    metadata: ScrapeMetadata | None = None
    #: Request-level metadata: billing + routing usage for this request.
    response_meta: ScrapeResponseMeta | None = None
    #: Non-error notices about the scrape (stable codes -- safe to switch on):
    #: an output was capped (``*_truncated``) or could not be extracted
    #: (``*_unavailable``) -- see :data:`ScrapeWarningCode`. Kept as
    #: ``list[str]`` so a code added later still deserializes.
    #:
    #: Warnings are stored with the result, so cache hits and async result
    #: fetches carry them too, filtered to the outputs you requested
    #: (``raw_html_truncated`` always surfaces, since a truncated body also
    #: feeds ``markdown`` and ``cleaned_html``).
    warnings: list[str] | None = None
