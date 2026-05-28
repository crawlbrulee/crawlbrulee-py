"""Unit tests for to_dict / from_dict."""

from __future__ import annotations

from crawlbrulee._serde import from_dict, to_dict
from crawlbrulee.types.async_ import AsyncJobStatusResponse
from crawlbrulee.types.common import ScreenshotRequest, ScreenshotWaitAction
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
