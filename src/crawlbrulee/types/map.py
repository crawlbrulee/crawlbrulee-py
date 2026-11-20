"""Request and response shapes for ``POST /api/map``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .common import MapUsage

#: Which limit stopped sitemap discovery first. ``max_results``: your own
#: ``max_results`` was reached. Ask again with a higher one to get more.
#: ``depth``: there are sitemap files past the ``depth`` you asked for. That is
#: the answer to the depth you chose, not a fault: with ``depth=0`` it is how a
#: site's top sitemap files are listed, and with ``depth=1`` and
#: ``entries="sitemaps"`` how the top files and every file they list are
#: listed. The files past it are in ``unread_sitemaps``; read each one with
#: ``sitemap_url``, or ask with a higher depth. ``time``: discovery
#: ran out of its time budget. ``file_budget``: the site has more sitemap files
#: than one request reads. ``file_size``: a sitemap file was too large. A file
#: that says up front that it is over the size limit is not downloaded: nothing
#: comes back from it, and it is listed in ``unread_sitemaps``. A file of pages
#: that turns out too large while it is read returns the links in its first
#: part. Any other file that turns out too large, such as a sitemap index,
#: returns nothing and is listed. ``unread_files``: a sitemap file the site
#: publishes could not be read whole this time (the request failed or was rate
#: limited, the download broke off, or the file was not a readable sitemap).
#: When a download broke off, the links received before the break are returned,
#: and the file is listed in ``unread_sitemaps``. Asking again later can return
#: more.
DiscoveryCapReason = Literal[
    "max_results",
    "time",
    "file_budget",
    "depth",
    "file_size",
    "unread_files",
]

#: What a map returns, sent as ``entries``: ``pages`` (page addresses, the
#: default), ``sitemaps`` (sitemap files, of type ``sitemap`` or
#: ``sitemap_index``) or ``all`` (both).
MapEntries = Literal["pages", "sitemaps", "all"]

#: What a link in a map result is. ``page``: a page address.
#: ``sitemap_index``: a sitemap file that this map found to be a sitemap index
#: (a file that lists other sitemap files), whether it read all of the file,
#: part of it, or only its start. Such a file can also be in
#: ``unread_sitemaps`` when this map did not read all of it. ``sitemap``: any
#: other sitemap file: one that lists pages, or one whose kind this map did not
#: learn (past ``depth``, or it could not be read). Read a ``sitemap`` or
#: ``sitemap_index`` file with ``sitemap_url`` in another call (a file on
#: another site only when the site's robots.txt names its host).
MapLinkType = Literal["page", "sitemap", "sitemap_index"]

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
    """Single discovered URL in a map result: ``url``, ``type`` and ``lastmod``."""

    url: str
    #: ``page`` for a page address; ``sitemap`` or ``sitemap_index`` for a
    #: sitemap file you can read with ``sitemap_url`` in another call (see
    #: :data:`MapLinkType`). A link found on the home page is a ``page``.
    #: Always sent by the api; an older api that predates it reads as
    #: ``page``, which is what every link was then.
    type: MapLinkType = "page"
    #: The entry's ``lastmod`` from the sitemap, as an ISO 8601 date and time
    #: in UTC, or ``None`` when the sitemap gives none or it can't be read.
    #: Always ``None`` for a link found on the home page.
    lastmod: str | None = None


@dataclass
class MapPagination:
    """Pagination details on a map response."""

    page: int
    limit: int
    #: How many links this answer holds across all its pages, after
    #: ``entries``, ``types`` and ``max_results`` are applied.
    total: int
    total_pages: int
    has_more: bool


@dataclass
class MapTruncation:
    """Whether the stored or returned map was truncated.

    Fields added after the first release have defaults. A server that predates
    them omits them, and the defaults then read as "nothing was cut
    short", so an older server degrades quietly instead of raising.
    """

    #: Whether the map found more than 100000 URLs, the most one map holds, so
    #: some were left out.
    storage_capped: bool
    #: Whether more links were eligible than ``max_results``, so the list was
    #: trimmed. Discovery itself stops at ``max_results``, so this is normally
    #: true only when home-page links pushed the total past it. See
    #: :attr:`discovery_cap_reason` for a discovery stop.
    response_capped: bool
    #: Deprecated: use :attr:`total_before_max_results`, which always has the
    #: same value. The api removes ``total_before_max_urls`` on 2027-02-01.
    total_before_max_urls: int = 0
    #: Total URLs found, before the 100000-URL limit of one map.
    total_detected_before_storage_cap: int = 0
    #: Whether sitemap discovery stopped before it had read every sitemap file
    #: it found. When true, the site has more pages than this map lists.
    discovery_capped: bool = False
    #: How many sitemap files were skipped or only partly read during discovery.
    sitemaps_skipped: int = 0
    #: Which limit stopped sitemap discovery first, or ``None`` when nothing
    #: did. See :data:`DiscoveryCapReason`.
    discovery_cap_reason: DiscoveryCapReason | None = None
    #: Total links found before ``max_results`` was applied.
    total_before_max_results: int = 0
    #: The sitemap files this call knew about but did not read whole, because a
    #: limit stopped it, the file could not be read, or its download broke off.
    #: Read each one with ``sitemap_url`` in another call, except a file that
    #: says it is over the size limit: no call reads that one. Up to 1000
    #: addresses; empty when every file was read. When this list is full, send
    #: the same request with ``entries="sitemaps"`` to get every sitemap file as
    #: a link, paged.
    unread_sitemaps: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # The two totals always hold the same value. When the api sends only one
        # (an older api, or after the old name is removed), fill in the other.
        if self.total_before_max_results == 0:
            self.total_before_max_results = self.total_before_max_urls
        elif self.total_before_max_urls == 0:
            self.total_before_max_urls = self.total_before_max_results


@dataclass
class MapResponseMeta:
    """Usage + pagination + truncation metadata for a map result set."""

    #: Billing + routing usage for this request (credit cost, resolved proxy, cache).
    usage: MapUsage
    pagination: MapPagination
    truncation: MapTruncation


@dataclass
class MapResponse:
    """Success response from ``POST /api/map``.

    Returned URLs are normalized, the same way ``/scrape`` normalizes its
    returned ``url``.
    """

    #: The current page of discovered URLs, each with its ``type`` and
    #: ``lastmod``. The site root is listed only when a sitemap lists it.
    links: list[MapLinkItem]
    #: Pagination + truncation metadata for the result set.
    response_meta: MapResponseMeta
