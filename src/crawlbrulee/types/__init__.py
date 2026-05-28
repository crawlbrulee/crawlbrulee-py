"""Public request/response types for the crawlbrulee SDK.

These mirror the canonical API wire shapes. Response objects are returned by the
client methods; the nested request shapes (``ScrapeExtract``, ``ScreenshotRequest``,
``MapTypes``, ...) are passed to method keyword arguments (or as plain dicts).
"""

from __future__ import annotations

from .account import UsageResponse, WhoamiResponse
from .async_ import AsyncJobStatus, AsyncJobStatusResponse, AsyncScrapeResponse
from .common import (
    ApiErrorName,
    ApiErrorResponse,
    ProxyTier,
    RateLimitErrorDetails,
    ScreenshotAfterAction,
    ScreenshotBeforeAction,
    ScreenshotCleanup,
    ScreenshotDeviceMode,
    ScreenshotRequest,
    ScreenshotScrollAction,
    ScreenshotSliceAction,
    ScreenshotType,
    ScreenshotViewport,
    ScreenshotWaitAction,
    UsageAllocationErrorDetails,
    UsageAllocationReason,
    UsageLimitDetails,
)
from .map import (
    MapCache,
    MapLinkItem,
    MapLocation,
    MapPagination,
    MapResponse,
    MapResponseMeta,
    MapTruncation,
    MapTypes,
)
from .scrape import (
    PageInlineImage,
    PageLink,
    ScrapeCache,
    ScrapeExtract,
    ScrapeLocation,
    ScrapeMetadata,
    ScrapeResponse,
    ScreenshotProperties,
    ScreenshotResult,
    ScreenshotSlice,
    ScreenshotViewportInfo,
)

__all__ = [
    # common
    "ProxyTier",
    "ScreenshotType",
    "ScreenshotDeviceMode",
    "ScreenshotCleanup",
    "ScreenshotWaitAction",
    "ScreenshotScrollAction",
    "ScreenshotSliceAction",
    "ScreenshotBeforeAction",
    "ScreenshotAfterAction",
    "ScreenshotViewport",
    "ScreenshotRequest",
    "ApiErrorName",
    "ApiErrorResponse",
    "UsageAllocationReason",
    "UsageLimitDetails",
    "UsageAllocationErrorDetails",
    "RateLimitErrorDetails",
    # scrape
    "ScrapeExtract",
    "ScrapeCache",
    "ScrapeLocation",
    "ScreenshotViewportInfo",
    "ScreenshotProperties",
    "ScreenshotSlice",
    "ScreenshotResult",
    "PageInlineImage",
    "PageLink",
    "ScrapeMetadata",
    "ScrapeResponse",
    # map
    "MapTypes",
    "MapCache",
    "MapLocation",
    "MapLinkItem",
    "MapPagination",
    "MapTruncation",
    "MapResponseMeta",
    "MapResponse",
    # async
    "AsyncJobStatus",
    "AsyncScrapeResponse",
    "AsyncJobStatusResponse",
    # account
    "UsageResponse",
    "WhoamiResponse",
]
