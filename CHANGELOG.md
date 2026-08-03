# changelog

all notable changes to the `crawlbrulee` python sdk are documented here.

this project follows [Semantic Versioning](https://semver.org). while on `0.x`, minor versions may include breaking changes.

## 0.10.0 (2026-08-03)

### removed (breaking)

- **`overage_hard_cap` is no longer part of `UsageAllocationReason`.** the api used to return two
  reason codes for one condition: `credit_limit` when a plan had no headroom, `overage_hard_cap`
  when it did. they were mutually exclusive by plan — no org could ever see both — and meant the
  same thing to you: no credits left, refused until the cycle resets, same status and same remedy.
  they are now reported as `credit_limit` for every plan.

  if you branch on `overage_hard_cap`, fold that branch into your `credit_limit` case. type
  checkers will flag comparisons against the removed literal, which is the intended prompt to look.

## 0.9.0 (2026-07-28)

### fixed

- **`ScrapeResponse.requested_url` — the field finally reaches you.** the api sends
  `requested_url` (the url you requested, echoed verbatim — before any redirects) on every
  scrape success, but the sdk's deserializer drops keys its models don't declare, so the field
  was silently unreachable at runtime. it is now a required field on `ScrapeResponse`, on both
  the sync `scrape()` response and the async `get_scrape_result()` / `wait_for_scrape()` result.
- `__version__` (and the user-agent built from it) had drifted — 0.8.0 shipped still reporting
  `0.7.0`. both now track the release version again.

### added

- **`unsupported_screenshot_output`** joins `ApiErrorName`, and `create_api_error` maps it to
  `ValidationError` — the same class as `unsupported_content`. raised as a `422` when a
  screenshot was the *only* requested output and the content type can't be screenshotted.

### changed (docs)

- **screenshot failure contract, stated precisely.** the "rest of your outputs still arrive and
  `page.screenshot` is `None`" behavior only applies when other outputs were requested. a
  screenshot-**only** request that can't deliver fails instead — `422`
  `unsupported_screenshot_output` when the content type can't be screenshotted, `500` on a
  capture failure — and isn't billed.
- **cache billing wording.** `credits` is `0` on a *fully* cached result; only parts still
  computed fresh (e.g. a newly produced screenshot-slice variant) are charged. `cache_hit`
  no longer claims a cache hit always costs `0`.
- **link semantics documented.** `PageLink.href` is the link as written on the page, resolved
  to an absolute url — verbatim otherwise (query string, fragment, and duplicates preserved);
  non-http(s) hrefs are dropped. `PageLink.internal` means same domain, where `www` and the
  bare domain count as the same and other subdomains are external.
- `ScrapeResponse.url` is documented more precisely: the url actually scraped, after any
  redirects, in cleaned canonical form (tracking params and fragment removed) — the base that
  `links`, `images`, and `internal` labels are computed against.

## 0.8.0 (2026-07-27)

### removed

- **`ScrapeCache.ignore_query_params` is gone**, because the api no longer accepts it — `cache` is
  strict, so a request carrying the field is rejected. `max_age` is now the only cache control.
  if you were setting it, drop it and send the url you actually want cached: every non-tracking
  query parameter is part of the cache key, so ``https://example.com/page`` and
  ``https://example.com/page?ref=x`` are separate entries.

### changed

- the ``url`` field is documented more precisely: known tracking parameters (``utm_*``, ``mtm_*``,
  ``ga_*``, ``pk_*``, ``gclid``, ``fbclid``, ``msclkid``, and more) are removed before the page is
  fetched, so they reach neither the target site nor the cache key. every other query parameter is
  kept verbatim.

## 0.7.0 (2026-07-15)

### changed

- **proxy tier types now match the supported API surface.** `ProxyTier` is
  `Literal["basic", "advanced", "auto"]` and `ResolvedProxyTier` is
  `Literal["basic", "advanced"]`. this is a type-only change — no runtime behaviour is
  affected, and any value outside these was already rejected by the api.

## 0.6.0 (2026-07-14)

### changed

- **screenshots.** in the rare case a screenshot can't be captured, we still return the rest of
  your requested outputs and leave out the screenshot, so `page.screenshot` is `None`.
  `ScrapeResponse.screenshot` was already `Optional`; the docstring and README now say so
  explicitly — guard with `page.screenshot and page.screenshot.url`.
- **custom screenshot viewport is bounded.** `ScreenshotViewport.width`/`height` are integers in
  `[16, 10000]`; `device_scale_factor` is in `[1, 4]` and now **accepts fractional values** (type
  widened from `int` to `float`). out-of-range values are rejected with a `400`. the returned
  `ScreenshotViewportInfo.device_scale_factor` is likewise typed `float`.
- **`extract.images` output.** image urls now preserve their query string and resolve
  document-relative `src`s against the full page url (browser parity) — the same rules as the
  links extractor. output-only change; `PageInlineImage` is unchanged, and its docstring notes
  the new behavior.

## 0.5.0 (2026-07-13)

### fixed

- **async status fields now deserialize correctly.** `AsyncJobStatusResponse.job_id` and
  `.created_at` were being read from the pre-June camelCase wire keys (`jobId`, `createdAt`) and
  came back unset against the live snake_case api. the sdk now mirrors the snake_case wire 1:1
  (no case mapping). public attribute names are unchanged, so this is invisible to callers — the
  fields simply populate again.

### changed (docs)

- default proxy tier is now `auto` (tries the basic tier first, escalates to advanced on failure;
  billed at the delivered tier) instead of `basic`. docstring-only — the client still omits
  `proxy` when unset and lets the server apply the default.

## 0.4.0 (2026-07-03)

### added

- **`response_meta.usage` on every success.** `ScrapeResponse` and `MapResponse` now expose a
  `response_meta.usage` block (`Usage`) with the per-request billing + routing details:
  - `credits` — credits charged (`0` on a cache hit).
  - `proxy` — the proxy tier that actually ran (`"basic"` / `"advanced"`). this is the
    **resolved** tier; `"auto"` is decided server-side and is never echoed back
    (`ResolvedProxyTier`).
  - `cache_hit` — whether the result was served from cache.
- **async status usage.** `AsyncJobStatusResponse` gains an optional `response_meta`
  (`AsyncStatusMeta`) carrying `usage`, present once the job reaches `done`.
- **webhook usage.** the `scrape.complete` delivery's `data` gains a `response_meta`
  (`ScrapeCompleteWebhookMeta`) carrying `usage` for the finished job.
- new public types: `Usage`, `ResolvedProxyTier`, `ScrapeResponseMeta`, `AsyncStatusMeta`,
  `ScrapeCompleteWebhookMeta`.

## 0.3.0 (2026-06-15)

### added

- initial public beta.
