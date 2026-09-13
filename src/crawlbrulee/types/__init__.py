"""Public request/response types for the crawlbrulee SDK.

These mirror the canonical API wire shapes. Response objects are returned by the
client methods; the nested request shapes (``ScrapeExtract``, ``ScreenshotRequest``,
``MapTypes``, ...) are passed to method keyword arguments (or as plain dicts).
"""

from __future__ import annotations

from .account import UsageResponse, WhoamiResponse
from .async_ import (
    AsyncJobStatus,
    AsyncJobStatusResponse,
    AsyncScrapeResponse,
    AsyncStatusMeta,
)
from .common import (
    ApiErrorName,
    ApiErrorResponse,
    BillingEngine,
    MapBillingEngine,
    MapUsage,
    ProxyTier,
    RateLimitErrorDetails,
    ResolvedProxyTier,
    ScreenshotAfterAction,
    ScreenshotBeforeAction,
    ScreenshotDeviceMode,
    ScreenshotRequest,
    ScreenshotScrollAction,
    ScreenshotSliceAction,
    ScreenshotType,
    ScreenshotViewport,
    ScreenshotWaitAction,
    Usage,
    UsageAllocationErrorDetails,
    UsageAllocationReason,
    UsageLimitDetails,
)
from .map import (
    DiscoveryCapReason,
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
    ScrapeCleanup,
    ScrapeExtract,
    ScrapeLocation,
    ScrapeMetadata,
    ScrapeResponse,
    ScrapeResponseMeta,
    ScrapeWarningCode,
    ScrapeWebhook,
    ScreenshotProperties,
    ScreenshotResult,
    ScreenshotSlice,
    ScreenshotViewportInfo,
)
from .webhooks import (
    ScrapeCompleteWebhook,
    ScrapeCompleteWebhookData,
    ScrapeCompleteWebhookMeta,
)

__all__ = [
    # common
    "ProxyTier",
    "ResolvedProxyTier",
    "BillingEngine",
    "MapBillingEngine",
    "ScreenshotType",
    "ScreenshotDeviceMode",
    "ScreenshotWaitAction",
    "ScreenshotScrollAction",
    "ScreenshotSliceAction",
    "ScreenshotBeforeAction",
    "ScreenshotAfterAction",
    "ScreenshotViewport",
    "ScreenshotRequest",
    "Usage",
    "MapUsage",
    "ApiErrorName",
    "ApiErrorResponse",
    "UsageAllocationReason",
    "UsageLimitDetails",
    "UsageAllocationErrorDetails",
    "RateLimitErrorDetails",
    # scrape
    "ScrapeExtract",
    "ScrapeCache",
    "ScrapeCleanup",
    "ScrapeLocation",
    "ScrapeWebhook",
    "ScreenshotViewportInfo",
    "ScreenshotProperties",
    "ScreenshotSlice",
    "ScreenshotResult",
    "PageInlineImage",
    "PageLink",
    "ScrapeMetadata",
    "ScrapeResponseMeta",
    "ScrapeResponse",
    "ScrapeWarningCode",
    # map
    "DiscoveryCapReason",
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
    "AsyncStatusMeta",
    "AsyncJobStatusResponse",
    # account
    "UsageResponse",
    "WhoamiResponse",
    # webhooks
    "ScrapeCompleteWebhook",
    "ScrapeCompleteWebhookData",
    "ScrapeCompleteWebhookMeta",
]
