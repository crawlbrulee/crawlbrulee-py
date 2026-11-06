"""headers and cookies: the request fields, the 400 for a refused header, and the
``custom_user_agent`` warning."""

from __future__ import annotations

import contextlib
from types import MappingProxyType
from typing import get_args

import httpx
import pytest

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import (
    ScrapeCookie,
    ScrapeCookies,
    ScrapeResponse,
    ScrapeWarningCode,
    ValidationError,
)
from crawlbrulee._serde import async_scrape_body, from_dict, scrape_body

HEADERS = {"Authorization": "Bearer t0ken", "X-Tenant-Id": "acme"}
COOKIES_WIRE = [{"name": "session_id", "value": "a1b2c3"}, {"name": "theme", "value": "dark"}]

PAGE = {"url": "https://app.example.com/orders", "requested_url": "https://app.example.com/orders"}


def _capture(seen: list[dict], payload: object = None):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path, "body": request_json(request)})
        return json_response(payload if payload is not None else {"job_id": "j1"})

    return handler


def test_sync_client_sends_headers_and_cookies_on_both_scrape_calls() -> None:
    seen: list[dict] = []
    client = make_sync(_capture(seen))
    cookies = [ScrapeCookie(name="session_id", value="a1b2c3"), {"name": "theme", "value": "dark"}]
    with contextlib.suppress(Exception):  # stub reply is no full result; only the body counts
        client.scrape(url=PAGE["url"], headers=HEADERS, cookies=cookies)
    client.scrape_async(url=PAGE["url"], headers=HEADERS, cookies=cookies)

    assert [s["path"] for s in seen] == ["/api/scrape", "/api/scrape/async"]
    for s in seen:
        assert s["body"]["headers"] == HEADERS
        assert s["body"]["cookies"] == COOKIES_WIRE


async def test_async_client_sends_headers_and_cookies_on_both_scrape_calls() -> None:
    seen: list[dict] = []
    async with make_async(_capture(seen)) as client:
        with contextlib.suppress(Exception):
            await client.scrape(
                url=PAGE["url"],
                headers=HEADERS,
                cookies=[{"name": "session_id", "value": "a1b2c3"}],
            )
        await client.scrape_async(
            url=PAGE["url"],
            headers=HEADERS,
            cookies=[ScrapeCookie(name="session_id", value="a1b2c3")],
        )

    assert [s["path"] for s in seen] == ["/api/scrape", "/api/scrape/async"]
    for s in seen:
        assert s["body"]["headers"] == HEADERS
        assert s["body"]["cookies"] == [{"name": "session_id", "value": "a1b2c3"}]


def test_fields_left_out_when_not_given() -> None:
    body = scrape_body("https://example.com", None, None, None, None, None, None)
    assert "headers" not in body
    assert "cookies" not in body


def test_any_mapping_and_a_tuple_work() -> None:
    cookies: ScrapeCookies = (ScrapeCookie(name="a", value="1"),)
    body = scrape_body(
        "https://example.com",
        None,
        None,
        None,
        None,
        None,
        None,
        headers=MappingProxyType({"X-Api-Key": "k"}),
        cookies=cookies,
    )
    assert body["headers"] == {"X-Api-Key": "k"}
    assert type(body["headers"]) is dict
    assert body["cookies"] == [{"name": "a", "value": "1"}]


def test_empty_values_are_sent_as_is() -> None:
    body = scrape_body(
        "https://example.com", None, None, None, None, None, None, headers={}, cookies=[]
    )
    assert body["headers"] == {}
    assert body["cookies"] == []


def test_fields_sit_top_level_next_to_the_webhook() -> None:
    body = async_scrape_body(
        "https://example.com",
        None,
        None,
        None,
        None,
        None,
        None,
        {"url": "https://hooks.example.com"},
        headers={"X-Api-Key": "k"},
        cookies=[{"name": "s", "value": "v"}],
    )
    assert body == {
        "url": "https://example.com",
        "webhook": {"url": "https://hooks.example.com"},
        "headers": {"X-Api-Key": "k"},
        "cookies": [{"name": "s", "value": "v"}],
    }


def test_map_takes_no_headers_or_cookies() -> None:
    client = make_sync(lambda _r: json_response({}))
    with pytest.raises(TypeError):
        client.map(url="https://example.com", headers=HEADERS)  # type: ignore[call-arg]


def test_refused_header_raises_validation_error() -> None:
    message = (
        'Request validation failed: headers: "Cookie" can\'t be set as a header. '
        "Send cookies in the cookies field."
    )

    def handler(_request: httpx.Request) -> httpx.Response:
        return json_response({"name": "validation_error", "message": message}, status=400)

    with pytest.raises(ValidationError) as caught:
        make_sync(handler).scrape(url=PAGE["url"], headers={"Cookie": "a=b"})
    assert caught.value.status == 400
    assert "Cookie" in str(caught.value)


def test_custom_user_agent_warning_comes_through() -> None:
    seen: list[dict] = []
    payload = {**PAGE, "warnings": ["custom_user_agent"]}
    page = make_sync(_capture(seen, payload)).scrape(
        url=PAGE["url"], headers={"User-Agent": "my-bot/1.0"}
    )

    assert seen[0]["body"]["headers"] == {"User-Agent": "my-bot/1.0"}
    assert page.warnings == ["custom_user_agent"]
    assert "custom_user_agent" in get_args(ScrapeWarningCode)


def test_unknown_warning_code_still_parses() -> None:
    page = from_dict(ScrapeResponse, {**PAGE, "warnings": ["custom_user_agent", "new_code"]})
    assert page.warnings == ["custom_user_agent", "new_code"]


def test_cookie_value_stays_out_of_repr() -> None:
    # A cookie value is often a session secret; printing the object (a log
    # line, a pytest diff, an error tracker) must not show it.
    cookie = ScrapeCookie(name="session_id", value="s3cr3t-token-value")
    assert "s3cr3t-token-value" not in repr(cookie)
    assert "session_id" in repr(cookie)
    assert cookie.value == "s3cr3t-token-value"
