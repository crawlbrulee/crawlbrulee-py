"""Unit tests for to_dict / from_dict."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from crawlbrulee._serde import from_dict, scrape_body, to_dict
from crawlbrulee.types.async_ import AsyncJobStatusResponse
from crawlbrulee.types.common import ScreenshotRequest, ScreenshotWaitAction
from crawlbrulee.types.map import MapResponse, MapTruncation
from crawlbrulee.types.scrape import ScrapeCleanup, ScrapeExtract, ScrapeResponse


@dataclass
class _Aliased:
    """Throwaway dataclass exercising the generic ``__wire_aliases__`` machinery.

    No production type currently maps field names to differently-cased wire keys
    (the whole API is snake_case 1:1), so this local fixture keeps the alias
    branch of ``to_dict`` / ``from_dict`` covered on its own terms.
    """

    snake_field: str
    plain: str
    __wire_aliases__: ClassVar[dict[str, str]] = {"snake_field": "wireField"}


def test_to_dict_omits_none_and_recurses() -> None:
    extract = ScrapeExtract(
        markdown=True,
        screenshot=ScreenshotRequest(
            type="full_page",
            actions_before=[ScreenshotWaitAction(ms=500)],
        ),
    )
    assert to_dict(extract) == {
        "markdown": True,
        "screenshot": {
            "type": "full_page",
            "actions_before": [{"ms": 500, "type": "wait"}],
        },
    }


def test_to_dict_dict_passthrough_drops_none() -> None:
    assert to_dict({"a": 1, "b": None, "c": {"d": None, "e": 2}}) == {"a": 1, "c": {"e": 2}}


def test_from_dict_ignores_unknown_keys() -> None:
    page = from_dict(
        ScrapeResponse,
        {
            "url": "https://x.com",
            "requested_url": "https://x.com",
            "markdown": "m",
            "future_field": "ignored",
        },
    )
    assert page.url == "https://x.com"
    assert page.markdown == "m"
    assert page.cleaned_html is None


def test_from_dict_parses_requested_url() -> None:
    # requested_url is echoed verbatim (before redirects and url cleaning), while
    # url is the cleaned, post-redirect base -- both must survive deserialization.
    page = from_dict(
        ScrapeResponse,
        {
            "url": "https://x.com/final",
            "requested_url": "https://x.com/start?ref=news#top",
        },
    )
    assert page.requested_url == "https://x.com/start?ref=news#top"
    assert page.url == "https://x.com/final"


def test_from_dict_applies_wire_aliases() -> None:
    obj = from_dict(_Aliased, {"wireField": "v9", "plain": "p"})
    assert obj.snake_field == "v9"
    assert obj.plain == "p"


def test_to_dict_applies_wire_aliases() -> None:
    obj = _Aliased(snake_field="v9", plain="p")
    assert to_dict(obj) == {"wireField": "v9", "plain": "p"}


def test_async_status_uses_snake_case_wire_1to1() -> None:
    # The async status endpoint is snake_case on the wire like everything else;
    # no case mapping is applied.
    status = from_dict(
        AsyncJobStatusResponse,
        {"job_id": "j9", "status": "done", "created_at": "2026-01-01T00:00:00Z"},
    )
    assert status.job_id == "j9"
    assert status.created_at == "2026-01-01T00:00:00Z"
    assert status.status == "done"


def test_from_dict_handles_null_for_non_optional_list_field() -> None:
    # MapResponse.links is a required (non-Optional) list; a wire null must not crash.
    result = from_dict(
        MapResponse,
        {
            "links": None,
            "response_meta": {
                "usage": {
                    "credits": 0,
                    "engine": "cache",
                    "proxy": "basic",
                },
                "pagination": {
                    "page": 1,
                    "limit": 10,
                    "total": 0,
                    "total_pages": 0,
                    "has_more": False,
                },
                "truncation": {
                    "storage_capped": False,
                    "response_capped": False,
                    "total_before_max_urls": 0,
                    "total_detected_before_storage_cap": 0,
                },
            },
        },
    )
    assert result.links is None
    assert result.response_meta.pagination.total == 0


def test_from_dict_fills_defaults_for_fields_an_older_server_omits() -> None:
    # MapTruncation's three discovery fields arrived after the first release.
    # from_dict skips wire keys that aren't present, so the dataclass defaults
    # stand in and an older server parses cleanly.
    truncation = from_dict(
        MapTruncation,
        {
            "storage_capped": False,
            "response_capped": True,
            "total_before_max_urls": 12,
            "total_detected_before_storage_cap": 12,
        },
    )
    assert truncation.response_capped is True
    assert truncation.discovery_capped is False
    assert truncation.sitemaps_skipped == 0
    assert truncation.discovery_cap_reason is None


def test_from_dict_passes_literal_union_member_through() -> None:
    # discovery_cap_reason is Literal[...] | None -- the Optional unwraps to a
    # single non-None arm, and a Literal is passed through unconverted.
    truncation = from_dict(
        MapTruncation,
        {
            "storage_capped": False,
            "response_capped": False,
            "total_before_max_urls": 5000,
            "total_detected_before_storage_cap": 5000,
            "discovery_capped": True,
            "sitemaps_skipped": 2,
            "discovery_cap_reason": "file_budget",
        },
    )
    assert truncation.discovery_cap_reason == "file_budget"
    assert truncation.sitemaps_skipped == 2


def test_from_dict_handles_null_for_nested_dataclass_field() -> None:
    # A wire null for a nested dataclass field must map to None, not crash.
    page = from_dict(
        ScrapeResponse,
        {"url": "https://x.com", "requested_url": "https://x.com", "screenshot": None},
    )
    assert page.screenshot is None


def test_scrape_body_sends_cleanup_as_a_nested_block() -> None:
    """`cleanup` is a top-level object, not the flat `exclude_selectors` it replaced.

    The server schema is strict: a stray top-level `exclude_selectors`, or a
    `cleanup` block nested under `screenshot`, is a 400. Pinned because the
    failure is a runtime rejection the type checker cannot see.
    """
    body = scrape_body(
        "https://example.com",
        None,
        None,
        None,
        ScrapeCleanup(ads_and_popups=False, exclude_selectors=["#promo"]),
        None,
        None,
    )

    assert body["cleanup"] == {"ads_and_popups": False, "exclude_selectors": ["#promo"]}
    assert "exclude_selectors" not in body


def test_scrape_body_accepts_a_plain_dict_cleanup() -> None:
    body = scrape_body(
        "https://example.com", None, None, None, {"ads_and_popups": True}, None, None
    )

    assert body["cleanup"] == {"ads_and_popups": True}


def test_scrape_body_omits_cleanup_when_not_given() -> None:
    """Omitted means "use the server default" (ads_and_popups: true) — an empty
    object would be a different request that pins the default client-side."""
    body = scrape_body("https://example.com", None, None, None, None, None, None)

    assert "cleanup" not in body
