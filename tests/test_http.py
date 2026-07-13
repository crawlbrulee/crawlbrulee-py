"""Transport-level behavior: non-JSON bodies, empty bodies, timeouts."""

from __future__ import annotations

import httpx
import pytest

from conftest import BASE_URL
from crawlbrulee import TransportError
from crawlbrulee._http import SyncTransport


def _transport(handler: object) -> SyncTransport:
    client = httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]
    return SyncTransport(api_key="cwbl_test", base_url=BASE_URL, client=client)


def test_non_json_body_raises_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>not json</html>")

    transport = _transport(handler)
    with pytest.raises(TransportError, match="non-JSON"):
        transport.request("GET", "/api/whoami")


def test_empty_body_parses_as_empty_dict() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"")

    transport = _transport(handler)
    assert transport.request("GET", "/api/whoami") == {}


def test_unrecognized_json_error_body_raises_transport_error() -> None:
    # Valid JSON but not the standard {name, message} error shape -> HTTP <status>.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"unexpected": "shape"})

    transport = _transport(handler)
    with pytest.raises(TransportError, match="HTTP 500"):
        transport.request("GET", "/api/whoami")


def test_non_json_body_with_error_status_raises_non_json_error() -> None:
    # Non-JSON body is reported as such regardless of status (matches the JS SDK).
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = _transport(handler)
    with pytest.raises(TransportError, match="non-JSON"):
        transport.request("GET", "/api/whoami")


def test_timeout_maps_to_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    transport = SyncTransport(api_key="cwbl_test", base_url=BASE_URL, timeout=2.5, client=client)
    with pytest.raises(TransportError) as excinfo:
        transport.request("GET", "/api/whoami")
    assert excinfo.value.error_name == "request_timeout"
    # The configured timeout duration is surfaced in the message.
    assert "2.5s" in excinfo.value.message


def test_network_error_maps_to_transport_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    transport = _transport(handler)
    with pytest.raises(TransportError, match="Network error"):
        transport.request("GET", "/api/whoami")


def test_path_must_start_with_slash() -> None:
    transport = _transport(lambda r: httpx.Response(200, content=b"{}"))
    with pytest.raises(ValueError, match="must start with"):
        transport.request("GET", "api/whoami")
