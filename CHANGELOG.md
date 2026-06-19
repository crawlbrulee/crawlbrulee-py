# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`0.x` releases may
carry breaking changes between minor versions while the API stabilizes).

## [Unreleased]

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
