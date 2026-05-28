"""Mapping endpoint: request body + nested meta parsing."""

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
                "meta": {
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
    assert result.meta.pagination.total == 2
    assert result.meta.pagination.has_more is False
    assert result.meta.truncation.storage_capped is False
