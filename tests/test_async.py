"""Async-job endpoints, wait_for_scrape polling, and the AsyncCrawlbrulee client."""

from __future__ import annotations

import httpx
import pytest

from conftest import json_response, make_async, make_sync
from crawlbrulee import CrawlbruleeError


def test_scrape_async_returns_job_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/async"
        return json_response({"job_id": "job_123"})

    client = make_sync(handler)
    result = client.scrape_async(url="https://example.com")
    assert result.job_id == "job_123"


def test_get_scrape_status_maps_camelcase_wire_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/status/job_123"
        return json_response(
            {"jobId": "job_123", "status": "running", "createdAt": "2026-05-28T00:00:00Z"}
        )

    client = make_sync(handler)
    status = client.get_scrape_status("job_123")
    assert status.job_id == "job_123"
    assert status.status == "running"
    assert status.created_at == "2026-05-28T00:00:00Z"
    assert status.error is None


def test_job_id_is_url_encoded() -> None:
    seen: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        # raw_path keeps the percent-encoding (url.path would decode %2F back to /).
        seen["raw_path"] = request.url.raw_path
        return json_response({"jobId": "a/b", "status": "done", "createdAt": "t"})

    client = make_sync(handler)
    client.get_scrape_status("a/b")
    assert seen["raw_path"] == b"/api/scrape/status/a%2Fb"


def test_empty_job_id_raises() -> None:
    client = make_sync(lambda r: json_response({}))
    with pytest.raises(CrawlbruleeError, match="non-empty"):
        client.get_scrape_status("  ")


def test_wait_for_scrape_polls_until_done() -> None:
    calls = {"status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/scrape/status/"):
            calls["status"] += 1
            state = "pending" if calls["status"] < 3 else "done"
            return json_response({"jobId": "j1", "status": state, "createdAt": "t"})
        if request.url.path == "/api/scrape/result/j1":
            return json_response({"url": "https://example.com", "markdown": "done!"})
        raise AssertionError(request.url.path)

    client = make_sync(handler)
    page = client.wait_for_scrape("j1", interval=0.001)
    assert calls["status"] == 3
    assert page.markdown == "done!"


def test_wait_for_scrape_failed_raises_job_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"jobId": "j1", "status": "failed", "createdAt": "t", "error": "boom"})

    client = make_sync(handler)
    with pytest.raises(CrawlbruleeError) as excinfo:
        client.wait_for_scrape("j1", interval=0.001)
    assert excinfo.value.error_name == "job_failed"
    assert "boom" in excinfo.value.message


def test_wait_for_scrape_timeout_raises_request_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"jobId": "j1", "status": "pending", "createdAt": "t"})

    client = make_sync(handler)
    with pytest.raises(CrawlbruleeError) as excinfo:
        client.wait_for_scrape("j1", interval=0.001, timeout=0.02)
    assert excinfo.value.error_name == "request_timeout"


async def test_async_client_scrape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape"
        return json_response({"url": "https://example.com", "markdown": "# async"})

    client = make_async(handler)
    page = await client.scrape(url="https://example.com")
    assert page.markdown == "# async"
    await client.aclose()


async def test_async_client_wait_for_scrape() -> None:
    calls = {"status": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/api/scrape/status/"):
            calls["status"] += 1
            state = "running" if calls["status"] < 2 else "done"
            return json_response({"jobId": "j1", "status": state, "createdAt": "t"})
        return json_response({"url": "https://example.com", "markdown": "ok"})

    async with make_async(handler) as client:
        page = await client.wait_for_scrape("j1", interval=0.001)
    assert page.markdown == "ok"
