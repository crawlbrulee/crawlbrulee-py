"""Mapping endpoint: request body + nested response_meta parsing."""

from __future__ import annotations

import httpx

from conftest import json_response, make_sync, request_json
from crawlbrulee import MapTypes


def test_map_posts_body_and_parses_meta() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request_json(request)
        return json_response(
            {
                "links": [{"url": "https://example.com/a"}, {"url": "https://example.com/b"}],
                "response_meta": {
                    "usage": {
                        "credits": 1,
                        "engine": "text",
                        "proxy": "basic",
                    },
                    "pagination": {
                        "page": 1,
                        "limit": 1000,
                        "total": 2,
                        "total_pages": 1,
                        "has_more": False,
                    },
                    "truncation": {
                        "storage_capped": False,
                        "response_capped": False,
                        "total_before_max_urls": 2,
                        "total_detected_before_storage_cap": 2,
                        "discovery_capped": False,
                        "sitemaps_skipped": 0,
                        "discovery_cap_reason": None,
                    },
                },
            }
        )

    client = make_sync(handler)
    result = client.map(
        url="https://example.com",
        sitemap_only=False,
        types=MapTypes(internal=True, external=False),
        max_urls=5000,
        page=1,
    )

    assert captured["path"] == "/api/map"
    assert captured["body"] == {
        "url": "https://example.com",
        "sitemap_only": False,
        "types": {"internal": True, "external": False},
        "max_urls": 5000,
        "page": 1,
    }
    assert len(result.links) == 2
    assert result.links[0].url == "https://example.com/a"
    assert result.response_meta.usage.credits == 1
    assert result.response_meta.usage.engine == "text"
    assert result.response_meta.usage.proxy == "basic"
    assert not hasattr(result.response_meta.usage, "screenshot_slices")
    assert result.response_meta.pagination.total == 2
    assert result.response_meta.pagination.has_more is False
    truncation = result.response_meta.truncation
    assert truncation.storage_capped is False
    assert truncation.discovery_capped is False
    assert truncation.sitemaps_skipped == 0
    assert truncation.discovery_cap_reason is None


def _map_payload(links: list[str], truncation: dict) -> dict:
    """A map response body with ``truncation`` merged over sane defaults."""
    return {
        "links": [{"url": u} for u in links],
        "response_meta": {
            "usage": {"credits": 1, "engine": "text", "proxy": "basic"},
            "pagination": {
                "page": 1,
                "limit": 5000,
                "total": len(links),
                "total_pages": 1,
                "has_more": False,
            },
            "truncation": {
                "storage_capped": False,
                "response_capped": False,
                "total_before_max_urls": len(links),
                "total_detected_before_storage_cap": len(links),
                **truncation,
            },
        },
    }


def test_map_sends_no_defaults_of_its_own() -> None:
    # max_urls and limit are the server's call (5000 each). The SDK must send
    # only what the caller passed, so a server-side default change needs no
    # SDK release.
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response(_map_payload(["https://example.com/a"], {}))

    make_sync(handler).map(url="https://example.com")

    assert captured["body"] == {"url": "https://example.com"}


def test_map_reports_discovery_stopped_at_max_urls() -> None:
    # Discovery stops at the caller's max_urls, so the list is exactly that long
    # while response_capped stays False -- discovery_cap_reason is the only
    # signal that the site has more pages.
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            _map_payload(
                [f"https://example.com/{i}" for i in range(3)],
                {
                    "response_capped": False,
                    "discovery_capped": True,
                    "sitemaps_skipped": 4,
                    "discovery_cap_reason": "max_urls",
                },
            )
        )

    result = make_sync(handler).map(url="https://example.com", max_urls=3)

    truncation = result.response_meta.truncation
    assert len(result.links) == 3
    assert truncation.response_capped is False
    assert truncation.discovery_capped is True
    assert truncation.sitemaps_skipped == 4
    assert truncation.discovery_cap_reason == "max_urls"


def test_map_truncation_defaults_when_server_omits_new_fields() -> None:
    # An older server predates discovery_capped / sitemaps_skipped /
    # discovery_cap_reason. Their absence must read as "nothing was cut short",
    # not raise.
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "links": [{"url": "https://example.com/a"}],
                "response_meta": {
                    "usage": {"credits": 1, "engine": "text", "proxy": "basic"},
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
        )

    truncation = make_sync(handler).map(url="https://example.com").response_meta.truncation

    assert truncation.discovery_capped is False
    assert truncation.sitemaps_skipped == 0
    assert truncation.discovery_cap_reason is None


def test_map_link_item_carries_only_url() -> None:
    # An unknown key must be ignored rather than break parsing.
    def handler(request: httpx.Request) -> httpx.Response:
        payload = _map_payload(["https://example.com/a"], {})
        payload["links"][0]["source"] = "sitemap"  # type: ignore[index]
        return json_response(payload)

    link = make_sync(handler).map(url="https://example.com").links[0]

    assert link.url == "https://example.com/a"
    assert not hasattr(link, "source")
