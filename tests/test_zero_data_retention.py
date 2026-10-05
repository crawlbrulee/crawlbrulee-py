"""Zero data retention: the request field, the usage field, and the 403 error."""

from __future__ import annotations

import contextlib

import httpx
import pytest

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import (
    AntibotBlockedError,
    AuthenticationError,
    CrawlbruleeError,
    MapUsage,
    Usage,
    ZeroDataRetentionNotEnabledError,
)
from crawlbrulee._errors import create_api_error
from crawlbrulee._serde import from_dict

NOT_ENABLED = {
    "name": "zero_data_retention_not_enabled",
    "message": (
        "zero_data_retention is not enabled for your organization. Contact us to turn it on."
    ),
}


def _capture(seen: list[dict], payload: object = None):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request_json(request))
        return json_response(payload if payload is not None else {"job_id": "j1"})

    return handler


def _send_all_sync(client) -> None:
    for call in (
        lambda: client.scrape(url="https://example.com", zero_data_retention=True),
        lambda: client.scrape_async(url="https://example.com", zero_data_retention=True),
        lambda: client.map(url="https://example.com", zero_data_retention=True),
    ):
        with contextlib.suppress(Exception):  # stub reply is no full result; only the body counts
            call()


def test_sync_sends_flag_top_level() -> None:
    seen: list[dict] = []
    _send_all_sync(make_sync(_capture(seen)))
    assert len(seen) == 3
    for body in seen:
        assert body["zero_data_retention"] is True
        assert "zero_data_retention" not in body.get("cache", {})


async def test_async_sends_flag_top_level() -> None:
    seen: list[dict] = []
    async with make_async(_capture(seen)) as client:
        for call in (
            lambda: client.scrape(url="https://example.com", zero_data_retention=True),
            lambda: client.scrape_async(url="https://example.com", zero_data_retention=True),
            lambda: client.map(url="https://example.com", zero_data_retention=True),
        ):
            with contextlib.suppress(Exception):
                await call()
    assert len(seen) == 3
    assert all(b["zero_data_retention"] is True for b in seen)


def test_flag_omitted_when_not_given_and_false_is_sent() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen))
    with contextlib.suppress(Exception):
        client.scrape(url="https://example.com")
    with contextlib.suppress(Exception):
        client.scrape(url="https://example.com", zero_data_retention=False)
    assert "zero_data_retention" not in seen[0]
    assert seen[1]["zero_data_retention"] is False


def test_usage_field_parses_and_is_none_when_absent() -> None:
    usage = from_dict(
        Usage,
        {
            "total_credit_cost": 6,
            "engine_credit_cost": 1,
            "proxy_multiplier": 5,
            "screenshot_slicing_credit_cost": 0,
            "zero_data_retention_credit_cost": 1,
            "engine": "http",
            "proxy": "advanced",
        },
    )
    assert usage.zero_data_retention_credit_cost == 1
    assert usage.total_credit_cost == 6
    older = from_dict(
        Usage,
        {
            "total_credit_cost": 1,
            "engine": "http",
            "proxy": "basic",
            "screenshot_slicing_credit_cost": 0,
        },
    )
    assert older.zero_data_retention_credit_cost is None


def test_map_usage_field_parses_and_is_none_when_absent() -> None:
    usage = from_dict(
        MapUsage,
        {
            "total_credit_cost": 6,
            "engine_credit_cost": 1,
            "proxy_multiplier": 5,
            "zero_data_retention_credit_cost": 1,
            "engine": "http",
            "proxy": "advanced",
        },
    )
    assert usage.zero_data_retention_credit_cost == 1
    assert (
        from_dict(
            MapUsage, {"total_credit_cost": 1, "engine": "http", "proxy": "basic"}
        ).zero_data_retention_credit_cost
        is None
    )


def test_error_maps_by_name_on_403() -> None:
    err = create_api_error(NOT_ENABLED, 403)
    assert isinstance(err, ZeroDataRetentionNotEnabledError)
    assert isinstance(err, CrawlbruleeError)
    assert not isinstance(err, AuthenticationError)
    assert err.error_name == "zero_data_retention_not_enabled"
    assert err.status == 403
    assert err.message == NOT_ENABLED["message"]


def test_other_403s_keep_their_classes() -> None:
    assert isinstance(
        create_api_error({"name": "antibot_blocked", "message": "x"}, 403), AntibotBlockedError
    )
    assert isinstance(
        create_api_error({"name": "access_denied", "message": "x"}, 403), AuthenticationError
    )
    assert isinstance(create_api_error({"name": "weird", "message": "x"}, 403), AuthenticationError)


def test_sync_calls_raise_once_without_retrying() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return json_response(NOT_ENABLED, status=403)

    client = make_sync(handler)
    with pytest.raises(ZeroDataRetentionNotEnabledError):
        client.scrape(url="https://example.com", zero_data_retention=True)
    with pytest.raises(ZeroDataRetentionNotEnabledError):
        client.scrape_async(url="https://example.com", zero_data_retention=True)
    with pytest.raises(ZeroDataRetentionNotEnabledError):
        client.map(url="https://example.com", zero_data_retention=True)
    assert calls["n"] == 3


async def test_async_calls_raise() -> None:
    async with make_async(lambda r: json_response(NOT_ENABLED, status=403)) as client:
        with pytest.raises(ZeroDataRetentionNotEnabledError):
            await client.scrape(url="https://example.com", zero_data_retention=True)
        with pytest.raises(ZeroDataRetentionNotEnabledError):
            await client.map(url="https://example.com", zero_data_retention=True)
