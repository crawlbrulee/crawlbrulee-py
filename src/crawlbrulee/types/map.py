"""Request and response shapes for ``POST /api/map``."""

from __future__ import annotations

from dataclasses import dataclass

from .common import Usage

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
    """Single discovered URL in a map result."""

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
    """Whether the stored or returned map was truncated."""

    #: Whether the stored map was capped by ``max_urls``.
    storage_capped: bool
    #: Whether the response was capped by pagination.
    response_capped: bool
    #: Total URLs found before the ``max_urls`` cap was applied.
    total_before_max_urls: int
    #: Total URLs detected during discovery before the storage cap was applied.
    total_detected_before_storage_cap: int


@dataclass
class MapResponseMeta:
    """Usage + pagination + truncation metadata for a map result set."""

    #: Billing + routing usage for this request (credits, resolved proxy, cache).
    usage: Usage
    pagination: MapPagination
    truncation: MapTruncation


@dataclass
class MapResponse:
    """Success response from ``POST /api/map``."""

    #: The current page of discovered URLs.
    links: list[MapLinkItem]
    #: Pagination + truncation metadata for the result set.
    response_meta: MapResponseMeta
