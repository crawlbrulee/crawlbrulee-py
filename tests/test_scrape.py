"""Synchronous scrape: request body serialization + nested response parsing."""

from __future__ import annotations

import httpx

from conftest import json_response, make_sync, request_json
from crawlbrulee import ScrapeExtract, ScreenshotRequest


def test_scrape_posts_to_endpoint_and_parses_response() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = request_json(request)
        return json_response(
            {
                "url": "https://example.com",
                "content_type": "text/html",
                "markdown": "# Hello",
                "links": [
                    {"text": "Home", "href": "/", "internal": True},
                    {"text": "Out", "href": "https://other.com", "internal": False},
                ],
                "metadata": {"title": "Example", "keywords": ["a", "b"]},
                "response_meta": {
                    "usage": {"credits": 1, "proxy": "basic", "cache_hit": False},
                },
                "warnings": ["screenshot_truncated"],
            }
        )

    client = make_sync(handler)
    page = client.scrape(
        url="https://example.com", extract=ScrapeExtract(markdown=True, links=True)
    )

    assert captured["method"] == "POST"
    assert captured["path"] == "/api/scrape"
    assert page.url == "https://example.com"
    assert page.markdown == "# Hello"
    assert page.links is not None
    assert page.links[0].text == "Home"
    assert page.links[1].internal is False
    assert page.metadata is not None
    assert page.metadata.title == "Example"
    assert page.metadata.keywords == ["a", "b"]
    assert page.response_meta is not None
    assert page.response_meta.usage.credits == 1
    assert page.response_meta.usage.proxy == "basic"
    assert page.response_meta.usage.cache_hit is False
    assert page.warnings == ["screenshot_truncated"]


def test_scrape_parses_meta_usage_on_cache_hit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "url": "https://example.com",
                "markdown": "# cached",
                "response_meta": {
                    "usage": {"credits": 0, "proxy": "advanced", "cache_hit": True},
                },
            }
        )

    client = make_sync(handler)
    page = client.scrape(url="https://example.com")
    assert page.response_meta is not None
    assert page.response_meta.usage.credits == 0
    assert page.response_meta.usage.proxy == "advanced"
    assert page.response_meta.usage.cache_hit is True


def test_scrape_body_omits_none_and_nests_dataclasses() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response({"url": "https://example.com"})

    client = make_sync(handler)
    client.scrape(
        url="https://example.com",
        extract=ScrapeExtract(
            markdown=True,
            screenshot=ScreenshotRequest(type="full_page"),
        ),
        require_js=True,
        proxy="advanced",
    )

    body = captured["body"]
    assert body == {
        "url": "https://example.com",
        "extract": {"markdown": True, "screenshot": {"type": "full_page"}},
        "require_js": True,
        "proxy": "advanced",
    }
    # None-valued optionals are omitted entirely.
    assert "cache" not in body
    assert "links" not in body["extract"]


def test_scrape_accepts_plain_dict_request_parts() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response({"url": "https://example.com"})

    client = make_sync(handler)
    client.scrape(url="https://example.com", extract={"markdown": True, "metadata": None})

    # dict passthrough still drops explicit None values.
    assert captured["body"]["extract"] == {"markdown": True}


def test_scrape_parses_screenshot_with_slices() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "url": "https://example.com",
                "screenshot": {
                    "url": "https://cdn/full.png",
                    "type": "full_page",
                    "properties": {
                        "file_name": "full.png",
                        "mime": "image/png",
                        "width": 1280,
                        "height": 4000,
                        "viewport": {"width": 1280, "height": 720, "device_scale_factor": 2},
                    },
                    "slices": [
                        {
                            "row_nr": 0,
                            "url": "https://cdn/0.png",
                            "type": "slice",
                            "properties": {
                                "file_name": "0.png",
                                "mime": "image/png",
                                "width": 1280,
                                "height": 500,
                                "viewport": {
                                    "width": 1280,
                                    "height": 720,
                                    "device_scale_factor": 2,
                                },
                            },
                        }
                    ],
                },
            }
        )

    client = make_sync(handler)
    page = client.scrape(url="https://example.com")
    assert page.screenshot is not None
    assert page.screenshot.properties.viewport.device_scale_factor == 2
    assert page.screenshot.slices is not None
    assert page.screenshot.slices[0].row_nr == 0
    assert page.screenshot.slices[0].properties.height == 500
