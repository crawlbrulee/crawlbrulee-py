# crawlbrulee Python SDK — design

**Repo:** `crawlbrulee-py` · **Notion:** Ship the Python SDK (CWBL, In Progress) ·
**Mirrors:** `crawlbrulee-js` (`@crawlbrulee/sdk`, CWBL-141) · **Strategy:** CWBL-139
(hand-written, no codegen until SDK #3)

## Goal

Ship the second crawlbrulee client library: a hand-written, fully typed Python SDK,
feature-equivalent to the TS/JS SDK but idiomatic Python. Foundation that a future
Python CLI / tooling can wrap.

## Scope (v0.1.0)

Customer-facing API surface only — the same endpoints as the TS SDK:

| Endpoint | Method |
| --- | --- |
| `POST /api/scrape` | `scrape()` |
| `POST /api/scrape/async` | `scrape_async()` → `{job_id}` |
| `GET /api/scrape/status/:jobId` | `get_scrape_status()` |
| `GET /api/scrape/result/:jobId` | `get_scrape_result()` |
| (convenience) | `wait_for_scrape()` — polls until terminal, returns the result |
| `POST /api/map` | `map()` |
| `GET /api/usage` | `usage()` |
| `GET /api/whoami` | `whoami()` |

### Out of scope (intentional, matches TS SDK)

- `/public/health`, `/metrics` — infra concerns, not product features.
- Persistence / login flow / config files — the CLI's job.
- Streaming / SSE / webhooks — the API exposes none yet.

## Decisions

- **Distribution name:** `crawlbrulee` on PyPI (flat namespace; no npm-style scopes).
  `pip install crawlbrulee` → `import crawlbrulee`. (`crawlbrulee` and `crawlbrulee-sdk`
  both unclaimed as of 2026-05-28.)
- **Client surface:** two clients — `Crawlbrulee` (sync) and `AsyncCrawlbrulee` (async).
  Forced by httpx (sync and async clients are distinct); the two-client split is the
  Python standard (openai/anthropic/stripe/httpx). Shared logic lives in a base.
- **DTOs:** `@dataclass`. String-unions (`ProxyTier`, `ScreenshotType`, `AsyncJobStatus`,
  `ApiErrorName`, `UsageAllocationReason`) are `Literal[...]` aliases (keep wire values,
  no `Enum`).
- **Request input:** top-level request fields are **explicit keyword arguments** on each
  method (best autocomplete/signature help). Nested structures (`extract`, `screenshot`,
  `cache`, `location`, map `types`) are typed dataclasses **or** plain dicts. Responses are
  always dataclasses.
- **Timeouts:** seconds (`float`), Python-idiomatic. Default `None` = no timeout (matches
  the JS default of `0`). Per-call override on every method.
- **Cancellation:** no `AbortSignal` equivalent. Sync has no cancellation primitive; async
  callers cancel via normal `asyncio` task cancellation (httpx honors it). Covered by
  `timeout` + asyncio.
- **Runtime dependency:** `httpx` only. Dev: `ruff`, `pyright`, `pytest`. Build: `uv` +
  `hatchling`.
- **Python:** 3.10+, `from __future__ import annotations` everywhere. (3.10 floor: the
  reflective `from_dict` evaluates `X | None` annotations at runtime via
  `get_type_hints`, which needs PEP 604 unions; 3.9 is also EOL as of 2025-10.)
- **License:** AGPL-3.0-only (matches TS SDK).

### Deliberate divergences from the JS SDK

- **`AsyncJobStatusResponse` uses Pythonic `job_id` / `created_at`** instead of the wire's
  camelCase `jobId` / `createdAt`. A per-class wire-alias map handles the rename during
  deserialization. (The JS SDK chose to mirror the wire faithfully; camelCase attributes
  are a wart in Python.) Documented in the README.
- **Request fields as method kwargs** rather than a single request-object argument
  (JS passes `scrape({ url, ... })`).

## Repo layout

```
crawlbrulee-py/
  pyproject.toml            # uv + hatchling, AGPL-3.0-only, runtime dep: httpx
  README.md
  LICENSE
  src/crawlbrulee/
    __init__.py             # public exports: clients, errors, types, config constants
    py.typed                # PEP 561 marker (ship type info)
    _config.py              # DEFAULT_BASE_URL, ENV_API_KEY, USER_AGENT, default timeout
    _errors.py              # error hierarchy + create_api_error()
    _serde.py               # to_dict (omit None) + from_dict (type-hint driven, alias hook)
    _http.py                # shared request build/parse/error-map; Sync + Async transports
    _client.py              # Crawlbrulee (sync)
    _async_client.py        # AsyncCrawlbrulee
    types/
      __init__.py
      common.py             # ProxyTier, Screenshot*, ApiError* + detail shapes
      scrape.py             # ScrapeExtract, ScrapeCache, ScrapeLocation, ScrapeResponse, ...
      map.py                # MapTypes, MapCache, MapLocation, MapResponse + meta shapes
      async_.py             # AsyncScrapeResponse, AsyncJobStatusResponse
      account.py            # UsageResponse, WhoamiResponse
  tests/                    # pytest + httpx.MockTransport (no network, no extra dep)
```

Internal modules are underscore-prefixed (openai-python convention). Public surface is
re-exported from `crawlbrulee/__init__.py`; types are also reachable at `crawlbrulee.types`.

## Public API

### Construction

```python
Crawlbrulee(api_key: str, *, base_url: str | None = None, timeout: float | None = None)
AsyncCrawlbrulee(api_key: str, *, base_url: str | None = None, timeout: float | None = None)

Crawlbrulee.from_env(**overrides)        # reads CRAWLBRULEE_API_KEY; same for AsyncCrawlbrulee
```

- `api_key` stripped; empty/whitespace rejected with `CrawlbruleeError`.
- `base_url` defaults to `https://api.crawlbrulee.com`; trailing slash stripped.
- Context-manager support: `with Crawlbrulee(...) as c:` / `async with AsyncCrawlbrulee(...)`.
  Also `close()` / `aclose()` to release the httpx client. The httpx client is created at
  construction and reused across calls (connection pooling).

### Methods (identical signatures on both clients; async ones are awaitable)

```python
scrape(url, *, extract=None, cache=None, require_js=None, exclude_selectors=None,
       proxy=None, location=None, timeout=None) -> ScrapeResponse

scrape_async(url, *, extract=None, cache=None, require_js=None, exclude_selectors=None,
             proxy=None, location=None, timeout=None) -> AsyncScrapeResponse

get_scrape_status(job_id, *, timeout=None) -> AsyncJobStatusResponse
get_scrape_result(job_id, *, timeout=None) -> ScrapeResponse

wait_for_scrape(job_id, *, interval=2.0, timeout=300.0) -> ScrapeResponse
    # polls get_scrape_status until terminal, then get_scrape_result.
    # 'failed'  -> CrawlbruleeError(error_name="job_failed")
    # exceeded  -> CrawlbruleeError(error_name="request_timeout")  (timeout=0 waits forever)
    # sync sleeps with time.sleep; async with asyncio.sleep.

map(url, *, proxy=None, sitemap_only=None, types=None, cache=None, max_urls=None,
    page=None, limit=None, location=None, timeout=None) -> MapResponse

usage(*, timeout=None) -> UsageResponse
whoami(*, timeout=None) -> WhoamiResponse
```

`job_id` is validated non-empty and URL-encoded into the path.

## Types

Direct port of `crawlbrulee-js/src/types/`. Highlights:

- `common.py`: `ProxyTier = Literal["basic","advanced","auto","none"]`;
  `ScreenshotType`, `ScreenshotDeviceMode`; `ScreenshotCleanup`, `ScreenshotViewport`,
  `ScreenshotRequest`; action unions `ScreenshotWaitAction | ScreenshotScrollAction`
  (before) and `ScreenshotSliceAction` (after); `ApiErrorName` Literal union;
  `UsageAllocationReason`; `UsageLimitDetails`, `UsageAllocationErrorDetails`,
  `RateLimitErrorDetails`, `ApiErrorResponse`.
- `scrape.py`: `ScrapeExtract`, `ScrapeCache` (`max_age: int | str | None`),
  `ScrapeLocation`, plus response shapes `ScreenshotProperties`, `ScreenshotSlice`,
  `ScreenshotResult`, `PageInlineImage`, `PageLink`, `ScrapeMetadata`, `ScrapeResponse`.
- `map.py`: `MapTypes`, `MapCache`, `MapLocation`, `MapLinkItem`, `MapPagination`,
  `MapTruncation`, `MapResponse` (with nested `meta`).
- `async_.py`: `AsyncScrapeResponse`, `AsyncJobStatusResponse` (Pythonic field names + alias map).
- `account.py`: `UsageResponse`, `WhoamiResponse`.

All request-side nested dataclasses have optional fields defaulting to `None`.

## Serialization (`_serde.py`)

- **`to_dict(obj)`** — request bodies. Recurse over dataclass fields; **omit `None`** so
  server defaults apply; recurse into nested dataclasses and lists. snake_case field names
  already equal wire keys, so no remap on the request side. A plain `dict` passes through
  unchanged (lets callers hand-roll a body).
- **`from_dict(cls, data)`** — responses. Small generic builder driven by `typing` hints:
  handles `Optional[X]`, `list[X]`, nested dataclasses, and primitives. Unknown keys are
  ignored (forward-compatible with new server fields). Honors an optional
  `__wire_aliases__: dict[str, str]` (wire-key → field-name) on a dataclass, used by
  `AsyncJobStatusResponse`.

## Errors (`_errors.py`)

Mirrors the JS hierarchy:

- `CrawlbruleeError(Exception)` — base. Attrs: `message`, `status` (int; `0` for transport),
  `error_name` (`ApiErrorName | None`), `details` (dict | None), `response` (dict | None).
- `AuthenticationError` — 401/403 (`invalid_credentials`, `access_denied`).
- `RateLimitError` — 429; attrs `retry_after_ms`, `limited_by`. `error_name` normalized to
  `too_many_requests`.
- `UsageAllocationError` — plan limits; attrs `reason`, `usage`. `error_name`
  `usage_allocation_error` (synthesizes `reason="internal_error"` if details missing).
- `ValidationError` — `validation_error`, `invalid_url`, `url_too_long`,
  `unsupported_url_schema`, `url_credentials_not_supported`, `blocked_url`,
  `unsupported_content`.
- `NotFoundError` — 404 / `not_found`.
- `TransportError` — network failure, timeout (`error_name="request_timeout"`), aborted
  (`client_closed_request`), or non-JSON body. `status` defaults to `0`.
- `is_crawlbrulee_error(err)` helper.

**`create_api_error(body, status)`** — same **name-first** dispatch as the JS
`createApiError`: switch on the body's `name`; fall back to status heuristics (429 →
RateLimit, 401/403 → Auth, 404 → NotFound) only when the name is unrecognized; never
override what the name said.

## HTTP layer (`_http.py`)

- Shared, mode-agnostic helpers: build URL (`base_url` + path, path must start with `/`),
  headers (`authorization: Bearer <key>`, `accept: application/json`, `user-agent`,
  `content-type` when there's a body), JSON-encode the body, and `parse_response()` that
  maps non-2xx → typed error (via `create_api_error`) or non-JSON → `TransportError`.
- `SyncTransport` wraps `httpx.Client`; `AsyncTransport` wraps `httpx.AsyncClient`. Each owns
  request execution and translates httpx exceptions: `httpx.TimeoutException` →
  `TransportError(error_name="request_timeout")`, other `httpx.TransportError` → generic
  `TransportError`.
- An instrumentation seam lets tests inject an `httpx.MockTransport` and an alternate
  base URL without monkeypatching globals (mirrors the JS `CwblInstrumentation` seam).
- Empty response body parses to `{}` (matches JS).

## Config (`_config.py`)

```python
DEFAULT_BASE_URL = "https://api.crawlbrulee.com"
ENV_API_KEY = "CRAWLBRULEE_API_KEY"
USER_AGENT = "crawlbrulee-python/<version> (httpx)"
DEFAULT_REQUEST_TIMEOUT = None   # no timeout unless caller sets one
```

## Testing

pytest + `httpx.MockTransport` (no network, no extra dependency), run against **both**
clients where behavior should match. Port the JS suite's coverage:

- client construction, `from_env`, missing/blank key, `base_url` normalization
- `scrape` happy path + extract serialization (None omitted)
- `scrape_async` + `wait_for_scrape` polling (pending→running→done, failed, timeout)
- `map`, `usage`, `whoami`
- error mapping for every branch of `create_api_error` (name-first + status fallback)
- transport: network error, timeout, non-JSON body, empty body
- serde round-trip (`to_dict` omit-None; `from_dict` nesting + `__wire_aliases__`)

`verify` target: `ruff check` + `ruff format --check` + `pyright` + `pytest` + `uv build`.

## Distribution / packaging

- Build backend: `hatchling`, `src/` layout, `py.typed` shipped.
- Publish to PyPI as `crawlbrulee` (`uv build` + `uv publish` / `twine`). Repo stays private
  until a publish-readiness review, same as the TS SDK.
- PyPI namespace is flat and global; a name is claimed by uploading a release (no
  reserve-without-publish). PEP 503 normalization collapses dash/underscore/case variants.
  Optionally squat the typo `crawlbrule` like the npm CLI placeholder.

## Open items

None blocking. DTO-to-spec drift is tracked at the ecosystem level (manual bump for now;
revisit when the SDK count grows) — same as the TS SDK.
