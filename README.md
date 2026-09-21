# 🍮 crawlbrulee python sdk

[![pypi](https://img.shields.io/pypi/v/crawlbrulee?style=flat-square&label=pypi)](https://pypi.org/project/crawlbrulee/)
[![python](https://img.shields.io/pypi/pyversions/crawlbrulee?style=flat-square&label=python)](https://pypi.org/project/crawlbrulee/)
[![license](https://img.shields.io/pypi/l/crawlbrulee?style=flat-square&label=license)](./LICENSE)

**EU-native web scraping for AI agents & developers.**

the official python sdk for [crawlbrulee](https://crawlbrulee.com), published to PyPI as [`crawlbrulee`](https://pypi.org/project/crawlbrulee/). one call turns any url into clean markdown, screenshots, metadata and links, with per-request usage on every response. typed sync and async clients with auth, retries, and error mapping built in.

- **everything runs in the EU.** the fetch, the render, the cache and your result never leave EU servers. the proxy exit is the one hop you choose: pick an EU exit and nothing leaves at all. gdpr-aligned, with a data processing agreement.
- **output made for models.** markdown with the page chrome stripped and the links kept, ready for the prompt. full-page screenshots can come back as tiles sized for an image model.
- **the hard parts, handled.** headless Chrome when a page needs it, rotating proxies with country selection, automatic retries, ad and cookie-banner removal, caching, background jobs and signed webhooks.
- **start free.** 750 credits, no credit card.

**get a free api key** → [dashboard.crawlbrulee.com](https://dashboard.crawlbrulee.com)

the sdk:

- fully typed (ships `py.typed`).
- sync **and** async clients (`Crawlbrulee` / `AsyncCrawlbrulee`).
- one runtime dependency: [`httpx`](https://www.python-httpx.org/).
- Python 3.10+.

this readme covers the sdk itself — the clients, the types, and the python-side ergonomics.
for how the api behaves — endpoints, parameters, and error semantics — please see our
[api docs](https://crawlbrulee.com/docs).

---

## install

```bash
pip install crawlbrulee
# or: uv add crawlbrulee
```

## quickstart

```python
from crawlbrulee import Crawlbrulee, ScrapeExtract

client = Crawlbrulee(api_key="cwbl_…")
# or read CRAWLBRULEE_API_KEY from the environment:
client = Crawlbrulee.from_env()

page = client.scrape(
    url="https://example.com",
    extract=ScrapeExtract(markdown=True, links=True),
)

print(page.markdown)
print(len(page.links or []), "links found")
print(page.metadata.title if page.metadata else None)

# Per-request billing + routing usage rides along on every success:
if page.response_meta:
    usage = page.response_meta.usage
    print(usage.credits, usage.engine, usage.proxy, usage.screenshot_slices)
```

### async

the async client mirrors the sync one method-for-method:

```python
import asyncio
from crawlbrulee import AsyncCrawlbrulee

async def main() -> None:
    async with AsyncCrawlbrulee.from_env() as client:
        page = await client.scrape(url="https://example.com")
        print(page.markdown)

asyncio.run(main())
```

### configuration

| option     | default                        | description                                                                  |
| ---------- | ------------------------------ | ---------------------------------------------------------------------------- |
| `api_key`  | —                              | sent as `Authorization: Bearer …`. **required** — or use `from_env()`.       |
| `base_url` | `https://api.crawlbrulee.com`  | override the target host (local dev / staging). trailing slashes stripped.   |
| `timeout`  | `None` (no timeout)            | per-request timeout in **seconds**. a per-call `timeout=` overrides it.      |

`Crawlbrulee.from_env(**overrides)` reads the key from `CRAWLBRULEE_API_KEY` and
forwards any other option through. keys are minted in the dashboard; see
[authentication](https://crawlbrulee.com/docs/authentication) for how the api consumes them.

both clients support context managers (`with` / `async with`) and expose
`close()` / `aclose()` to release the connection pool.

---

## request inputs

top-level request fields are plain keyword arguments. nested structures are typed
dataclasses (importable from `crawlbrulee`) — or plain `dict`s, if you prefer:

```python
from crawlbrulee import ScrapeCleanup, ScrapeExtract, ScreenshotRequest

client.scrape(
    url="https://news.example.com/article-1",
    extract=ScrapeExtract(
        markdown=True,
        metadata=True,
        links=True,
        screenshot=ScreenshotRequest(type="full_page", device_mode="desktop"),
    ),
    # Shapes markdown, cleaned_html, links, images AND the screenshot.
    # Never touches raw_html - that is always the page before any removal.
    cleanup=ScrapeCleanup(
        ads_and_popups=True,
        exclude_selectors=["nav", "footer"],
    ),
    require_js=True,
    proxy="advanced",
    cache={"max_age": 3600},          # dataclass or dict, your call
    location={"country": "US"},
)
```

`None`-valued options are omitted from the request entirely, so the server's
defaults apply.

**notes:**

- **`proxy` defaults to `auto`** when omitted — it starts at the basic tier and
  escalates to advanced on failure, billed at the delivered tier. pass `"basic"`
  or `"advanced"` to pin a tier. see
  [proxies & location](https://crawlbrulee.com/docs/proxies) for what each tier does.
- **screenshots.** in rare cases a screenshot can't be captured; when you also requested
  other outputs, those still arrive and the screenshot is simply left out, so
  `page.screenshot` is `None` — guard for it (`page.screenshot and page.screenshot.url`).
  a screenshot-**only** request that can't deliver fails instead — `422`
  `unsupported_screenshot_output` when the content type can't be screenshotted, `500` on
  a capture failure — and isn't billed. custom `viewport.width`/`height` are
  integers in `[16, 10000]` and `device_scale_factor` is in `[1, 3]` (fractional
  allowed); out-of-range values are rejected with a `400`. full capture options:
  [screenshots](https://crawlbrulee.com/docs/scrape/screenshots).
- **`extract.images`** urls preserve their query string and resolve document-relative
  `src`s against the full page url (browser parity) — the same rules as `links`.
  every extract field is documented under
  [extraction](https://crawlbrulee.com/docs/scrape/extraction).

for the complete request contract — every field, its defaults, and its constraints — see the
[scrape endpoint](https://crawlbrulee.com/docs/scrape) reference.

---

## api reference

every method returns a typed dataclass and accepts a per-call `timeout=` (seconds).

### scraping

| method | description |
| --- | --- |
| `scrape(url, **opts)` | scrape a url synchronously; blocks until done. |
| `scrape_async(url, **opts)` | submit a background job; returns `{ job_id }` immediately. |
| `get_scrape_status(job_id)` | current job state — `pending` / `running` / `done` / `failed`. |
| `get_scrape_result(job_id)` | result of a completed job (raises if not finished). |
| `wait_for_scrape(job_id, interval=2.0, timeout=300.0)` | poll until terminal, then return the result. |

```python
job = client.scrape_async(url="https://example.com")
page = client.wait_for_scrape(job.job_id, interval=2.0, timeout=300.0)
```

`wait_for_scrape` raises a `CrawlbruleeError` with `error_name="job_failed"` if the
job fails, or `error_name="request_timeout"` if the wait expires (`timeout=0` waits
forever). the job lifecycle itself — states, retention, and when to prefer async over
sync — is documented under [async scrape](https://crawlbrulee.com/docs/scrape/async).

#### the scrape response

a successful `scrape` / `get_scrape_result` returns a `ScrapeResponse`:

- `url` — the url that was actually scraped, after any redirects, in normalized
  form — the base that `links`, `images`, and `internal` labels are computed against.
- `requested_url` — the url you requested, echoed verbatim — before any redirects.
- `metadata` — extracted page metadata (`title`, `description`, OG/Twitter
  tags, …), present when `extract.metadata` is on (the default).
- `response_meta.usage` — per-request billing + routing usage:
  - `credits` — credits charged: engine base × proxy multiplier + screenshot slices.
  - `engine` — the delivered billing base: `"http"`, `"browser"`, `"screenshot"`,
    or `"cache"`. use `engine == "cache"` to identify a cache hit.
  - `proxy` — the proxy tier that actually ran: `"basic"` or `"advanced"` (the
    **resolved** tier — `"auto"` is decided server-side and is never echoed
    here).
  - `screenshot_slices` — `1` when this request produced screenshot slices and
    billed the flat +1 add-on; otherwise `0`.
- `warnings` — a list of stable string codes flagging something worth noting on an
  otherwise-successful scrape, in two families. an output hit a cap and was truncated —
  loudly, never silently — so the payload is partial but still usable:
  - `screenshot_truncated` — a long page exceeded the scrolling-screenshot height cap.
  - `links_truncated` — the page had more than 30 000 links.
  - `inline_images_truncated` — the page had more than 10 000 inline images.
  - `raw_html_truncated` — the serialized body html exceeded 10 000 000 characters.
  - `metadata_truncated` — the serialized head html exceeded 2 000 000 characters.

  or one section's extraction failed, so that field comes back omitted or empty while the
  rest of the scrape succeeds — which is how you tell "the page had none" from "we
  couldn't read them":
  - `links_unavailable` — link extraction failed.
  - `inline_images_unavailable` — image extraction failed.
  - `metadata_unavailable` — metadata extraction failed.

  the page body has no such code: if it can't be extracted the scrape fails outright
  rather than returning a hollow `200`, and isn't billed.

  safe to switch on — the `ScrapeWarningCode` literal gives you the known set, while the
  field itself stays `list[str]` so a code added later still deserializes. warnings are
  stored with the result, so cache hits and async result fetches report them too,
  filtered to the outputs you asked for.
- `unsupported_fields` — if you request an extract that doesn't apply to the content type
  (e.g. `markdown` of a pdf), that field name comes back here and the rest of your payload is
  still returned.

```python
page = client.scrape(url="https://example.com")
if page.response_meta and page.response_meta.usage.engine == "cache":
    print("served from cache —", page.response_meta.usage.credits, "credits")
```

### mapping

```python
result = client.map(
    url="https://example.com",
    sitemap_only=False,
    types={"internal": True, "external": False},
    max_urls=5_000,
    page=1,
    limit=1_000,
)
print(len(result.links), "of", result.response_meta.pagination.total_pages, "pages")
usage = result.response_meta.usage
print(usage.credits, "credits", "(cache hit)" if usage.engine == "cache" else "")
```

every argument is optional. leave one out and the server's default applies — the SDK
never sends one of its own. `max_urls` defaults to **5000** (maximum 100000) and `limit`,
the page size, defaults to **5000** (maximum 10000).

`max_urls` is a crawl budget, not a slice taken at the end: sitemap discovery stops as
soon as that many URLs are found, so a smaller value is a faster, cheaper crawl. a map
that hit the budget comes back with exactly `max_urls` links and `response_capped` still
`False` — the signal that the site has more is `discovery_cap_reason`:

```python
t = result.response_meta.truncation
if t.discovery_cap_reason == "max_urls":
    print("more pages exist — ask again with a higher max_urls")
elif t.discovery_cap_reason == "unread_files":
    # a sitemap file could not be read at all this time. often temporary —
    # asking again later can return a fuller map.
    print("some sitemap files could not be read — try again later")
elif t.discovery_capped:
    # "time", "file_budget", "depth" or "file_size" — the site itself is big,
    # slow or deep, so a bigger max_urls will not help.
    print("discovery stopped early:", t.discovery_cap_reason,
          f"({t.sitemaps_skipped} sitemap files skipped or partly read)")
```

`result.response_meta` carries map usage (`credits` / billed `engine` / resolved `proxy`)
alongside the `pagination` and `truncation` blocks. `truncation` has:

| field | meaning |
| --- | --- |
| `storage_capped` | the stored map hit the 100000-URL storage cap. |
| `response_capped` | more links were eligible than `max_urls`, so the list was trimmed. normally only true when home-page links pushed the total past it. |
| `total_before_max_urls` | URLs found before the `max_urls` cap was applied. |
| `total_detected_before_storage_cap` | URLs detected during discovery before the storage cap. |
| `discovery_capped` | discovery stopped before reading every sitemap file it found — the site has more pages than this map lists. |
| `sitemaps_skipped` | how many sitemap files were skipped or only partly read (too large, fetch failed, or a discovery limit hit). |
| `discovery_cap_reason` | which limit stopped discovery first, or `None`. one of `max_urls`, `time`, `file_budget`, `depth`, `file_size`, `unread_files`. only `max_urls` is yours to change; `unread_files` is often temporary, so asking again later can return more. |

each link is just `{"url": ...}`. returned URLs are
normalized, matching the `url` that `scrape` returns.

against an older server that predates `discovery_capped` / `sitemaps_skipped` /
`discovery_cap_reason`, those fields come back as `False` / `0` / `None` rather than
raising. see the [map endpoint](https://crawlbrulee.com/docs/map) for discovery rules and
pagination semantics.

the async **status** response (`get_scrape_status`) also gains a `response_meta.usage`
once the job is `done`:

```python
status = client.get_scrape_status(job_id)
if status.status == "done" and status.response_meta:
    print("job cost", status.response_meta.usage.credits, "credits")
```

### account

| method | description |
| --- | --- |
| `usage()` | current billing-cycle snapshot — credits, quota %, concurrency, reset time. |
| `whoami()` | organization + token identity behind the api key. |

what a call costs, and how credits are counted, is documented under
[credits & pricing](https://crawlbrulee.com/docs/credits-and-pricing).

---

## webhooks

if you configure a webhook endpoint, the api POSTs a `scrape.complete` delivery
when an async scrape job reaches a terminal state. each delivery is signed with
HMAC-SHA256 in the `X-Cwbl-Signature` header (`t=<unix_seconds>,v1=<hex>`), over
the `{timestamp}.{raw_body}` payload.

the delivery contract and payload shape live under
[webhooks](https://crawlbrulee.com/docs/scrape/webhooks); the signature scheme is specified in
[webhook verification](https://crawlbrulee.com/docs/webhook-verification). what follows is how
this sdk helps you consume them.


### triggering a webhook

pass `webhook=` to `scrape_async` to tell the api where to deliver the
`scrape.complete` POST for that job. this is **async-only** — the sync `scrape()`
response *is* the result, so it has no `webhook` parameter.

```python
from crawlbrulee import Crawlbrulee, ScrapeWebhook

client = Crawlbrulee.from_env()

job = client.scrape_async(
    url="https://example.com",
    webhook=ScrapeWebhook(
        url="https://your-app.example.com/webhooks/crawlbrulee",  # HTTPS in production
        metadata={"order_id": "abc-123"},                          # optional, dict or omit
    ),
)
# or pass a plain dict:
# webhook={"url": "https://your-app.example.com/webhooks/crawlbrulee"}
```

- `url` — http/https endpoint (max 2048 chars). **https is required in production.**
- `metadata` — opaque metadata object, echoed back verbatim in the webhook
  payload's `data.metadata` (max 2048 bytes serialized). use it to route
  deliveries without keeping your own `job_id` mapping.

the delivered `scrape.complete` payload carries the echoed object on
`data.metadata`, plus `data.response_meta.usage` (`credits` / billed `engine` /
resolved `proxy` / `screenshot_slices`) for the finished job:

```python
webhook = ScrapeCompleteWebhook(...)  # parsed from the delivery (see below)
print(webhook.data.metadata)                    # {"order_id": "abc-123"}
if webhook.data.response_meta:
    print("job cost", webhook.data.response_meta.usage.credits, "credits")
```

deliveries are signed with your **organization** webhook secret (configured in the
dashboard under account → webhooks); there is no per-request secret. verify and
consume them as shown below.

**verify the signature first**, using the **raw** request body (the exact bytes
you received — not re-serialized json). `verify_webhook_signature` is pure crypto
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

(in Flask, the equivalent is `request.get_data()` for the raw body and
`request.headers` for the lookup.)

`fetch_scrape_result_from_webhook(webhook)` accepts the parsed webhook as either
the decoded `dict` or a `ScrapeCompleteWebhook` dataclass. on a `success` job it
fetches the result via `get_scrape_result`; on `failed` it raises a
`CrawlbruleeError` carrying the error message (`error_name="job_failed"`), and on
`cancelled` it raises indicating cancellation.

**secret rotation.** during a rotation grace window the api also sends an
`X-Cwbl-Signature-Rotated` header signed with the *previous* secret. keep passing
your current secret — `verify_webhook_signature` checks the primary header first,
then the rotated one, and reports which matched via `result.signed_with`
(`"primary"` or `"rotated"`).

**replay protection** is on by default: deliveries whose timestamp differs from
now by more than `tolerance_seconds` (default `300`) are rejected with
`reason="timestamp_out_of_tolerance"`. pass `tolerance_seconds=0` to disable it.

---

## errors

every failure raised by the sdk subclasses `CrawlbruleeError`:

| class | when |
| --- | --- |
| `AuthenticationError` | 401 / 403 (missing, invalid, or unauthorized key). |
| `AntibotBlockedError` | 403 `antibot_blocked` — the target site's bot protection blocked us. not a key problem. |
| `TooManyRedirectsError` | 422 `too_many_redirects` — the target site redirected in a loop. not a bad request; retrying rarely helps. |
| `PageTooLargeError` | 422 `page_too_large` — the page's html was too large to process. terminal; do not retry it. |
| `RateLimitError` | 429. exposes `retry_after_ms` and `limited_by` when provided. |
| `UsageAllocationError` | plan limit hit. exposes `reason` and `usage`. |
| `ValidationError` | bad request (`invalid_url`, `url_too_long`, `blocked_url`, …). |
| `NotFoundError` | 404 (e.g. unknown async `job_id`). |
| `ServiceUnavailableError` | 503 (`service_unavailable`). transient infrastructure failure on our side — retry it. |
| `TransportError` | network failure, timeout, or non-json response. |
| `CrawlbruleeError` | base class — any other api error. always has `status`, `error_name`, `message`. |

```python
import time
from crawlbrulee import (
    Crawlbrulee,
    RateLimitError,
    ServiceUnavailableError,
    UsageAllocationError,
)

client = Crawlbrulee.from_env()
try:
    client.scrape(url="https://example.com")
except RateLimitError as err:
    time.sleep((err.retry_after_ms or 1000) / 1000)
    # retry…
except ServiceUnavailableError:
    time.sleep(1)
    # retry with backoff — nothing about the request needs changing
except UsageAllocationError as err:
    print("Plan limit hit:", err.reason, err.usage)
```

**`AntibotBlockedError` is not an auth problem either.** a `403` carrying `antibot_blocked`
means the *target site* blocked the request, not that your key was rejected. retrying the same
request rarely helps — use a higher proxy tier (`proxy="advanced"`) or skip the site. both
`scrape` and `map` can return it. only a `403` with an unrecognized name still falls back to
`AuthenticationError`.

**`TooManyRedirectsError` is the target's doing too.** a `422` carrying `too_many_redirects`
means the site redirected the request in a loop, or through more hops than the api follows. it
is not a `ValidationError`, because nothing about your request was wrong. retrying rarely helps.
both `scrape` and `map` can return it.

**`PageTooLargeError` is about the page, not the request.** a `422` carrying `page_too_large`
means the page's html was too large to process. it is not a `ValidationError`, because nothing
about your request was wrong. it is terminal: the same url will fail the same way, so do not
retry it — scrape a smaller page instead. `scrape` returns it; `map` does not.

**`ServiceUnavailableError` is not an auth problem.** a `503` means a piece of our
infrastructure failed while handling your request — the request never reached a verdict
about your key or your page. it is transient and retryable, and **not** a reason to rotate
an api key. a key that is genuinely unknown or expired still comes back as a `401`
`invalid_credentials` (an `AuthenticationError`), which is the only failure worth
re-checking your credentials over.

for exhaustive branching, switch on `err.error_name`. the api docs carry the canonical
[error reference](https://crawlbrulee.com/docs/errors) — every `error_name`, what causes it,
and how to recover.

---

## timeouts

per-call `timeout=` is in **seconds** and overrides the constructor `timeout`; the default
is `None`, so a request has **no ceiling** and a slow page can hang indefinitely — pass
`timeout=` when you need one. a request that exceeds it raises a `TransportError` with
`error_name="request_timeout"`. with the async client, standard asyncio cancellation
applies — cancelling the awaiting task cancels the in-flight request.

(note `wait_for_scrape(timeout=…)` is different — that's the overall polling budget for a
job, not an http timeout.)

---

## notes on the wire format

the sdk mirrors the api's json shapes faithfully. every endpoint — including the
async job **status** response (`job_id`, `created_at`) — is snake_case on the
wire, and the sdk field names match it 1:1.

---

## development

```bash
uv sync                 # or: pip install -e ".[dev]"
ruff check . && ruff format --check .
pyright
pytest
```

the sdk keeps a single runtime dependency (`httpx`) on purpose — please keep it that
way when contributing.

## part of the crawlbrulee toolkit

one api, many ways to call it:

- **[js/ts sdk](https://github.com/crawlbrulee/crawlbrulee-js)** — `@crawlbrulee/sdk`
- **[python sdk](https://github.com/crawlbrulee/crawlbrulee-py)** — `crawlbrulee` on pypi (this one)
- **[cli](https://github.com/crawlbrulee/crawlbrulee-cli)** — `npx crawlbrulee`
- **[mcp server](https://github.com/crawlbrulee/crawlbrulee-mcp)** — `@crawlbrulee/mcp`, for ai agents
- **[agent skills](https://github.com/crawlbrulee/crawlbrulee-skills)** — for skills-aware coding agents

docs: [crawlbrulee.com/docs](https://crawlbrulee.com/docs) · dashboard: [dashboard.crawlbrulee.com](https://dashboard.crawlbrulee.com)

## license

[Apache-2.0](./LICENSE)
