# changelog

all notable changes to the `crawlbrulee` python sdk are documented here.

this project follows [Semantic Versioning](https://semver.org). while on `0.x`, minor versions may include breaking changes.

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
