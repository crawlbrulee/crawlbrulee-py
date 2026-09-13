"""Error mapping: create_api_error dispatch + end-to-end HTTP error surfacing."""

from __future__ import annotations

import httpx
import pytest

from conftest import json_response, make_sync
from crawlbrulee import (
    AntibotBlockedError,
    AuthenticationError,
    CrawlbruleeError,
    NotFoundError,
    PageTooLargeError,
    RateLimitError,
    ServiceUnavailableError,
    TooManyRedirectsError,
    UsageAllocationError,
    ValidationError,
)
from crawlbrulee._errors import create_api_error


def test_rate_limit_with_details() -> None:
    err = create_api_error(
        {
            "name": "too_many_requests",
            "message": "slow down",
            "details": {
                "error_name": "too_many_requests",
                "retry_after_ms": 1500,
                "limited_by": "org",
            },
        },
        429,
    )
    assert isinstance(err, RateLimitError)
    assert err.error_name == "too_many_requests"
    assert err.retry_after_ms == 1500
    assert err.limited_by == "org"


def test_usage_allocation_with_reason() -> None:
    err = create_api_error(
        {
            "name": "usage_allocation_error",
            "message": "no credits",
            "details": {
                "error_name": "usage_allocation_error",
                "reason": "credit_limit",
                "details": {"current_usage": 100, "max_credits": 100},
            },
        },
        402,
    )
    assert isinstance(err, UsageAllocationError)
    assert err.reason == "credit_limit"
    assert err.usage == {"current_usage": 100, "max_credits": 100}


def test_usage_allocation_without_details_synthesizes_reason() -> None:
    err = create_api_error({"name": "usage_allocation_error", "message": "nope"}, 402)
    assert isinstance(err, UsageAllocationError)
    assert err.reason == "internal_error"


def test_auth_errors() -> None:
    for name in ("invalid_credentials", "access_denied"):
        err = create_api_error({"name": name, "message": "no"}, 401)
        assert isinstance(err, AuthenticationError)
        assert err.error_name == name


def test_not_found() -> None:
    err = create_api_error({"name": "not_found", "message": "gone"}, 404)
    assert isinstance(err, NotFoundError)


def test_validation_errors() -> None:
    for name in ("validation_error", "invalid_url", "blocked_url", "url_too_long"):
        err = create_api_error({"name": name, "message": "bad"}, 400)
        assert isinstance(err, ValidationError)
        assert err.error_name == name


def test_unsupported_screenshot_output_maps_to_validation_error() -> None:
    # 422: a screenshot was the only requested output, but the content type
    # can't be screenshotted. Same class as unsupported_content.
    err = create_api_error(
        {"name": "unsupported_screenshot_output", "message": "screenshots need an HTML page"},
        422,
    )
    assert isinstance(err, ValidationError)
    assert err.error_name == "unsupported_screenshot_output"
    assert err.status == 422


def test_service_unavailable_maps_by_name() -> None:
    # 503: infra failure during the token lookup. Must NOT read as an auth error.
    err = create_api_error(
        {"name": "service_unavailable", "message": "temporarily unavailable"},
        503,
    )
    assert isinstance(err, ServiceUnavailableError)
    assert not isinstance(err, AuthenticationError)
    assert err.error_name == "service_unavailable"
    assert err.status == 503


def test_service_unavailable_status_fallback_for_unknown_name() -> None:
    err = create_api_error({"name": "weird", "message": "x"}, 503)
    assert isinstance(err, ServiceUnavailableError)


def test_name_first_beats_status_heuristics() -> None:
    # A 403 carrying name=not_found must map by name, not by status.
    err = create_api_error({"name": "not_found", "message": "x"}, 403)
    assert isinstance(err, NotFoundError)


def test_status_fallback_for_unknown_name() -> None:
    assert isinstance(create_api_error({"name": "weird", "message": "x"}, 429), RateLimitError)
    assert isinstance(create_api_error({"name": "weird", "message": "x"}, 401), AuthenticationError)
    assert isinstance(create_api_error({"name": "weird", "message": "x"}, 404), NotFoundError)


def test_generic_fallback() -> None:
    err = create_api_error({"name": "internal_server_error", "message": "oops"}, 500)
    assert type(err) is CrawlbruleeError
    assert err.status == 500
    assert err.error_name == "internal_server_error"


def test_http_error_surfaces_as_typed_exception() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "name": "too_many_requests",
                "message": "slow down",
                "details": {"error_name": "too_many_requests", "retry_after_ms": 2000},
            },
            status=429,
        )

    client = make_sync(handler)
    with pytest.raises(RateLimitError) as excinfo:
        client.scrape(url="https://example.com")
    assert excinfo.value.retry_after_ms == 2000
    assert excinfo.value.status == 429


def test_antibot_blocked_maps_by_name() -> None:
    # 403: the target site's bot protection blocked us. Must NOT read as a
    # credentials problem -- the key is fine, the site said no.
    err = create_api_error(
        {"name": "antibot_blocked", "message": "blocked by the target site"},
        403,
    )
    assert isinstance(err, AntibotBlockedError)
    assert not isinstance(err, AuthenticationError)
    assert err.error_name == "antibot_blocked"
    assert err.status == 403


def test_too_many_redirects_maps_by_name() -> None:
    # 422: the target redirected the request in a loop. Target-side like
    # antibot_blocked -- the request was fine, so it must NOT read as a bad
    # request.
    err = create_api_error(
        {"name": "too_many_redirects", "message": "redirect loop"},
        422,
    )
    assert isinstance(err, TooManyRedirectsError)
    assert not isinstance(err, ValidationError)
    assert err.error_name == "too_many_redirects"
    assert err.status == 422


def test_page_too_large_maps_by_name() -> None:
    # 422: the page's HTML was too large to process. About the page, not the
    # request -- so it must NOT read as a bad request, and it must not be
    # confused with the other 422, too_many_redirects.
    err = create_api_error(
        {"name": "page_too_large", "message": "The page is too large or too complex to convert."},
        422,
    )
    assert isinstance(err, PageTooLargeError)
    assert not isinstance(err, ValidationError)
    assert not isinstance(err, TooManyRedirectsError)
    assert err.error_name == "page_too_large"
    assert err.status == 422


def test_unknown_name_on_403_still_maps_to_authentication_error() -> None:
    # The status fallback is unchanged: only a recognized antibot_blocked name
    # escapes the 401/403 -> AuthenticationError heuristic.
    err = create_api_error({"name": "weird", "message": "x"}, 403)
    assert isinstance(err, AuthenticationError)
    assert not isinstance(err, AntibotBlockedError)
