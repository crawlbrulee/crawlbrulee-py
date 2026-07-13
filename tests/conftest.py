"""Shared test helpers: build clients wired to an httpx.MockTransport."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx

from crawlbrulee import AsyncCrawlbrulee, Crawlbrulee
from crawlbrulee._http import AsyncTransport, SyncTransport

#: Base URL used by the mock transport. The host is irrelevant -- MockTransport
#: intercepts every request -- but the path must match the SDK's routes.
BASE_URL = "https://api.test"

Handler = Callable[[httpx.Request], httpx.Response]


def make_sync(handler: Handler, *, timeout: float | None = None) -> Crawlbrulee:
    """A sync client whose requests are served by ``handler``."""
    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = SyncTransport(
        api_key="cwbl_test", base_url=BASE_URL, timeout=timeout, client=client
    )
    return Crawlbrulee("cwbl_test", transport=transport)


def make_async(handler: Handler, *, timeout: float | None = None) -> AsyncCrawlbrulee:
    """An async client whose requests are served by ``handler``."""
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    transport = AsyncTransport(
        api_key="cwbl_test", base_url=BASE_URL, timeout=timeout, client=client
    )
    return AsyncCrawlbrulee("cwbl_test", transport=transport)


def json_response(payload: object, status: int = 200) -> httpx.Response:
    """A JSON ``httpx.Response`` (uses ``content`` so empty bodies are exact)."""
    return httpx.Response(
        status,
        content=json.dumps(payload),
        headers={"content-type": "application/json"},
    )


def request_json(request: httpx.Request) -> dict:
    """Decode the JSON body of an intercepted request."""
    return json.loads(request.content)
