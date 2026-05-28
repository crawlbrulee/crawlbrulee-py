"""Client construction, env handling, base-URL normalization, headers."""

from __future__ import annotations

import httpx
import pytest

from conftest import json_response, make_sync
from crawlbrulee import Crawlbrulee, CrawlbruleeError


def test_missing_api_key_raises() -> None:
    with pytest.raises(CrawlbruleeError, match="Missing API key"):
        Crawlbrulee("")
    with pytest.raises(CrawlbruleeError, match="Missing API key"):
        Crawlbrulee("   ")


def test_api_key_is_trimmed_and_sent_as_bearer() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["accept"] = request.headers["accept"]
        seen["ua"] = request.headers["user-agent"]
        return json_response({"organization_name": "o", "token_name": "t", "token_preview": "p"})

    # Inject a transport but exercise the public header path via a real request.
    client = make_sync(handler)
    client.whoami()
    assert seen["auth"] == "Bearer cble_test"
    assert seen["accept"] == "application/json"
    assert seen["ua"].startswith("crawlbrulee-python/")


def test_base_url_trailing_slash_stripped() -> None:
    client = Crawlbrulee("cble_test", base_url="https://example.com/api/")
    assert client.base_url == "https://example.com/api"


def test_default_base_url() -> None:
    client = Crawlbrulee("cble_test")
    assert client.base_url == "https://api.crawlbrulee.com"


def test_from_env_reads_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLBRULEE_API_KEY", "cble_from_env")
    client = Crawlbrulee.from_env()
    assert isinstance(client, Crawlbrulee)


def test_from_env_missing_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CRAWLBRULEE_API_KEY", raising=False)
    with pytest.raises(CrawlbruleeError, match="is not set"):
        Crawlbrulee.from_env()


def test_from_env_blank_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CRAWLBRULEE_API_KEY", "   ")
    with pytest.raises(CrawlbruleeError, match="is not set"):
        Crawlbrulee.from_env()


def test_context_manager_smoke() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return json_response({"organization_name": "o", "token_name": "t", "token_preview": "p"})

    with make_sync(handler) as client:
        result = client.whoami()
    assert result.organization_name == "o"
