"""The map's sitemap fields: ``sitemap_url``, ``depth``, ``entries``, ``modified_since`` and
``max_results`` on the request, ``type`` and ``lastmod`` on each link, and
``total_before_max_results`` and ``unread_sitemaps`` on the truncation block."""

from __future__ import annotations

from typing import get_args

import httpx

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import DiscoveryCapReason, MapEntries, MapLinkType, MapTruncation
from crawlbrulee._serde import from_dict


def _payload(links: list[dict], truncation: dict | None = None) -> dict:
    """A map response body with ``truncation`` merged over sane defaults."""
    return {
        "links": links,
        "response_meta": {
            "usage": {"total_credit_cost": 1, "engine": "http", "proxy": "basic"},
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
                "total_before_max_results": len(links),
                "total_before_max_urls": len(links),
                "total_detected_before_storage_cap": len(links),
                "discovery_capped": False,
                "sitemaps_skipped": 0,
                "unread_sitemaps": [],
                "discovery_cap_reason": None,
                **(truncation or {}),
            },
        },
    }


def _capture(seen: list[dict]):
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append({"path": request.url.path, "body": request_json(request)})
        return json_response(
            _payload([{"url": "https://example.com/", "type": "page", "lastmod": None}])
        )

    return handler


def test_new_request_fields_are_sent_at_the_top_level() -> None:
    seen: list[dict] = []
    make_sync(_capture(seen)).map(
        url="https://example.com",
        sitemap_url="https://cdn.example.com/sitemaps/products-1.xml.gz",
        depth=1,
        entries="all",
        modified_since="2026-11-01T00:00:00Z",
        max_results=2000,
    )

    assert seen[0]["path"] == "/api/map"
    assert seen[0]["body"] == {
        "url": "https://example.com",
        "sitemap_url": "https://cdn.example.com/sitemaps/products-1.xml.gz",
        "depth": 1,
        "entries": "all",
        "modified_since": "2026-11-01T00:00:00Z",
        "max_results": 2000,
    }


async def test_async_client_sends_the_same_fields() -> None:
    seen: list[dict] = []
    async with make_async(_capture(seen)) as client:
        await client.map(url="https://example.com", depth=0, entries="sitemaps")

    assert seen[0]["body"] == {"url": "https://example.com", "depth": 0, "entries": "sitemaps"}


def test_depth_is_passed_through_without_a_maximum() -> None:
    # The api owns the maximum, so raising it needs no SDK release.
    seen: list[dict] = []
    make_sync(_capture(seen)).map(url="https://example.com", depth=9)

    assert seen[0]["body"] == {"url": "https://example.com", "depth": 9}


def test_deprecated_max_urls_is_still_sent() -> None:
    seen: list[dict] = []
    make_sync(_capture(seen)).map(url="https://example.com", max_urls=300)

    assert seen[0]["body"] == {"url": "https://example.com", "max_urls": 300}


def test_type_lastmod_and_unread_sitemaps_are_parsed() -> None:
    client = make_sync(
        lambda _r: json_response(
            _payload(
                [
                    {
                        "url": "https://example.com/sitemap-products.xml",
                        "type": "sitemap",
                        "lastmod": None,
                    },
                    {
                        "url": "https://example.com/products/blue-mug",
                        "type": "page",
                        "lastmod": "2026-11-10T08:30:00.000Z",
                    },
                ],
                {
                    "discovery_capped": True,
                    "sitemaps_skipped": 1,
                    "unread_sitemaps": ["https://example.com/sitemap-blog.xml"],
                    "discovery_cap_reason": "depth",
                },
            )
        )
    )
    result = client.map(url="https://example.com", depth=0, entries="all")

    first, second = result.links
    assert first.url == "https://example.com/sitemap-products.xml"
    assert first.type == "sitemap"
    assert first.lastmod is None
    assert second.type == "page"
    assert second.lastmod == "2026-11-10T08:30:00.000Z"
    truncation = result.response_meta.truncation
    assert truncation.total_before_max_results == 2
    assert truncation.discovery_cap_reason == "depth"
    assert truncation.unread_sitemaps == ["https://example.com/sitemap-blog.xml"]


def test_total_before_max_results_alone_fills_the_deprecated_total() -> None:
    # After the api removes total_before_max_urls, the old attribute still reads right.
    truncation = from_dict(
        MapTruncation,
        {"storage_capped": False, "response_capped": False, "total_before_max_results": 7},
    )

    assert truncation.total_before_max_results == 7
    assert truncation.total_before_max_urls == 7


def test_option_values() -> None:
    assert set(get_args(MapEntries)) == {"pages", "sitemaps", "all"}
    assert set(get_args(MapLinkType)) == {"page", "sitemap"}
    assert set(get_args(DiscoveryCapReason)) == {
        "max_results",
        "time",
        "file_budget",
        "depth",
        "file_size",
        "unread_files",
    }
