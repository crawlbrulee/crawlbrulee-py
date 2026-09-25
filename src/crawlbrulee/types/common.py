"""Shared primitive types used across crawlbrulee request and response shapes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, TypedDict, cast

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


def _require(obj: object, *names: str) -> None:
    missing = [n for n in names if getattr(obj, n) is None]
    if missing:
        raise TypeError(f"{type(obj).__name__} is missing required field(s): {', '.join(missing)}")


def _pair(obj: object, name: str, new: int | None, old: int | None) -> tuple[int, int]:
    value = new if new is not None else old
    if value is None:
        raise TypeError(f"{type(obj).__name__} is missing required field: {name}")
    return value, value


@dataclass
class Usage:
    """Per-request billing + routing usage, reported on ``response_meta.usage``.

    Returned on every scrape success, on a terminal async status, and in the
    ``scrape.complete`` webhook payload, so callers can attribute spend and see
    which proxy tier actually ran -- without a separate ``/api/usage`` call.

    The cost parts always add up::

        total_credit_cost == engine_credit_cost * proxy_multiplier + screenshot_slicing_credit_cost

    A page we don't bill (for example a ``5xx`` page, see
    :attr:`ScrapeResponse.page_status_code <crawlbrulee.ScrapeResponse.page_status_code>`)
    has every cost part at ``0``; ``engine``, ``proxy`` and ``proxy_multiplier``
    are still reported.

    Older api versions only send ``credits``, ``engine``, ``proxy`` and
    ``screenshot_slices``. Then ``total_credit_cost`` and
    ``screenshot_slicing_credit_cost`` are filled in from ``credits`` and
    ``screenshot_slices`` (they always hold the same value), and
    ``engine_credit_cost`` and ``proxy_multiplier`` are ``None``. Once the
    api stops sending the deprecated names, they are filled in from the new
    ones the same way.
    """

    #: **Deprecated:** use :attr:`total_credit_cost`, which always has the same
    #: value. Kept so existing code keeps working; it will be removed in a
    #: future version.
    credits: int = field(default=cast(int, None))
    #: Engine the request was billed at, for the delivered result: ``http``,
    #: ``browser``, ``screenshot``, or ``cache`` (served from cache).
    engine: BillingEngine = field(default=cast(BillingEngine, None))
    #: The proxy tier actually used (the resolved tier -- never ``auto``).
    proxy: ResolvedProxyTier = field(default=cast(ResolvedProxyTier, None))
    #: **Deprecated:** use :attr:`screenshot_slicing_credit_cost`, which always
    #: has the same value. Despite its name this is a ``0``/``1`` charge, not a
    #: count of slices. It will be removed in a future version.
    screenshot_slices: int = field(default=cast(int, None))
    #: Credits charged for this request. ``0`` when nothing is billed: a page
    #: whose status is not billed, or a cache hit (a cache hit that cuts new
    #: screenshot slices still costs the ``1`` slicing add-on).
    total_credit_cost: int = field(default=cast(int, None))
    #: The engine base charged, before the proxy multiplier: ``1`` for
    #: ``http``, ``3`` for ``browser``, ``5`` for ``screenshot``, ``0`` for
    #: ``cache``. Also ``0`` when the page is not billed. ``None`` on an older
    #: api version that does not send it.
    engine_credit_cost: int | None = None
    #: Multiplier of the proxy tier the request ran on: ``1`` for ``basic``,
    #: ``5`` for ``advanced``. Reported even when the engine cost is ``0``.
    #: ``None`` on an older api version that does not send it.
    proxy_multiplier: int | None = None
    #: The screenshot slicing add-on: ``1`` when the screenshot was cut into
    #: slices on this request (a flat +1, outside the proxy multiplier, however
    #: many slices), else ``0``. A cache hit that reuses slices that already
    #: exist costs ``0``.
    screenshot_slicing_credit_cost: int = field(default=cast(int, None))

    def __post_init__(self) -> None:
        _require(self, "engine", "proxy")
        # Older api versions send only the deprecated names; a later one may
        # send only the new names. Each pair always holds the same value.
        self.total_credit_cost, self.credits = _pair(
            self, "total_credit_cost", self.total_credit_cost, self.credits
        )
        self.screenshot_slicing_credit_cost, self.screenshot_slices = _pair(
            self,
            "screenshot_slicing_credit_cost",
            self.screenshot_slicing_credit_cost,
            self.screenshot_slices,
        )


@dataclass
class MapUsage:
    """Per-request billing + routing usage for a map response.

    The cost parts always add up:
    ``total_credit_cost == engine_credit_cost * proxy_multiplier``.

    Older api versions only send ``credits``, ``engine`` and ``proxy``. Then
    ``total_credit_cost`` is filled in from ``credits`` (they always hold the
    same value), and ``engine_credit_cost`` and ``proxy_multiplier`` are ``None``.
    """

    #: **Deprecated:** use :attr:`total_credit_cost`, which always has the same
    #: value. Kept so existing code keeps working; it will be removed in a
    #: future version.
    credits: int = field(default=cast(int, None))
    #: ``http`` for fresh discovery or ``cache`` for a cached result.
    engine: MapBillingEngine = field(default=cast(MapBillingEngine, None))
    #: The proxy tier actually used (the resolved tier -- never ``auto``).
    proxy: ResolvedProxyTier = field(default=cast(ResolvedProxyTier, None))
    #: Credits charged for this map request. ``0`` for a cache hit, and for an
    #: empty map when the site answered only with statuses we don't bill
    #: (a ``5xx``, for example) or not at all.
    total_credit_cost: int = field(default=cast(int, None))
    #: The engine base charged, before the proxy multiplier: ``1`` for
    #: ``http``, ``0`` for ``cache``. Also ``0`` for an empty map that is not
    #: billed. ``None`` on an older api version that
    #: does not send it.
    engine_credit_cost: int | None = None
    #: Multiplier of the proxy tier the request ran on: ``1`` for ``basic``,
    #: ``5`` for ``advanced``. ``None`` on an older api version that does not
    #: send it.
    proxy_multiplier: int | None = None

    def __post_init__(self) -> None:
        _require(self, "engine", "proxy")
        # Older api versions send only the deprecated name; a later one may
        # send only the new name. Both always hold the same value.
        self.total_credit_cost, self.credits = _pair(
            self, "total_credit_cost", self.total_credit_cost, self.credits
        )


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
    "target_unreachable",
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
