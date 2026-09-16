"""Async-job endpoints, wait_for_scrape polling, and the AsyncCrawlbrulee client."""

from __future__ import annotations

import httpx
import pytest

from conftest import json_response, make_async, make_sync, request_json
from crawlbrulee import Crawlbrulee, CrawlbruleeError, ScrapeWebhook


def test_scrape_async_returns_job_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/async"
        return json_response({"job_id": "job_123"})

    client = make_sync(handler)
    result = client.scrape_async(url="https://example.com")
    assert result.job_id == "job_123"


def test_scrape_async_sends_webhook_dataclass() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request_json(request)
        return json_response({"job_id": "job_123"})

    client = make_sync(handler)
    client.scrape_async(
        url="https://example.com",
        webhook=ScrapeWebhook(
            url="https://hooks.example.com/cbl",
            metadata={"order_id": "abc-123"},
        ),
    )

    assert captured["path"] == "/api/scrape/async"
    assert captured["body"]["webhook"] == {
        "url": "https://hooks.example.com/cbl",
        "metadata": {"order_id": "abc-123"},
    }


def test_scrape_async_accepts_webhook_dict() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response({"job_id": "job_123"})

    client = make_sync(handler)
    client.scrape_async(
        url="https://example.com",
        webhook={"url": "https://hooks.example.com/cbl"},
    )

    # No metadata supplied -> only the url is sent (None omitted).
    assert captured["body"]["webhook"] == {"url": "https://hooks.example.com/cbl"}


def test_scrape_async_without_webhook_omits_field() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response({"job_id": "job_123"})

    client = make_sync(handler)
    client.scrape_async(url="https://example.com")
    assert "webhook" not in captured["body"]


def test_sync_scrape_has_no_webhook_param() -> None:
    # The webhook field is async-only; the sync scrape() must not accept it.
    import inspect

    assert "webhook" not in inspect.signature(Crawlbrulee.scrape).parameters
    assert "webhook" in inspect.signature(Crawlbrulee.scrape_async).parameters


async def test_async_client_scrape_async_sends_webhook() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = request_json(request)
        return json_response({"job_id": "job_async"})

    async with make_async(handler) as client:
        result = await client.scrape_async(
            url="https://example.com",
            webhook=ScrapeWebhook(
                url="https://hooks.example.com/cbl",
                metadata={"team": "growth"},
            ),
        )

    assert result.job_id == "job_async"
    assert captured["path"] == "/api/scrape/async"
    assert captured["body"]["webhook"] == {
        "url": "https://hooks.example.com/cbl",
        "metadata": {"team": "growth"},
    }


async def test_async_client_scrape_async_without_webhook_omits_field() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = request_json(request)
        return json_response({"job_id": "job_async"})

    async with make_async(handler) as client:
        await client.scrape_async(url="https://example.com")
    assert "webhook" not in captured["body"]


def test_get_scrape_status_reads_snake_case_wire_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/status/job_123"
        return json_response(
            {"job_id": "job_123", "status": "running", "created_at": "2026-05-28T00:00:00Z"}
        )

    client = make_sync(handler)
    status = client.get_scrape_status("job_123")
    assert status.job_id == "job_123"
    assert status.status == "running"
    assert status.created_at == "2026-05-28T00:00:00Z"
    assert status.error is None
    # response_meta is omitted while the job is still in flight.
    assert status.response_meta is None


def test_get_scrape_status_done_carries_usage_meta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {
                "job_id": "job_123",
                "status": "done",
                "created_at": "2026-05-28T00:00:00Z",
                "response_meta": {
                    "usage": {
                        "credits": 5,
                        "engine": "http",
                        "proxy": "advanced",
                        "screenshot_slices": 0,
                    }
                },
            }
        )

    client = make_sync(handler)
    status = client.get_scrape_status("job_123")
    assert status.status == "done"
    assert status.response_meta is not None
    assert status.response_meta.usage.credits == 5
    assert status.response_meta.usage.engine == "http"
    assert status.response_meta.usage.proxy == "advanced"
    assert status.response_meta.usage.screenshot_slices == 0


def test_job_id_is_url_encoded() -> None:
    seen: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        # raw_path keeps the percent-encoding (url.path would decode %2F back to /).
        seen["raw_path"] = request.url.raw_path
        return json_response({"job_id": "a/b", "status": "done", "created_at": "t"})

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
            return json_response({"job_id": "j1", "status": state, "created_at": "t"})
        if request.url.path == "/api/scrape/result/j1":
            return json_response(
                {
                    "url": "https://example.com",
                    "requested_url": "https://example.com",
                    "markdown": "done!",
                }
            )
        raise AssertionError(request.url.path)

    client = make_sync(handler)
    page = client.wait_for_scrape("j1", interval=0.001)
    assert calls["status"] == 3
    assert page.markdown == "done!"


def test_wait_for_scrape_failed_raises_job_failed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(
            {"job_id": "j1", "status": "failed", "created_at": "t", "error": "boom"}
        )

    client = make_sync(handler)
    with pytest.raises(CrawlbruleeError) as excinfo:
        client.wait_for_scrape("j1", interval=0.001)
    assert excinfo.value.error_name == "job_failed"
    assert "boom" in excinfo.value.message


def test_wait_for_scrape_timeout_raises_request_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"job_id": "j1", "status": "pending", "created_at": "t"})

    client = make_sync(handler)
    with pytest.raises(CrawlbruleeError) as excinfo:
        client.wait_for_scrape("j1", interval=0.001, timeout=0.02)
    assert excinfo.value.error_name == "request_timeout"


async def test_async_client_scrape() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape"
        return json_response(
            {
                "url": "https://example.com",
                "requested_url": "https://example.com",
                "markdown": "# async",
            }
        )

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
            return json_response({"job_id": "j1", "status": state, "created_at": "t"})
        return json_response(
            {"url": "https://example.com", "requested_url": "https://example.com", "markdown": "ok"}
        )

    async with make_async(handler) as client:
        page = await client.wait_for_scrape("j1", interval=0.001)
    assert page.markdown == "ok"
