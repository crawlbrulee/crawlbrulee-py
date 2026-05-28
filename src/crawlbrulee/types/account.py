"""Response shapes for the account endpoints (``/api/usage``, ``/api/whoami``)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class UsageResponse:
    """Response from ``GET /api/usage``. Current billing-cycle snapshot."""

    #: Total credits available for the current billing cycle
    #: (plan base + purchased + gifted).
    total_credits: int
    #: Credits spent so far in the current billing cycle. May exceed
    #: ``total_credits`` on plans that allow overages.
    used_credits: int
    #: Remaining credits, ``max(0, total_credits - used_credits)``.
    available_credits: int
    #: Percentage of ``total_credits`` used this cycle, rounded to one decimal.
    #: Not capped -- values above 100 indicate overage.
    used_quota_percent: float
    #: Maximum number of concurrent jobs allowed for the org.
    max_concurrency: int
    #: ISO-8601 UTC timestamp when the cycle ends and ``used_credits`` resets.
    usage_reset: str


@dataclass
class WhoamiResponse:
    """Response from ``GET /api/whoami``. Identifies the calling API token."""

    #: Display name of the organization that owns the token.
    organization_name: str
    #: User-assigned name of the API token.
    token_name: str
    #: Truncated preview of the API token (e.g. ``cble_...xyz``). Safe to display.
    token_preview: str
