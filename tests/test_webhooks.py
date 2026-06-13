"""Webhook signature verification + fetch_scrape_result_from_webhook (sync/async)."""

from __future__ import annotations

import hashlib
import hmac
import time

import httpx
import pytest

from conftest import json_response, make_async, make_sync
from crawlbrulee import (
    CrawlbruleeError,
    ScrapeCompleteWebhook,
    ScrapeCompleteWebhookData,
    verify_webhook_signature,
)
from crawlbrulee._webhooks import PRIMARY_HEADER, ROTATED_HEADER

SECRET = "whsec_current"
PREVIOUS_SECRET = "whsec_previous"
RAW_BODY = b'{"event":"scrape.complete","data":{"job_id":"job_1"}}'


def _sign(secret: str, timestamp: int, body: bytes) -> str:
    """Compute the wire signature header value the server would send."""
    signed = f"{timestamp}.".encode() + body
    digest = hmac.new(secret.encode(), msg=signed, digestmod=hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


# ----------------------------------------------------------------------
# verify_webhook_signature
# ----------------------------------------------------------------------


def test_valid_primary_signature() -> None:
    ts = int(time.time())
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: _sign(SECRET, ts, RAW_BODY)},
        secret=SECRET,
    )
    assert result.verified is True
    assert result.signed_with == "primary"
    assert result.reason is None


def test_valid_signature_with_str_payload_roundtrips() -> None:
    # A str payload must encode to the same bytes the server signed.
    body_str = RAW_BODY.decode()
    ts = int(time.time())
    result = verify_webhook_signature(
        payload=body_str,
        headers={PRIMARY_HEADER: _sign(SECRET, ts, RAW_BODY)},
        secret=SECRET,
    )
    assert result.verified is True
    assert result.signed_with == "primary"


def test_valid_rotated_only_signature() -> None:
    # The primary header is signed with a secret we no longer hold; the rotated
    # header is signed with the previous secret, which equals our current one.
    ts = int(time.time())
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={
            PRIMARY_HEADER: _sign("some_newer_secret", ts, RAW_BODY),
            ROTATED_HEADER: _sign(SECRET, ts, RAW_BODY),
        },
        secret=SECRET,
    )
    assert result.verified is True
    assert result.signed_with == "rotated"


def test_primary_preferred_over_rotated_when_both_match() -> None:
    ts = int(time.time())
    sig = _sign(SECRET, ts, RAW_BODY)
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: sig, ROTATED_HEADER: sig},
        secret=SECRET,
    )
    assert result.verified is True
    assert result.signed_with == "primary"


def test_tampered_body_mismatch() -> None:
    ts = int(time.time())
    result = verify_webhook_signature(
        payload=RAW_BODY + b"tampered",
        headers={PRIMARY_HEADER: _sign(SECRET, ts, RAW_BODY)},
        secret=SECRET,
    )
    assert result.verified is False
    assert result.reason == "signature_mismatch"


def test_wrong_secret_mismatch() -> None:
    ts = int(time.time())
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: _sign(SECRET, ts, RAW_BODY)},
        secret="whsec_wrong",
    )
    assert result.verified is False
    assert result.reason == "signature_mismatch"


def test_malformed_header() -> None:
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: "not-a-valid-signature"},
        secret=SECRET,
    )
    assert result.verified is False
    assert result.reason == "malformed_signature"


def test_malformed_header_uppercase_hex_rejected() -> None:
    # The grammar requires lowercase hex; uppercase must be treated as malformed.
    ts = int(time.time())
    digest = hmac.new(SECRET.encode(), msg=f"{ts}.".encode() + RAW_BODY, digestmod=hashlib.sha256)
    bad = f"t={ts},v1={digest.hexdigest().upper()}"
    result = verify_webhook_signature(
        payload=RAW_BODY, headers={PRIMARY_HEADER: bad}, secret=SECRET
    )
    assert result.verified is False
    assert result.reason == "malformed_signature"


def test_missing_headers() -> None:
    result = verify_webhook_signature(payload=RAW_BODY, headers={}, secret=SECRET)
    assert result.verified is False
    assert result.reason == "missing_signature"


def test_timestamp_out_of_tolerance() -> None:
    old_ts = int(time.time()) - 10_000
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: _sign(SECRET, old_ts, RAW_BODY)},
        secret=SECRET,
        tolerance_seconds=300,
    )
    assert result.verified is False
    assert result.reason == "timestamp_out_of_tolerance"


def test_timestamp_check_disabled_with_zero_tolerance() -> None:
    old_ts = int(time.time()) - 10_000
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER: _sign(SECRET, old_ts, RAW_BODY)},
        secret=SECRET,
        tolerance_seconds=0,
    )
    assert result.verified is True
    assert result.signed_with == "primary"


def test_case_insensitive_header_lookup() -> None:
    ts = int(time.time())
    # Frameworks frequently lowercase header names.
    result = verify_webhook_signature(
        payload=RAW_BODY,
        headers={PRIMARY_HEADER.lower(): _sign(SECRET, ts, RAW_BODY)},
        secret=SECRET,
    )
    assert result.verified is True
    assert result.signed_with == "primary"


# ----------------------------------------------------------------------
# fetch_scrape_result_from_webhook (sync)
# ----------------------------------------------------------------------


def _success_webhook_dict(job_id: str = "job_1") -> dict:
    return {
        "event_id": "evt_1",
        "timestamp": "2026-06-13T00:00:00Z",
        "event": "scrape.complete",
        "data": {
            "job_id": job_id,
            "status": "success",
            "url": "https://example.com",
            "completed_at": "2026-06-13T00:00:00Z",
        },
    }


def test_fetch_from_webhook_success_dict() -> None:
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        return json_response({"url": "https://example.com", "markdown": "# done"})

    client = make_sync(handler)
    page = client.fetch_scrape_result_from_webhook(_success_webhook_dict("job_42"))
    assert seen["path"] == "/api/scrape/result/job_42"
    assert page.markdown == "# done"


def test_fetch_from_webhook_success_dataclass() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/result/job_dc"
        return json_response({"url": "https://example.com", "markdown": "ok"})

    webhook = ScrapeCompleteWebhook(
        event_id="evt_1",
        timestamp="2026-06-13T00:00:00Z",
        event="scrape.complete",
        data=ScrapeCompleteWebhookData(
            job_id="job_dc",
            status="success",
            url="https://example.com",
            completed_at="2026-06-13T00:00:00Z",
        ),
    )
    client = make_sync(handler)
    page = client.fetch_scrape_result_from_webhook(webhook)
    assert page.markdown == "ok"


def test_fetch_from_webhook_failed_raises() -> None:
    body = _success_webhook_dict()
    body["data"]["status"] = "failed"
    body["data"]["error"] = "boom"

    client = make_sync(lambda r: json_response({}))
    with pytest.raises(CrawlbruleeError) as excinfo:
        client.fetch_scrape_result_from_webhook(body)
    assert "boom" in excinfo.value.message
    assert excinfo.value.error_name == "job_failed"


def test_fetch_from_webhook_cancelled_raises() -> None:
    body = _success_webhook_dict()
    body["data"]["status"] = "cancelled"

    client = make_sync(lambda r: json_response({}))
    with pytest.raises(CrawlbruleeError, match="cancelled"):
        client.fetch_scrape_result_from_webhook(body)


def test_fetch_from_webhook_wrong_event_raises() -> None:
    body = _success_webhook_dict()
    body["event"] = "scrape.started"

    client = make_sync(lambda r: json_response({}))
    with pytest.raises(CrawlbruleeError, match="scrape.complete"):
        client.fetch_scrape_result_from_webhook(body)


# ----------------------------------------------------------------------
# fetch_scrape_result_from_webhook (async)
# ----------------------------------------------------------------------


async def test_async_fetch_from_webhook_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/scrape/result/job_async"
        return json_response({"url": "https://example.com", "markdown": "async-done"})

    async with make_async(handler) as client:
        page = await client.fetch_scrape_result_from_webhook(_success_webhook_dict("job_async"))
    assert page.markdown == "async-done"


async def test_async_fetch_from_webhook_failed_raises() -> None:
    body = _success_webhook_dict()
    body["data"]["status"] = "failed"
    body["data"]["error"] = "kaboom"

    async with make_async(lambda r: json_response({})) as client:
        with pytest.raises(CrawlbruleeError) as excinfo:
            await client.fetch_scrape_result_from_webhook(body)
    assert "kaboom" in excinfo.value.message


async def test_async_fetch_from_webhook_cancelled_raises() -> None:
    body = _success_webhook_dict()
    body["data"]["status"] = "cancelled"

    async with make_async(lambda r: json_response({})) as client:
        with pytest.raises(CrawlbruleeError, match="cancelled"):
            await client.fetch_scrape_result_from_webhook(body)
