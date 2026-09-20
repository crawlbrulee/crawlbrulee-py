"""Request and response shapes for ``POST /api/map``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .common import MapUsage

#: Which limit stopped sitemap discovery first. Only ``max_urls`` is something
#: the caller can change from the request -- ask again with a higher ``max_urls``
#: to get more. ``time`` means discovery ran out of its time budget,
#: ``file_budget`` that the site has more sitemap files than one request reads,
#: ``depth`` that its sitemap indexes nest too deeply, and ``file_size`` that a
#: sitemap file was too large to read. ``unread_files`` means a sitemap file the
#: site publishes could not be read at all this time -- the request for it failed
#: or was rate limited, or the file was not a readable sitemap. ``unread_files``
#: is often temporary, so asking again later can return more. For ``time``,
#: ``file_budget``, ``depth`` and ``file_size`` a retry will not help.
DiscoveryCapReason = Literal[
    "max_urls",
    "time",
    "file_budget",
    "depth",
    "file_size",
    "unread_files",
]

# --------------------------------------------------------------------------
# Request shapes (nested; top-level fields are method keyword arguments)
# --------------------------------------------------------------------------


@dataclass
class MapTypes:
    """Filter which link types appear in the map result."""

    #: Include internal links (same domain). Default ``True``.
    internal: bool | None = None
    #: Include links to subdomains of the target. Default ``True``.
    internal_subdomains: bool | None = None
    #: Include external links (different domains). Default ``True``.
    external: bool | None = None


@dataclass
class MapCache:
    """Cache settings for a map request."""

    #: Maximum cache age -- seconds or an ISO-8601 datetime cutoff.
    #: Defaults to 7 days when omitted.
    max_age: int | str | None = None


@dataclass
class MapLocation:
    """Country-only egress emulation (map requests have no locale knob)."""

    #: ISO 3166-1 alpha-2 country code (e.g. ``US``). Case-insensitive.
    country: str | None = None


# --------------------------------------------------------------------------
# Response shapes
# --------------------------------------------------------------------------


@dataclass
class MapLinkItem:
    """Single discovered URL in a map result.

    ``url`` is the whole shape.
    """

    url: str


@dataclass
class MapPagination:
    """Pagination details on a map response."""

    page: int
    limit: int
    #: Total number of URLs in the stored map.
    total: int
    total_pages: int
    has_more: bool


@dataclass
class MapTruncation:
    """Whether the stored or returned map was truncated.

    The last three fields were added after the first release. A server that
    predates them simply omits them, and the defaults below then read as
    "nothing was cut short", so an older server degrades quietly instead of
    raising.
    """

    #: Whether the stored map hit the 100000-URL storage cap.
    storage_capped: bool
    #: Whether more links were eligible than ``max_urls``, so the list was
    #: trimmed. Discovery itself stops at ``max_urls``, so this is normally
    #: true only when home-page links pushed the total past it. See
    #: :attr:`discovery_cap_reason` for a discovery stop.
    response_capped: bool
    #: Total URLs found before the ``max_urls`` cap was applied.
    total_before_max_urls: int
    #: Total URLs detected during discovery before the storage cap was applied.
    total_detected_before_storage_cap: int
    #: Whether sitemap discovery stopped before it had read every sitemap file
    #: it found. When true, the site has more pages than this map lists.
    discovery_capped: bool = False
    #: How many sitemap files were skipped or only partly read during discovery
    #: -- a file was too large, could not be fetched, or a discovery limit was
    #: reached.
    sitemaps_skipped: int = 0
    #: Which limit stopped sitemap discovery first, or ``None`` when nothing
    #: did. Only ``"max_urls"`` is actionable from the request. ``"unread_files"``
    #: is often temporary, so asking again later can return a fuller map.
    discovery_cap_reason: DiscoveryCapReason | None = None


@dataclass
class MapResponseMeta:
    """Usage + pagination + truncation metadata for a map result set."""

    #: Billing + routing usage for this request (credits, resolved proxy, cache).
    usage: MapUsage
    pagination: MapPagination
    truncation: MapTruncation


@dataclass
class MapResponse:
    """Success response from ``POST /api/map``.

    Returned URLs are normalized, the same way ``/scrape`` normalizes its
    returned ``url``.
    """

    #: The current page of discovered URLs.
    links: list[MapLinkItem]
    #: Pagination + truncation metadata for the result set.
    response_meta: MapResponseMeta
