# crawlbrulee

The official Python SDK for the [crawlbrulee](https://crawlbrulee.com) web-scraping API.

- Fully typed (ships `py.typed`).
- Sync **and** async clients (`Crawlbrulee` / `AsyncCrawlbrulee`).
- One runtime dependency: [`httpx`](https://www.python-httpx.org/).
- Python 3.10+.

> **Status:** v0.2.0 (beta). The API surface is stabilizing — expect minor breaking
> changes between 0.x releases.

---

## Install

```bash
pip install crawlbrulee
# or: uv add crawlbrulee
```

## Quickstart

```python
from crawlbrulee import Crawlbrulee, ScrapeExtract

client = Crawlbrulee(api_key="cble_…")
# or read CRAWLBRULEE_API_KEY from the environment:
client = Crawlbrulee.from_env()

page = client.scrape(
    url="https://example.com",
    extract=ScrapeExtract(markdown=True, links=True),
)

print(page.markdown)
print(len(page.links or []), "links found")
```

### Async

The async client mirrors the sync one method-for-method:

```python
import asyncio
from crawlbrulee import AsyncCrawlbrulee

async def main() -> None:
    async with AsyncCrawlbrulee.from_env() as client:
        page = await client.scrape(url="https://example.com")
        print(page.markdown)

asyncio.run(main())
```

### Configuration

| Option     | Default                        | Description                                                                  |
| ---------- | ------------------------------ | ---------------------------------------------------------------------------- |
| `api_key`  | —                              | Sent as `Authorization: Bearer …`. **Required** — or use `from_env()`.       |
| `base_url` | `https://api.crawlbrulee.com`  | Override the target host (local dev / staging). Trailing slashes stripped.   |
| `timeout`  | `None` (no timeout)            | Per-request timeout in **seconds**. A per-call `timeout=` overrides it.      |

`Crawlbrulee.from_env(**overrides)` reads the key from `CRAWLBRULEE_API_KEY` and
forwards any other option through.

Both clients support context managers (`with` / `async with`) and expose
`close()` / `aclose()` to release the connection pool.

---

## Request inputs

Top-level request fields are plain keyword arguments. Nested structures are typed
dataclasses (importable from `crawlbrulee`) — or plain `dict`s, if you prefer:

```python
from crawlbrulee import ScrapeExtract, ScreenshotRequest

client.scrape(
    url="https://news.example.com/article-1",
    extract=ScrapeExtract(
        markdown=True,
        metadata=True,
        links=True,
        screenshot=ScreenshotRequest(type="full_page", device_mode="desktop"),
    ),
    require_js=True,
    proxy="advanced",
    exclude_selectors=["nav", "footer"],
    cache={"max_age": 3600},          # dataclass or dict, your call
    location={"country": "US"},
)
```

`None`-valued options are omitted from the request entirely, so the server's
defaults apply.

---

## API reference

Every method returns a typed dataclass and accepts a per-call `timeout=` (seconds).

### Scraping

| Method | Description |
| --- | --- |
| `scrape(url, **opts)` | Scrape a URL synchronously; blocks until done. |
| `scrape_async(url, **opts)` | Submit a background job; returns `{ job_id }` immediately. |
| `get_scrape_status(job_id)` | Current job state — `pending` / `running` / `done` / `failed`. |
| `get_scrape_result(job_id)` | Result of a completed job (raises if not finished). |
| `wait_for_scrape(job_id, interval=2.0, timeout=300.0)` | Poll until terminal, then return the result. |

```python
job = client.scrape_async(url="https://example.com")
page = client.wait_for_scrape(job.job_id, interval=2.0, timeout=300.0)
```

`wait_for_scrape` raises a `CrawlbruleeError` with `error_name="job_failed"` if the
job fails, or `error_name="request_timeout"` if the wait expires (`timeout=0` waits
forever).

### Mapping

```python
result = client.map(
    url="https://example.com",
    sitemap_only=False,
    types={"internal": True, "external": False},
    max_urls=5_000,
    page=1,
    limit=1_000,
)
print(len(result.links), "of", result.meta.pagination.total_pages, "pages")
```

### Account

| Method | Description |
| --- | --- |
| `usage()` | Current billing-cycle snapshot — credits, quota %, concurrency, reset time. |
| `whoami()` | Organization + token identity behind the API key. |

---

## Webhooks

If you configure a webhook endpoint, the API POSTs a `scrape.complete` delivery
when an async scrape job reaches a terminal state. Each delivery is signed with
HMAC-SHA256 in the `X-Cwbl-Signature` header (`t=<unix_seconds>,v1=<hex>`), over
the `{timestamp}.{raw_body}` payload.

**Verify the signature first**, using the **raw** request body (the exact bytes
you received — not re-serialized JSON). `verify_webhook_signature` is pure crypto
(no network, no extra dependency) and **returns** a result instead of raising, so
a forged or replayed delivery is normal control flow:

```python
import json
from fastapi import FastAPI, Request, Response
from crawlbrulee import Crawlbrulee, verify_webhook_signature

app = FastAPI()
client = Crawlbrulee.from_env()
WEBHOOK_SECRET = "whsec_…"  # your current signing secret

@app.post("/webhooks/crawlbrulee")
async def crawlbrulee_webhook(request: Request) -> Response:
    raw = await request.body()  # raw bytes — do NOT re-encode the parsed JSON
    result = verify_webhook_signature(
        payload=raw,
        headers=request.headers,        # case-insensitive lookup
        secret=WEBHOOK_SECRET,
    )
    if not result.verified:
        return Response(status_code=400)  # result.reason explains why

    webhook = json.loads(raw)
    page = client.fetch_scrape_result_from_webhook(webhook)
    print(page.markdown)
    return Response(status_code=200)
```

(In Flask, the equivalent is `request.get_data()` for the raw body and
`request.headers` for the lookup.)

`fetch_scrape_result_from_webhook(webhook)` accepts the parsed webhook as either
the decoded `dict` or a `ScrapeCompleteWebhook` dataclass. On a `success` job it
fetches the result via `get_scrape_result`; on `failed` it raises a
`CrawlbruleeError` carrying the error message (`error_name="job_failed"`), and on
`cancelled` it raises indicating cancellation.

**Secret rotation.** During a rotation grace window the API also sends an
`X-Cwbl-Signature-Rotated` header signed with the *previous* secret. Keep passing
your current secret — `verify_webhook_signature` checks the primary header first,
then the rotated one, and reports which matched via `result.signed_with`
(`"primary"` or `"rotated"`).

**Replay protection** is on by default: deliveries whose timestamp differs from
now by more than `tolerance_seconds` (default `300`) are rejected with
`reason="timestamp_out_of_tolerance"`. Pass `tolerance_seconds=0` to disable it.

---

## Errors

Every failure raised by the SDK subclasses `CrawlbruleeError`:

| Class | When |
| --- | --- |
| `AuthenticationError` | 401 / 403 (missing, invalid, or unauthorized key). |
| `RateLimitError` | 429. Exposes `retry_after_ms` and `limited_by` when provided. |
| `UsageAllocationError` | Plan limit hit. Exposes `reason` and `usage`. |
| `ValidationError` | Bad request (`invalid_url`, `url_too_long`, `blocked_url`, …). |
| `NotFoundError` | 404 (e.g. unknown async `job_id`). |
| `TransportError` | Network failure, timeout, or non-JSON response. |
| `CrawlbruleeError` | Base class — any other API error. Always has `status`, `error_name`, `message`. |

```python
import time
from crawlbrulee import Crawlbrulee, RateLimitError, UsageAllocationError

client = Crawlbrulee.from_env()
try:
    client.scrape(url="https://example.com")
except RateLimitError as err:
    time.sleep((err.retry_after_ms or 1000) / 1000)
    # retry…
except UsageAllocationError as err:
    print("Plan limit hit:", err.reason, err.usage)
```

For exhaustive branching, switch on `err.error_name`.

---

## Notes on the wire format

The SDK mirrors the API's JSON shapes faithfully. The one exception: the async job
**status** response uses camelCase on the wire (`jobId`, `createdAt`); the SDK
exposes Pythonic `job_id` / `created_at` on `AsyncJobStatusResponse`.

---

## Development

```bash
uv sync                 # or: pip install -e ".[dev]"
ruff check . && ruff format --check .
pyright
pytest
```

The SDK keeps a single runtime dependency (`httpx`) on purpose — please keep it that
way when contributing.

## License

[AGPL-3.0-only](./LICENSE)
