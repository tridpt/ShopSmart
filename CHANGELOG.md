# Changelog

All notable changes to ShopSmart are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- GitHub Actions CI running the test suite on every push and pull request.
- MIT `LICENSE` file, `CONTRIBUTING.md`, issue/PR templates, and Dependabot config.

## [0.6.0]

### Added
- Notification settings UI: toggle email alerts and set a Telegram chat id, with
  live channel-availability status.
- Production serving via waitress (`serve.py`, `wsgi.py`) and a standalone
  price-monitor process (`monitor.py`) for multi-worker deployments
  (`PRICE_MONITOR_IN_PROCESS`).

## [0.5.0]

### Added
- Multi-source price comparison (`/api/compare`) — groups offers by source and
  flags the cheapest.
- Track a product directly from the search UI, with an optional target price.
- CSV export of tracked products (UTF-8 BOM for Excel).
- Price-history chart highlights the all-time low/high points.
- Filter and sort controls on the tracking tab; inline target-price editing.

## [0.4.0]

### Added
- Stronger price scraping: official site-API adapter (Tiki), embedded-JSON
  mining for JS-rendered pages, and request retry/backoff.
- Smarter product-name matching for `analyze_price` (accent-insensitive,
  token-overlap scoring, ambiguity detection).
- Short-lived cache and rate limiter for web search to avoid HTTP 429 blocks.

### Fixed
- Search now filters out blog/news/promo URLs and prefers real product pages.
- Stopped falling back to generic CSS selectors on known stores, which could
  return a wrong (too-low) price.

## [0.3.0]

### Added
- Multi-user accounts with JWT auth (bcrypt password hashing); all product,
  chat, and notification data is now scoped per user.
- Real notification delivery via Telegram and SMTP email.
- Test suite (pytest) against an isolated temporary database.

## [0.2.0]

### Added
- Price hardening: noise-resistant VND parsing and price-range validation.
- Background price monitor that periodically re-scrapes tracked products and
  records history.
- Input validation on API endpoints.

### Changed
- Flask debug defaults to off; host/port/debug read from environment.

## [0.1.0]

### Changed
- Migrated from the deprecated `google-generativeai` package to `google-genai`.
- Improved error logging across the agent and tools.
