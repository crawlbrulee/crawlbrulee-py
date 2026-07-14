# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`0.x` releases may
carry breaking changes between minor versions while the API stabilizes).

## [0.6.0] — 2026-07-13

### Changed

- **Screenshots.** In the rare case a screenshot can't be captured, the rest of your
  requested outputs are still returned and the screenshot is simply left out, so
  `page.screenshot` is `None`. `ScrapeResponse.screenshot` was already `Optional`; the
  docstring and README now say so explicitly — guard for it (`page.screenshot and page.screenshot.url`).
- **Custom screenshot viewport is bounded.** `ScreenshotViewport.width`/`height`
  are integers in `[16, 10000]`; `device_scale_factor` is in `[1, 4]` and now
  **accepts fractional values** (type widened from `int` to `float`). Out-of-range
  values are rejected server-side with a `400`. The returned
  `ScreenshotViewportInfo.device_scale_factor` is likewise typed `float`.
- **`extract.images` output.** Image URLs now preserve their query string and
  resolve document-relative `src`s against the full page URL (browser parity) —
  the same rules as the links extractor. Output-only change; `PageInlineImage` is
  unchanged, and its docstring notes the new behavior.

### Docs

- Documented per-plan rate limits with separate sync/async buckets (Free 50/100,
  Starter 100/300, Pro 350/1000, Advanced 1000/3000). Sync `scrape()` and `map()`
  share the sync bucket; `scrape_async()` has its own.

## [0.5.0] — 2026-07-13

### Fixed

- **Async status fields now deserialize correctly.** `AsyncJobStatusResponse.job_id`
  and `.created_at` were being read from the pre-June camelCase wire keys
  (`jobId`, `createdAt`) and came back unset against the live API, which has been
  fully snake_case since 2026-06-13. The SDK now mirrors the snake_case wire 1:1
  (no case mapping). Public attribute names are unchanged, so this is invisible to
  callers — the fields simply populate again.

### Changed

- **Default proxy tier is `auto`.** Docs/type comments now describe the omitted-`proxy`
  default as `auto` (tries the basic tier first, escalates to advanced on failure;
  billed at the delivered tier) instead of `basic`. No behavioral change — the
  client still omits `proxy` when unset and lets the server default apply.
- **API token prefix is `cwbl_`.** Docstring and README examples use the new
  `cwbl_` token prefix (was `cble_`). Existing `cble_` tokens keep authenticating.

## [0.4.0] — 2026-07-03

### Added

- **`response_meta.usage` on every success.** `ScrapeResponse` and `MapResponse`
  now expose a `response_meta.usage` block (`Usage`) with the per-request billing +
  routing details:
  - `credits` — credits charged (`0` on a cache hit).
  - `proxy` — the proxy tier that actually ran (`"none"` / `"basic"` / `"advanced"`).
    This is the **resolved** tier; `"auto"` is decided server-side and is never
    echoed back (`ResolvedProxyTier`).
  - `cache_hit` — whether the result was served from cache.
- **Async status usage.** `AsyncJobStatusResponse` gains an optional `response_meta`
  (`AsyncStatusMeta`) carrying `usage`, present once the job reaches `done`.
- **Webhook usage.** The `scrape.complete` delivery's `data` gains a `response_meta`
  (`ScrapeCompleteWebhookMeta`) carrying `usage` for the finished job.
- New public types: `Usage`, `ResolvedProxyTier`, `ScrapeResponseMeta`,
  `AsyncStatusMeta`, `ScrapeCompleteWebhookMeta`.

## [0.3.0]

- Initial public beta.
