"""HTTP layer: URL/header composition, JSON (de)coding, error mapping, and the
sync / async transports backed by httpx.

The transports accept an optional pre-built httpx client, which is the seam the
test suite uses to inject an ``httpx.MockTransport`` and an alternate base URL
without touching globals.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from ._config import DEFAULT_BASE_URL, USER_AGENT
from ._errors import CrawlbruleeError, TransportError, create_api_error


def _strip_trailing_slash(url: str) -> str:
    return url.rstrip("/")


def _truncate_preview(text: str, limit: int = 200) -> str:
    return text[:limit] + ("…" if len(text) > limit else "")


def _build_headers(api_key: str, has_body: bool) -> dict[str, str]:
    headers = {
        "accept": "application/json",
        "user-agent": USER_AGENT,
        "authorization": f"Bearer {api_key}",
    }
    if has_body:
        headers["content-type"] = "application/json"
    return headers


def _parse_json_or_raise(text: str, status: int) -> Any:
    if text == "":
        return {}
    try:
        return json.loads(text)
    except ValueError as exc:
        raise TransportError(
            f"Unexpected non-JSON response (status {status}): {_truncate_preview(text)}",
            status=status,
            cause=exc,
        ) from exc


def _to_api_error(parsed: Any, status: int, raw: str) -> CrawlbruleeError:
    if (
        isinstance(parsed, dict)
        and isinstance(parsed.get("name"), str)
        and isinstance(parsed.get("message"), str)
    ):
        return create_api_error(parsed, status)
    preview = _truncate_preview(raw)
    return TransportError(f"HTTP {status}: {preview or '(empty body)'}", status=status)


def _parse_response(status: int, is_success: bool, text: str) -> Any:
    parsed = _parse_json_or_raise(text, status)
    if not is_success:
        raise _to_api_error(parsed, status, text)
    return parsed


def _encode_body(body: dict[str, Any] | None) -> str | None:
    return None if body is None else json.dumps(body)


class SyncTransport:
    """Blocking HTTP transport backed by ``httpx.Client``."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = _strip_trailing_slash(base_url or DEFAULT_BASE_URL)
        self._api_key = api_key
        self._timeout = timeout
        self._client = client or httpx.Client()
        self._owns_client = client is None

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = _build_url(self.base_url, path)
        headers = _build_headers(self._api_key, body is not None)
        effective_timeout = self._timeout if timeout is None else timeout
        try:
            response = self._client.request(
                method,
                url,
                headers=headers,
                content=_encode_body(body),
                timeout=effective_timeout,
            )
        except httpx.TimeoutException as exc:
            detail = f" after {effective_timeout}s" if effective_timeout else ""
            raise TransportError(
                f"Request timed out{detail}.", error_name="request_timeout", cause=exc
            ) from exc
        except httpx.RequestError as exc:
            raise TransportError(f"Network error: {exc}", cause=exc) from exc
        return _parse_response(response.status_code, response.is_success, response.text)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class AsyncTransport:
    """Async HTTP transport backed by ``httpx.AsyncClient``."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        timeout: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = _strip_trailing_slash(base_url or DEFAULT_BASE_URL)
        self._api_key = api_key
        self._timeout = timeout
        self._client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = _build_url(self.base_url, path)
        headers = _build_headers(self._api_key, body is not None)
        effective_timeout = self._timeout if timeout is None else timeout
        try:
            response = await self._client.request(
                method,
                url,
                headers=headers,
                content=_encode_body(body),
                timeout=effective_timeout,
            )
        except httpx.TimeoutException as exc:
            detail = f" after {effective_timeout}s" if effective_timeout else ""
            raise TransportError(
                f"Request timed out{detail}.", error_name="request_timeout", cause=exc
            ) from exc
        except httpx.RequestError as exc:
            raise TransportError(f"Network error: {exc}", cause=exc) from exc
        return _parse_response(response.status_code, response.is_success, response.text)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _build_url(base_url: str, path: str) -> str:
    if not path.startswith("/"):
        raise ValueError(f"crawlbrulee SDK: path must start with '/' (received {path!r})")
    return f"{base_url}{path}"
