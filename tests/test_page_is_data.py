"""A page the site served is data: ``page_status_code``, the usage cost fields,
and the ``target_unreachable`` error.

Every response test runs twice: once with the current api shape and once with
the older shape that has no ``page_status_code`` and only the old usage fields.
Both must parse, on the sync and the async client.
"""

from __future__ import annotations

import httpx
import pytest

from conftest import json_response, make_async, make_sync
from crawlbrulee import (
    CrawlbruleeError,
    MapUsage,
    NotFoundError,
    ScrapeCompleteWebhook,
    ServiceUnavailableError,
    TargetUnreachableError,
    Usage,
)
from crawlbrulee._errors import create_api_error
from crawlbrulee._serde import from_dict

# ----------------------------------------------------------------------
# Payloads
# ----------------------------------------------------------------------

NEW_USAGE = {
    "total_credit_cost": 15,
    "engine_credit_cost": 3,
    "proxy_multiplier": 5,
    "screenshot_slicing_credit_cost": 0,
    "engine": "browser",
    "proxy": "advanced",
    "credits": 15,
    "screenshot_slices": 0,
}

OLD_USAGE = {"credits": 16, "engine": "screenshot", "proxy": "basic", "screenshot_slices": 1}

NEW_MAP_USAGE = {
    "total_credit_cost": 5,
    "engine_credit_cost": 1,
    "proxy_multiplier": 5,
    "engine": "http",
    "proxy": "advanced",
    "credits": 5,
}

OLD_MAP_USAGE = {"credits": 1, "engine": "http", "proxy": "basic"}


def _page_404() -> dict:
    """A 404 page the site really served, as the current api returns it."""
    return {
        "url": "https://example.com/missing",
        "requested_url": "https://example.com/missing",
        "page_status_code": 404,
        "content_type": "text/html",
        "markdown": "# Page not found",
        "metadata": {"title": "Page not found"},
        "response_meta": {"usage": NEW_USAGE},
        "warnings": [],
    }


def _old_page() -> dict:
    """A scrape result from an api that predates ``page_status_code``."""
    return {
        "url": "https://example.com",
        "requested_url": "https://example.com",
        "content_type": "text/html",
        "markdown": "# Hello",
        "response_meta": {"usage": OLD_USAGE},
    }


def _map(usage: dict) -> dict:
    return {
        "links": [{"url": "https://example.com/a"}],
        "response_meta": {
            "usage": usage,
            "pagination": {
                "page": 1,
                "limit": 5000,
                "total": 1,
                "total_pages": 1,
                "has_more": False,
            },
            "truncation": {
                "storage_capped": False,
                "response_capped": False,
                "total_before_max_urls": 1,
                "total_detected_before_storage_cap": 1,
            },
        },
    }


def _router(page: dict, usage: dict, map_usage: dict):
    """Serve ``page`` for scrape + result, a done status, and a map."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in ("/api/scrape", "/api/scrape/result/j1"):
            return json_response(page)
        if path == "/api/scrape/status/j1":
            return json_response(
                {
                    "job_id": "j1",
                    "status": "done",
                    "created_at": "t",
                    "response_meta": {"usage": usage},
                }
            )
        if path == "/api/map":
            return json_response(_map(map_usage))
        raise AssertionError(path)

    return handler


# ----------------------------------------------------------------------
# page_status_code: a 404 page is a result, not an error
# ----------------------------------------------------------------------


def test_sync_scrape_of_a_404_page_returns_the_page() -> None:
    client = make_sync(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE))
    page = client.scrape(url="https://example.com/missing")
    assert page.page_status_code == 404
    assert page.markdown == "# Page not found"
    assert page.metadata is not None
    assert page.metadata.title == "Page not found"


def test_sync_async_result_carries_page_status_code() -> None:
    client = make_sync(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE))
    assert client.get_scrape_result("j1").page_status_code == 404
    assert client.wait_for_scrape("j1", interval=0.001).page_status_code == 404


async def test_async_client_scrape_of_a_404_page_returns_the_page() -> None:
    async with make_async(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE)) as client:
        page = await client.scrape(url="https://example.com/missing")
        result = await client.get_scrape_result("j1")
        waited = await client.wait_for_scrape("j1", interval=0.001)
    assert page.page_status_code == 404
    assert page.markdown == "# Page not found"
    assert result.page_status_code == 404
    assert waited.page_status_code == 404


def test_old_api_scrape_without_page_status_code_still_parses_sync() -> None:
    client = make_sync(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE))
    page = client.scrape(url="https://example.com")
    assert page.page_status_code is None
    assert page.markdown == "# Hello"
    assert client.get_scrape_result("j1").page_status_code is None


async def test_old_api_scrape_without_page_status_code_still_parses_async() -> None:
    async with make_async(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE)) as client:
        page = await client.scrape(url="https://example.com")
        result = await client.get_scrape_result("j1")
    assert page.page_status_code is None
    assert result.page_status_code is None


# ----------------------------------------------------------------------
# Usage: the new cost fields, and the old ones as a fallback
# ----------------------------------------------------------------------


def _assert_new_usage(usage: Usage) -> None:
    assert usage.total_credit_cost == 15
    assert usage.engine_credit_cost == 3
    assert usage.proxy_multiplier == 5
    assert usage.screenshot_slicing_credit_cost == 0
    assert usage.engine == "browser"
    assert usage.proxy == "advanced"
    # The deprecated names still carry the same values.
    assert usage.credits == 15
    assert usage.screenshot_slices == 0


def _assert_old_usage(usage: Usage) -> None:
    # Old api: the two exact matches are filled from the old names ...
    assert usage.total_credit_cost == 16
    assert usage.screenshot_slicing_credit_cost == 1
    # ... and the two parts the old api never sent stay unknown.
    assert usage.engine_credit_cost is None
    assert usage.proxy_multiplier is None
    assert usage.credits == 16
    assert usage.screenshot_slices == 1


def test_sync_usage_reads_the_new_cost_fields() -> None:
    client = make_sync(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE))
    page = client.scrape(url="https://example.com/missing")
    assert page.response_meta is not None
    _assert_new_usage(page.response_meta.usage)
    status = client.get_scrape_status("j1")
    assert status.response_meta is not None
    _assert_new_usage(status.response_meta.usage)


def test_sync_usage_falls_back_to_the_old_fields() -> None:
    client = make_sync(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE))
    page = client.scrape(url="https://example.com")
    assert page.response_meta is not None
    _assert_old_usage(page.response_meta.usage)
    status = client.get_scrape_status("j1")
    assert status.response_meta is not None
    _assert_old_usage(status.response_meta.usage)


async def test_async_usage_reads_new_and_falls_back_to_old() -> None:
    async with make_async(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE)) as client:
        new_page = await client.scrape(url="https://example.com/missing")
        new_status = await client.get_scrape_status("j1")
    async with make_async(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE)) as client:
        old_page = await client.scrape(url="https://example.com")
        old_status = await client.get_scrape_status("j1")
    assert new_page.response_meta is not None
    assert new_status.response_meta is not None
    assert old_page.response_meta is not None
    assert old_status.response_meta is not None
    _assert_new_usage(new_page.response_meta.usage)
    _assert_new_usage(new_status.response_meta.usage)
    _assert_old_usage(old_page.response_meta.usage)
    _assert_old_usage(old_status.response_meta.usage)


def test_unbilled_page_has_every_cost_part_at_zero() -> None:
    usage = from_dict(
        Usage,
        {
            "total_credit_cost": 0,
            "engine_credit_cost": 0,
            "proxy_multiplier": 1,
            "screenshot_slicing_credit_cost": 0,
            "engine": "http",
            "proxy": "basic",
            "credits": 0,
            "screenshot_slices": 0,
        },
    )
    assert usage.total_credit_cost == 0
    assert usage.engine_credit_cost == 0
    # The multiplier is still reported when nothing is billed.
    assert usage.proxy_multiplier == 1


def test_usage_built_by_hand_fills_the_new_totals() -> None:
    usage = Usage(credits=3, engine="browser", proxy="basic", screenshot_slices=0)
    assert usage.total_credit_cost == 3
    assert usage.screenshot_slicing_credit_cost == 0


def test_sync_map_usage_reads_new_and_falls_back_to_old() -> None:
    new = make_sync(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE)).map(url="https://example.com")
    assert new.response_meta.usage.total_credit_cost == 5
    assert new.response_meta.usage.engine_credit_cost == 1
    assert new.response_meta.usage.proxy_multiplier == 5
    assert new.response_meta.usage.credits == 5
    assert not hasattr(new.response_meta.usage, "screenshot_slicing_credit_cost")

    old = make_sync(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE)).map(url="https://example.com")
    assert old.response_meta.usage.total_credit_cost == 1
    assert old.response_meta.usage.engine_credit_cost is None
    assert old.response_meta.usage.proxy_multiplier is None
    assert old.response_meta.usage.credits == 1


async def test_async_map_usage_reads_new_and_falls_back_to_old() -> None:
    async with make_async(_router(_page_404(), NEW_USAGE, NEW_MAP_USAGE)) as client:
        new = await client.map(url="https://example.com")
    async with make_async(_router(_old_page(), OLD_USAGE, OLD_MAP_USAGE)) as client:
        old = await client.map(url="https://example.com")
    assert new.response_meta.usage.total_credit_cost == 5
    assert new.response_meta.usage.proxy_multiplier == 5
    assert old.response_meta.usage.total_credit_cost == 1
    assert old.response_meta.usage.proxy_multiplier is None


def test_map_usage_built_by_hand_fills_the_new_total() -> None:
    assert MapUsage(credits=5, engine="http", proxy="advanced").total_credit_cost == 5


# ----------------------------------------------------------------------
# scrape.complete webhook
# ----------------------------------------------------------------------


def _webhook(data: dict) -> dict:
    return {
        "event_id": "evt_1",
        "timestamp": "2026-09-25T00:00:00Z",
        "event": "scrape.complete",
        "data": {"job_id": "j1", "url": "https://example.com/missing", "completed_at": "t", **data},
    }


def test_webhook_success_carries_page_status_code_and_new_usage() -> None:
    wh = from_dict(
        ScrapeCompleteWebhook,
        _webhook(
            {"status": "success", "page_status_code": 404, "response_meta": {"usage": NEW_USAGE}}
        ),
    )
    assert wh.data.page_status_code == 404
    assert wh.data.response_meta is not None
    _assert_new_usage(wh.data.response_meta.usage)


def test_old_webhook_without_new_fields_still_parses() -> None:
    wh = from_dict(
        ScrapeCompleteWebhook,
        _webhook({"status": "success", "response_meta": {"usage": OLD_USAGE}}),
    )
    assert wh.data.page_status_code is None
    assert wh.data.response_meta is not None
    _assert_old_usage(wh.data.response_meta.usage)


def test_failed_webhook_has_no_page_status_code() -> None:
    wh = from_dict(ScrapeCompleteWebhook, _webhook({"status": "failed", "error": "x"}))
    assert wh.data.page_status_code is None
    assert wh.data.response_meta is None


# ----------------------------------------------------------------------
# target_unreachable (502)
# ----------------------------------------------------------------------

UNREACHABLE = {"name": "target_unreachable", "message": "Could not reach the target site."}


def test_target_unreachable_maps_by_name() -> None:
    err = create_api_error(UNREACHABLE, 502)
    assert isinstance(err, TargetUnreachableError)
    assert isinstance(err, CrawlbruleeError)
    assert not isinstance(err, ServiceUnavailableError)
    assert err.error_name == "target_unreachable"
    assert err.status == 502
    assert err.message == "Could not reach the target site."
    assert err.details is None


def test_unknown_name_on_502_stays_a_plain_error() -> None:
    # Only the name says the target site was unreachable. A 502 with some
    # other name is not guessed at.
    err = create_api_error({"name": "weird", "message": "x"}, 502)
    assert type(err) is CrawlbruleeError


def test_sync_scrape_raises_target_unreachable_once_without_retrying() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return json_response(UNREACHABLE, status=502)

    client = make_sync(handler)
    with pytest.raises(TargetUnreachableError) as excinfo:
        client.scrape(url="https://no-such-site.example")
    assert excinfo.value.status == 502
    assert calls["n"] == 1


def test_sync_map_raises_target_unreachable() -> None:
    client = make_sync(lambda r: json_response(UNREACHABLE, status=502))
    with pytest.raises(TargetUnreachableError):
        client.map(url="https://no-such-site.example")


async def test_async_scrape_raises_target_unreachable() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return json_response(UNREACHABLE, status=502)

    async with make_async(handler) as client:
        with pytest.raises(TargetUnreachableError):
            await client.scrape(url="https://no-such-site.example")
        with pytest.raises(TargetUnreachableError):
            await client.map(url="https://no-such-site.example")
    assert calls["n"] == 2


def test_not_found_is_only_about_our_own_resources() -> None:
    # A 404 from the api is an unknown job id, never the target page.
    err = create_api_error({"name": "not_found", "message": "Job not found"}, 404)
    assert isinstance(err, NotFoundError)


def test_usage_without_the_deprecated_fields_still_parses() -> None:
    # The api will drop `credits` and `screenshot_slices` in a future version;
    # the sdk fills them from the new names so old code keeps working.
    new_only = {k: v for k, v in NEW_USAGE.items() if k not in ("credits", "screenshot_slices")}
    usage = from_dict(Usage, new_only)
    assert usage.credits == 15
    assert usage.screenshot_slices == 0

    map_usage = from_dict(
        MapUsage,
        {
            "total_credit_cost": 5,
            "engine_credit_cost": 1,
            "proxy_multiplier": 5,
            "engine": "http",
            "proxy": "advanced",
        },
    )
    assert map_usage.credits == 5


def test_usage_still_requires_engine_proxy_and_a_cost() -> None:
    with pytest.raises(TypeError):
        from_dict(
            Usage, {"total_credit_cost": 1, "screenshot_slicing_credit_cost": 0, "proxy": "basic"}
        )
    with pytest.raises(TypeError):
        from_dict(Usage, {"engine": "http", "proxy": "basic", "screenshot_slices": 0})
