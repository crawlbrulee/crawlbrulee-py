"""Unit tests for to_dict / from_dict."""

from __future__ import annotations

from crawlbrulee._serde import from_dict, to_dict
from crawlbrulee.types.async_ import AsyncJobStatusResponse
from crawlbrulee.types.common import ScreenshotRequest, ScreenshotWaitAction
from crawlbrulee.types.map import MapResponse
from crawlbrulee.types.scrape import ScrapeExtract, ScrapeResponse


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
        {"url": "https://x.com", "markdown": "m", "future_field": "ignored"},
    )
    assert page.url == "https://x.com"
    assert page.markdown == "m"
    assert page.cleaned_html is None


def test_from_dict_applies_wire_aliases() -> None:
    status = from_dict(
        AsyncJobStatusResponse,
        {"jobId": "j9", "status": "done", "createdAt": "2026-01-01T00:00:00Z"},
    )
    assert status.job_id == "j9"
    assert status.created_at == "2026-01-01T00:00:00Z"
    assert status.status == "done"


def test_to_dict_applies_wire_aliases() -> None:
    status = AsyncJobStatusResponse(job_id="j9", status="done", created_at="t")
    assert to_dict(status) == {"jobId": "j9", "status": "done", "createdAt": "t"}


def test_from_dict_handles_null_for_non_optional_list_field() -> None:
    # MapResponse.links is a required (non-Optional) list; a wire null must not crash.
    result = from_dict(
        MapResponse,
        {
            "links": None,
            "response_meta": {
                "usage": {"credits": 0, "proxy": "none", "cache_hit": True},
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


def test_from_dict_handles_null_for_nested_dataclass_field() -> None:
    # A wire null for a nested dataclass field must map to None, not crash.
    page = from_dict(ScrapeResponse, {"url": "https://x.com", "screenshot": None})
    assert page.screenshot is None
