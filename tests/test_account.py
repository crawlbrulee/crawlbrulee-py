"""Account endpoints: usage + whoami."""

from __future__ import annotations

import httpx

from conftest import json_response, make_sync


def test_usage() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/usage"
        return json_response(
            {
                "total_credits": 1000,
                "used_credits": 250,
                "available_credits": 750,
                "used_quota_percent": 25.0,
                "max_concurrency": 5,
                "usage_reset": "2026-06-01T00:00:00Z",
            }
        )

    client = make_sync(handler)
    usage = client.usage()
    assert usage.total_credits == 1000
    assert usage.available_credits == 750
    assert usage.used_quota_percent == 25.0
    assert usage.usage_reset == "2026-06-01T00:00:00Z"


def test_whoami() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/whoami"
        return json_response(
            {
                "organization_name": "Acme",
                "token_name": "ci-key",
                "token_preview": "cwbl_…xyz",
            }
        )

    client = make_sync(handler)
    who = client.whoami()
    assert who.organization_name == "Acme"
    assert who.token_name == "ci-key"
    assert who.token_preview == "cwbl_…xyz"
