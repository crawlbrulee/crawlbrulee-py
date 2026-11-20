"""Request and response shapes for ``POST /api/scrape`` (and its async variant)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypeAlias, TypedDict

from .common import ScreenshotRequest, ScreenshotType, Usage

# --------------------------------------------------------------------------
# Request shapes (nested; top-level fields are method keyword arguments)
# --------------------------------------------------------------------------


#: What an ``extract.elements`` spec returns for each match: ``text`` (the
#: default), ``html`` (the outer HTML) or ``attribute`` (the value of
#: :attr:`ScrapeElementSpec.attribute`).
ScrapeElementOutput = Literal["text", "html", "attribute"]


@dataclass
class ScrapeElementSpec:
    """One named value in ``extract.elements``, read by CSS selector.

    A plain selector string does the same as ``ScrapeElementSpec(selector=...)``:
    the text of the first match. Rules and limits:
    https://crawlbrulee.com/docs/scrape/targeted-extraction
    """

    #: CSS selector. At most 500 characters.
    selector: str
    #: What to return for each match. Defaults to ``text``. Leave it out when
    #: you set ``fields``.
    output: ScrapeElementOutput | None = None
    #: The attribute to read when ``output`` is ``attribute``. ``href`` and
    #: ``src`` come back as full urls.
    attribute: str | None = None
    #: ``True`` returns every match as a list instead of the first. Default ``False``.
    all: bool | None = None
    #: Used instead of ``output``: turns each match into an object. Each field is
    #: a name and a selector (or spec) read inside that match; the selector
    #: ``:scope`` reads the match itself, for example the matched element's own
    #: ``href``. Fields nest up to 3 levels; the innermost level has no ``fields``.
    fields: Mapping[str, ScrapeElementSelector] | None = None


class _ScrapeElementSpecDictRequired(TypedDict):
    selector: str


class ScrapeElementSpecDict(_ScrapeElementSpecDictRequired, total=False):
    """The plain-dict form of :class:`ScrapeElementSpec`, with the same keys.

    ``selector`` is required; the other keys are optional.
    """

    output: ScrapeElementOutput
    attribute: str
    all: bool
    fields: Mapping[str, ScrapeElementSelector]


#: A value in ``extract.elements`` (or in :attr:`ScrapeElementSpec.fields`): a
#: selector string, which returns the text of the first match, a
#: :class:`ScrapeElementSpec`, or the same spec as a plain dict
#: (:class:`ScrapeElementSpecDict`).
ScrapeElementSelector: TypeAlias = str | ScrapeElementSpec | ScrapeElementSpecDict

#: The ``extract.elements`` map: a name you pick to a selector string, a
#: :class:`ScrapeElementSpec` or a plain dict spec. Any ``Mapping`` works.
ScrapeElements: TypeAlias = Mapping[str, ScrapeElementSelector]


#: How a PDF lays out the page: ``pages`` (the default), the page on sheets of
#: paper, laid out as in the browser window and shrunk to fit the paper width;
#: or ``single_page``, one page as wide as the browser window and as tall as the
#: web page, up to 15 000 px.
PdfLayout = Literal["pages", "single_page"]

#: Paper size for a PDF with ``layout="pages"``.
PdfPaper = Literal["a4", "letter"]

#: Which style of the site a PDF shows: ``screen`` (the default), the page as it
#: looks on screen, or ``print``, the site's own print style.
PdfMedia = Literal["screen", "print"]


@dataclass
class PdfRequest:
    """PDF settings. Pass this on ``extract.pdf``; ``PdfRequest()`` takes every
    default.

    The PDF is a real document with selectable text and working links,
    backgrounds printed, and no header or footer added. The request runs in a
    browser. It costs what a screenshot costs, and a PDF and a screenshot in one
    request are billed once. When the PDF can't be made (it would be over 50 MB,
    it takes too long, or the page could not be loaded), the rest of the scrape
    still comes back with the ``pdf_unavailable`` warning, and the request costs
    what it costs without the PDF.

    A cached copy of the page answers only when it has a PDF made with the same
    settings, in the same browser window (the screenshot's ``device_mode``,
    ``viewport`` and ``color_scheme``, when the request also asks for a
    screenshot). ``cache.max_age=0`` always makes a new one.

    A PDF on its own is made with the light theme: the PDF has no color setting
    of its own.
    When the same request also asks for a screenshot with
    ``color_scheme="dark"``, the PDF is dark too.
    """

    #: ``pages`` (default): the page on sheets of paper, laid out as in the
    #: browser window (the desktop default, or the screenshot's device and
    #: viewport when the request also asks for one) and shrunk to fit the paper
    #: width. ``single_page``: one page as wide as the browser window and as tall
    #: as the web page, up to 15 000 px; a taller page goes on over more pages,
    #: with the ``pdf_single_page_overflow`` warning.
    layout: PdfLayout | None = None
    #: Paper size for ``layout="pages"``. Defaults to ``a4``. Not allowed with
    #: ``single_page``.
    paper: PdfPaper | None = None
    #: Turn the paper sideways, for ``layout="pages"``. Defaults to ``False``.
    #: Not allowed with ``single_page``.
    landscape: bool | None = None
    #: ``screen`` (default): the page as it looks on screen. ``print``: the
    #: site's own print style, which on many sites hides menus and images; a site
    #: without one looks as on screen.
    media: PdfMedia | None = None


@dataclass
class ScrapeExtract:
    """Which content formats to extract. The default request extracts
    ``markdown + metadata``. Naming other formats keeps these two on; set
    ``markdown=False`` or ``metadata=False`` to turn one off.

    ``extract`` only selects what is returned. Changing it does not change
    whether a request is served from cache. The exceptions are ``screenshot``
    and ``pdf``: a cached copy answers them only when it has a screenshot or
    PDF made with the same settings.
    """

    #: Extract page metadata (title, description, OG/Twitter tags). Default ``True``.
    metadata: bool | None = None
    #: Extract cleaned HTML: the page body with scripts, styles, ads and cookie banners
    #: removed. Default ``False``.
    cleaned_html: bool | None = None
    #: Extract the page as clean Markdown. Default ``True``.
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
    #: Named values to read from the page by CSS selector. Each key is a name you
    #: pick; each value is a selector string, a :class:`ScrapeElementSpec`, or
    #: the same spec as a plain dict (:class:`ScrapeElementSpecDict`). The
    #: values come back in :attr:`ScrapeResponse.elements` under the same names.
    #: No extra credits. See https://crawlbrulee.com/docs/scrape/targeted-extraction
    elements: ScrapeElements | None = None
    #: Save the page as a PDF. Omit to skip; set a :class:`PdfRequest` to enable
    #: (``PdfRequest()`` takes every default). The PDF comes back on
    #: :attr:`ScrapeResponse.pdf`.
    pdf: PdfRequest | None = None


@dataclass
class ScrapeCleanup:
    """What is removed from the page before any output is built.

    Applies to ``markdown``, ``cleaned_html``, ``links``, ``images`` and
    ``elements`` on every engine, and to the screenshot. It never applies to
    ``raw_html`` — that is always the page as it arrived, before anything was
    removed.
    """

    #: Remove ads, cookie banners, consent dialogs and chat widgets. Defaults to
    #: ``True`` server-side. Set it to ``False`` to capture the page as-is, or to
    #: get past a site that refuses to serve an ad-blocking client.
    ads_and_popups: bool | None = None
    #: CSS selectors whose elements are removed before anything is captured. Use
    #: it for a banner or widget ``ads_and_popups`` does not recognise. At most
    #: 100 selectors, each at most 500 characters. Requests with different
    #: selectors here don't share a cache entry.
    exclude_selectors: list[str] | None = None


@dataclass
class ScrapeCache:
    """Cache settings for a scrape request.

    ``max_age`` is the only cache control. A non-zero ``actions_before`` wait
    or scroll disables the cache for that request. A request with ``headers``
    or ``cookies`` never reads from or writes to the cache. Requests with different
    ``cleanup.exclude_selectors`` don't share a cache entry. Changing
    ``extract`` (``elements`` too) does not change whether a request is served
    from cache, except for ``screenshot`` and ``pdf``: a cached copy answers them
    only when it has a screenshot or PDF made with the same settings
    (``color_scheme`` included).
    """

    #: Maximum cache age: a number of seconds (non-negative int) or an ISO-8601
    #: datetime cutoff. Defaults to 2 days when omitted.
    max_age: int | str | None = None


@dataclass
class ScrapeCookie:
    """One of your own cookies to send to the site with the request.

    Sent only to the host of ``url``. Cookies the site sets while redirecting
    are not kept. Up to 20 cookies, each up to 4096 bytes (name and value),
    counted toward the limit on ``headers``. A value may not hold ``;`` or
    start or end with a space. A ``__Secure-``, ``__Host-`` or ``__Http-``
    cookie needs an https url. See
    https://crawlbrulee.com/docs/scrape/custom-headers-and-cookies
    """

    #: The cookie name. Must not be empty.
    name: str
    #: The cookie value. Often a secret, so it is left out of ``repr()``,
    #: which keeps it out of logs, test output and error trackers.
    value: str = field(repr=False)


class ScrapeCookieDict(TypedDict):
    """The plain-dict form of :class:`ScrapeCookie`, with the same keys.

    Both ``name`` and ``value`` are required.
    """

    name: str
    value: str


#: The ``cookies`` list: each entry a :class:`ScrapeCookie` or the same cookie
#: as a plain dict (:class:`ScrapeCookieDict`). A list or a tuple works.
ScrapeCookies: TypeAlias = Sequence[ScrapeCookie | ScrapeCookieDict]


@dataclass
class ScrapeLocation:
    """Optional locale + country emulation for the scrape."""

    #: BCP-47 locale (e.g. ``en-US``): the language to ask the site for.
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

#: One value in :attr:`ScrapeResponse.elements`: a string, an object (from
#: ``fields``, with the same names), a list of either (``all: True``), or
#: ``None`` when nothing matched (``[]`` with ``all: True``).
ScrapeElementValue: TypeAlias = (
    str | dict[str, "ScrapeElementValue"] | list[str | dict[str, "ScrapeElementValue"]] | None
)


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
    #: Signed link to this slice image. Expires 24 hours after the scrape (for an
    #: async scrape, 24 hours after it was submitted). Download the image; don't
    #: keep the link.
    url: str
    properties: ScreenshotProperties
    type: Literal["slice"] = "slice"


@dataclass
class ScreenshotResult:
    """Result block returned when a screenshot was requested."""

    #: Signed link to the full screenshot image. Expires 24 hours after the scrape
    #: (for an async scrape, 24 hours after it was submitted). Download the image;
    #: don't keep the link.
    url: str
    type: ScreenshotType
    properties: ScreenshotProperties
    #: Tile slices, present only when the ``slice`` after-action was requested.
    slices: list[ScreenshotSlice] | None = None


@dataclass
class PdfResult:
    """Result block returned when a PDF was requested and could be made."""

    #: Signed link to download the PDF. Expires 24 hours after the scrape (for an
    #: async scrape, 24 hours after it was submitted; fetching the result again
    #: does not extend it). Download the file; don't keep the link.
    url: str
    #: Size of the PDF file in bytes.
    bytes: int


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

    #: Billing + routing usage for this request (credit cost, resolved proxy, cache).
    usage: Usage


#: Stable codes that can appear in ``ScrapeResponse.warnings``, in three groups.
#:
#: Truncation -- the output was capped, loudly rather than silently, so the
#: payload is partial but still usable:
#:
#: - ``screenshot_truncated`` -- a scrolling full-page capture exceeded the height cap.
#: - ``links_truncated`` -- the page had more than 30 000 links.
#: - ``inline_images_truncated`` -- the page had more than 10 000 inline images.
#: - ``raw_html_truncated`` -- the serialized body HTML exceeded 10 000 000 characters.
#: - ``elements_truncated`` -- at least one ``elements`` value hit a limit (see
#:   https://crawlbrulee.com/docs/scrape/targeted-extraction).
#: - ``pdf_single_page_overflow`` -- a ``single_page`` PDF was taller than the
#:   15 000 px page limit, so it goes on over more pages.
#:
#: Unavailability -- that section's extraction failed, so the field is omitted or
#: empty while the rest of the scrape succeeded. These distinguish "the page had
#: none" from "we couldn't read them":
#:
#: - ``links_unavailable`` -- link extraction failed.
#: - ``inline_images_unavailable`` -- image extraction failed.
#: - ``metadata_unavailable`` -- metadata extraction failed.
#: - ``screenshot_unavailable`` -- a screenshot was asked for, but the page came
#:   back from the ``http`` engine without one.
#: - ``pdf_unavailable`` -- a PDF was asked for, but the page came back without
#:   one: it would have been over 50 MB, it did not finish in time, or the page
#:   could not be loaded in a browser (the site answered an empty error page,
#:   for example). The rest of the result is there.
#:
#: Request notices -- about what the request sent, not about the page:
#:
#: - ``custom_user_agent`` -- the request set its own ``User-Agent`` header;
#:   this can lower the success rate.
#:
#: Deprecated: ``metadata_truncated`` is retired and no longer sent. Metadata has
#: no size limit of its own now. It can still appear on results stored before
#: that change, so it stays in this alias.
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
    "elements_truncated",
    "pdf_single_page_overflow",
    "links_unavailable",
    "inline_images_unavailable",
    "metadata_unavailable",
    "screenshot_unavailable",
    "pdf_unavailable",
    "custom_user_agent",
]


@dataclass
class ScrapeResponse:
    """Successful response from ``POST /api/scrape`` and
    ``GET /api/scrape/result/:job_id``.

    A page the site really served is a result, whatever its own status: a
    ``404``, ``410``, ``401`` or ``503`` page comes back here with its content,
    and :attr:`page_status_code` tells you what the site answered. The sdk does
    not raise for it. Check ``page_status_code`` yourself when a page that is
    not ``2xx`` means something to you.
    """

    #: The URL that was actually scraped, after any redirects, in normalized
    #: form -- the base that ``links``, ``images``, and ``internal`` labels are
    #: computed against.
    url: str
    #: The URL you requested, echoed verbatim -- before any redirects.
    requested_url: str
    #: ``Content-Type`` header returned by the origin.
    content_type: str | None = None
    #: Requested extract fields that aren't supported for this content type
    #: (``"elements"`` when the page is JSON, plain text, XML or markdown, not HTML).
    unsupported_fields: list[str] | None = None
    #: Page content as clean Markdown (when ``extract.markdown``, on by default).
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
    #: request (every other format off: ``markdown=False`` and ``metadata=False``, and
    #: no ``cleaned_html``, ``raw_html``, ``links``, ``images`` or ``elements``) that
    #: can't deliver fails instead -- 422 ``unsupported_screenshot_output``
    #: when the content type can't be screenshotted, 500 on a capture failure -- and
    #: isn't billed. A request with only a screenshot and a PDF counts as
    #: screenshot-only here.
    #:
    #: An async job like that ends ``failed`` and isn't billed either: reading
    #: its result raises the same 422 (:class:`~crawlbrulee.ValidationError`)
    #: when the content type can't be captured, or a 400 ``job_failed`` when no
    #: capture could be made.
    screenshot: ScreenshotResult | None = None
    #: Extracted page metadata (when ``extract.metadata``, on by default).
    metadata: ScrapeMetadata | None = None
    #: The values asked for in ``extract.elements``, under the same names. Every
    #: requested name is present, at every level of ``fields``. See
    #: :data:`ScrapeElementValue`.
    elements: dict[str, ScrapeElementValue] | None = None
    #: Request-level metadata: billing + routing usage for this request.
    response_meta: ScrapeResponseMeta | None = None
    #: Non-error notices about the scrape (stable codes -- safe to switch on):
    #: an output was capped (``*_truncated``, ``pdf_single_page_overflow``),
    #: could not be extracted (``*_unavailable``), or the request set its own
    #: ``User-Agent`` (``custom_user_agent``); see :data:`ScrapeWarningCode`. Kept as
    #: ``list[str]`` so a code added later still deserializes.
    #:
    #: Warnings are stored with the result, so cache hits and async result
    #: fetches carry them too, filtered to the outputs you requested
    #: (``raw_html_truncated`` always surfaces, since a truncated body also
    #: feeds ``markdown`` and ``cleaned_html``).
    warnings: list[str] | None = None
    #: The HTTP status the target site answered with for the final page, after
    #: redirects (in the browser: the main document, not images or scripts).
    #: A ``404`` page is data, not an error. Billing follows this status:
    #: ``2xx`` and ``4xx`` pages are billed, except ``403``, ``407``, ``408``,
    #: ``429``, ``444`` and ``451``; ``5xx`` pages are never billed.
    #:
    #: ``None`` on an older api version that does not send it.
    page_status_code: int | None = None
    #: The PDF of the page (when ``extract.pdf`` and it could be made). When it
    #: can't be made, this is ``None`` and ``warnings`` carries
    #: ``pdf_unavailable``, while the rest of the scrape comes back. Guard for
    #: it (``page.pdf and page.pdf.url``). A PDF-only request (every other format
    #: off: ``markdown=False`` and ``metadata=False``, and no ``cleaned_html``,
    #: ``raw_html``, ``links``, ``images``, ``elements`` or screenshot) whose
    #: content type can't be made into a PDF fails with a 422
    #: ``unsupported_pdf_output`` (:class:`~crawlbrulee.ValidationError`) and
    #: isn't billed; when no PDF could be made, it fails with a 500 and isn't
    #: billed.
    #:
    #: An async job like that ends ``failed`` and isn't billed either: reading
    #: its result raises the same 422 when the content type can't be made into
    #: a PDF, or a 400 ``job_failed`` when no PDF could be made.
    pdf: PdfResult | None = None
