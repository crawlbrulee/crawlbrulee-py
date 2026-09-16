"""Shared primitive types used across crawlbrulee request and response shapes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

#: Proxy tier used to route the fetch.
#:
#: - ``basic`` -- datacenter proxy, lowest cost.
#: - ``advanced`` -- enhanced proxy tier with a higher success rate.
#: - ``auto`` -- tries the basic tier first and escalates to advanced on failure;
#:   billed at the delivered tier (default).
ProxyTier = Literal["basic", "advanced", "auto"]

#: The proxy tier actually used to route the fetch, as reported back on
#: ``response_meta.usage.proxy``. Always a concrete tier -- ``auto`` is resolved
#: server-side to ``basic`` or ``advanced`` and is never echoed here.
ResolvedProxyTier = Literal["basic", "advanced"]

#: Engine base the operation was billed at. This reflects what the server
#: delivered, not what the request asked for. ``cache`` identifies a cache hit.
BillingEngine = Literal["http", "browser", "screenshot", "cache"]
MapBillingEngine = Literal["http", "cache"]

#: Screenshot capture mode: visible viewport or the full scrollable page.
ScreenshotType = Literal["viewport", "full_page"]

#: Emulated device class for the viewport (drives default width/height).
ScreenshotDeviceMode = Literal["desktop", "mobile"]


@dataclass
class ScreenshotWaitAction:
    """A ``wait`` action: pause for ``ms`` milliseconds before the next step."""

    #: Milliseconds to wait. Must be a non-negative integer.
    ms: int
    type: Literal["wait"] = "wait"


@dataclass
class ScreenshotScrollAction:
    """A ``scroll`` action: scroll the page by ``pixels`` (positive = down)."""

    #: Pixels to scroll. Positive scrolls down, negative scrolls up.
    pixels: int
    type: Literal["scroll"] = "scroll"


@dataclass
class ScreenshotSliceAction:
    """Cut the screenshot into horizontal tiles of ``height`` px after capture."""

    #: Tile height in pixels. Minimum 500.
    height: int
    type: Literal["slice"] = "slice"


#: Actions performed before the screenshot is taken. The server caps the total
#: wait time (~20 s) and total absolute scroll distance (~50 000 px) across the
#: list; at most 5 actions are accepted.
ScreenshotBeforeAction = ScreenshotWaitAction | ScreenshotScrollAction

#: Action performed after the screenshot is taken. Currently only ``slice``.
ScreenshotAfterAction = ScreenshotSliceAction


@dataclass
class ScreenshotViewport:
    """Custom browser viewport dimensions used during a screenshot capture."""

    #: Viewport width in pixels. Integer in ``[16, 10000]``; out-of-range values
    #: are rejected with a 400.
    width: int
    #: Viewport height in pixels. Integer in ``[16, 10000]``; out-of-range values
    #: are rejected with a 400.
    height: int
    #: Device pixel ratio (e.g. 2 for retina). Fractional values are allowed;
    #: must be in ``[1, 3]``. Defaults to 1 server-side.
    device_scale_factor: float | None = None


@dataclass
class ScreenshotRequest:
    """Screenshot capture configuration. Pass this on ``extract.screenshot``."""

    #: Capture mode: ``viewport`` (visible only) or ``full_page``.
    type: ScreenshotType
    #: Custom viewport. If omitted, the ``device_mode`` defaults are used.
    viewport: ScreenshotViewport | None = None
    #: Emulate desktop or mobile. Defaults to ``desktop``.
    device_mode: ScreenshotDeviceMode | None = None
    #: Pre-capture actions (waits and scrolls). Maximum 5 entries.
    actions_before: list[ScreenshotWaitAction | ScreenshotScrollAction] | None = None
    #: Post-capture actions (e.g. slice into tiles). Maximum 1 entry.
    actions_after: list[ScreenshotSliceAction] | None = None


@dataclass
class Usage:
    """Per-request billing + routing usage, reported on ``response_meta.usage``.

    Returned on every scrape success, on a terminal async status, and in the
    ``scrape.complete`` webhook payload, so callers can attribute spend and see
    which proxy tier actually ran -- without a separate ``/api/usage`` call.
    """

    #: Credits charged for this request: engine base multiplied by the resolved
    #: proxy multiplier, plus ``screenshot_slices``.
    credits: int
    #: Engine base billed for the delivered result: ``http`` (1), ``browser``
    #: (3), ``screenshot`` (5), or ``cache`` (0).
    engine: BillingEngine
    #: The proxy tier actually used (the resolved tier -- never ``auto``).
    #: ``advanced`` multiplies the engine base by 5.
    proxy: ResolvedProxyTier
    #: Screenshot-slice add-on billed for this request: ``1`` when slices were
    #: produced during this request, otherwise ``0``.
    screenshot_slices: int


@dataclass
class MapUsage:
    """Per-request billing + routing usage for a map response."""

    #: Credits charged for this request: engine base multiplied by the
    #: resolved proxy multiplier.
    credits: int
    #: ``http`` for fresh discovery or ``cache`` for a cached result.
    engine: MapBillingEngine
    #: The proxy tier actually used (the resolved tier -- never ``auto``).
    proxy: ResolvedProxyTier


#: Machine-readable error names returned by the crawlbrulee API. Stable
#: identifiers -- clients can switch on them.
ApiErrorName = Literal[
    "usage_allocation_error",
    "request_timeout",
    "invalid_url",
    "url_too_long",
    "client_closed_request",
    "reset_password_token_expired",
    "user_not_found",
    "unsupported_url_schema",
    "url_credentials_not_supported",
    "blocked_url",
    "scrape_error",
    "job_failed",
    "incorrect_login_method_used",
    "not_found",
    "invalid_credentials",
    "resource_already_exists",
    "access_denied",
    "internal_server_error",
    "service_unavailable",
    "too_many_requests",
    "unsupported_content",
    "unsupported_screenshot_output",
    "validation_error",
    "antibot_blocked",
    "too_many_redirects",
    "page_too_large",
]

#: Reason a usage allocation was denied (when ``name == usage_allocation_error``).
UsageAllocationReason = Literal[
    "credit_limit",
    "concurrency_limit",
    "duplicate_reservation",
    "internal_error",
]


class UsageLimitDetails(TypedDict, total=False):
    """Snapshot of the org's current usage at the moment an error was raised."""

    current_usage: int
    current_reserved: int
    max_credits: int
    current_concurrent: int
    max_concurrent: int


class UsageAllocationErrorDetails(TypedDict, total=False):
    """Discriminated detail for ``name == usage_allocation_error``."""

    error_name: Literal["usage_allocation_error"]
    reason: UsageAllocationReason
    details: UsageLimitDetails


class RateLimitErrorDetails(TypedDict, total=False):
    """Discriminated detail for ``name == too_many_requests``."""

    error_name: Literal["too_many_requests"]
    retry_after_ms: int
    limited_by: str


class ApiErrorResponse(TypedDict, total=False):
    """Standard JSON error shape returned for any non-2xx response."""

    name: ApiErrorName
    message: str
    details: dict[str, object]
