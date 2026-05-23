# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradFi is a Python value-investing tool with three surfaces sharing one backend:
1. **CLI** (`tradfi ...`) — Typer-based commands for analyze/screen/quarterly/list/compare.
2. **TUI** (`tradfi ui`) — Textual app for browsing/screening.
3. **Web + REST API** (`tradfi api`, deployed to Railway) — FastAPI server with HTMX/Jinja web frontend at `/` and JSON API at `/api/v1/*`.

## Architecture

### Remote-first CLI/TUI

The CLI and TUI **do not fetch yfinance data directly**. They call the hosted API at `TRADFI_API_URL` (defaults to `https://deepv-production.up.railway.app`) via `core/remote_provider.py` (persistent `httpx.Client` with connection pooling). Only the server-side code (`core/data.py`) talks to yfinance. When testing screening/analysis logic locally without a running API, you need to either run `tradfi api` in a separate terminal or point `TRADFI_API_URL` at a local server.

### Deployment entry point

- `server.py` (repo root) imports `tradfi.api.main:app` and is what `Procfile` / `nixpacks.toml` / `railway.json` boot via `uvicorn server:app`. The bare `src/tradfi/api.py` file is **legacy** — the live app lives in `src/tradfi/api/main.py`.
- `api/main.py` mounts: API routers under `/api/v1` (stocks, screening, lists, watchlist, cache, refresh, currency, users), web routes (Jinja templates under `templates/`), static files from `static/`, an APScheduler lifespan that runs `api/scheduler.py:refresh_universe` daily, and `SecurityHeadersMiddleware` + optional CORS.

### Auth model (two tiers)

- **User auth** (`web/auth_routes.py`, `api/routers/users.py`): passwordless email magic links → session tokens stored in `auth_tokens` table; `get_current_user` dependency validates `Authorization: Bearer <token>`.
- **Admin auth** (`api/auth.py:require_admin_key`): `X-Admin-Key` header compared via `hmac.compare_digest` to `TRADFI_ADMIN_KEY`. Required for cache clear, refresh trigger, and user registration. If unset, admin endpoints return 403 unless `TRADFI_ADMIN_DEV_MODE=1`.

### Cache layer

- SQLite at `~/.tradfi/cache.db` (override via `TRADFI_DATA_DIR` or `TRADFI_DB_PATH` for cloud deployments).
- `utils/cache.py` (~2400 LOC) is the single source of truth: stock cache w/ TTL, watchlist, saved lists, list categories, list item notes/positions, smart lists, users, and auth tokens. Connections use `check_same_thread=False`; a `ttl_cache` decorator memoizes aggregate queries (stats, sectors) to avoid hammering SQLite.
- `DEFAULT_CACHE_TTL` is 24h (`TRADFI_CACHE_TTL` env override).

### Screening pipeline

- `core/screener.py` defines `ScreenCriteria` (dataclass of nullable filter knobs) and a streamlined `PRESET_SCREENS` of **7 presets**: `graham`, `buffett`, `dividend`, `fallen-angels`, `hidden-gems`, `oversold`, `turnaround`. `PRESET_INFO` carries display strings used by the UI — keep both dicts in sync when adding presets.
- `AVAILABLE_UNIVERSES` maps universe names to ticker files under `data/` (40+ files: US indexes, ETFs, plus per-country/region for ~35 international markets). Some files (e.g. `etf.txt`) use `# Category` headers parsed by `load_tickers_with_categories`.
- `core/valuation.py` computes Graham number, DCF, EPV, and P/E fair value; `core/technical.py` computes RSI / SMA / 52w metrics. Both are called from `core/data.py` when building a `Stock`.

## Source layout

```
src/tradfi/
├── cli.py                  # Typer root; registers commands + `ui` / `api` / `serve`
├── api.py                  # LEGACY - do not extend; use api/main.py
├── commands/               # CLI command modules (analyze, screen, quarterly, compare, lists, watchlist, cache)
├── core/
│   ├── data.py             # yfinance fetch + Stock construction (server-side only)
│   ├── remote_provider.py  # HTTP client used by CLI/TUI
│   ├── screener.py         # PRESET_SCREENS, AVAILABLE_UNIVERSES, load_tickers
│   ├── valuation.py        # Graham/DCF/EPV/PE fair value
│   ├── technical.py        # RSI, SMA, 52w
│   ├── quarterly.py        # 8-quarter trend analysis
│   ├── portfolio.py        # P&L aggregation for list positions
│   ├── currency.py         # FX conversion for international universes
│   └── research.py         # SEC filings via OPENROUTER_API_KEY or ANTHROPIC_API_KEY
├── api/
│   ├── main.py             # FastAPI app, middleware, lifespan, router mounts
│   ├── auth.py             # require_admin_key dependency
│   ├── scheduler.py        # APScheduler daily refresh
│   ├── schemas.py          # Pydantic request/response models
│   ├── converters.py       # Stock dataclass <-> Pydantic dicts
│   └── routers/            # cache, currency, lists, refresh, screening, stocks, users, watchlist
├── web/                    # Jinja/HTMX web frontend (routes, auth_routes, partials, template_helpers)
├── tui/app.py              # Textual app
├── utils/cache.py          # SQLite layer + auth tokens (single ~2400 LOC file)
├── models/stock.py         # Stock dataclass + nested ETFMetrics, ValuationMetrics, etc.
├── static/, templates/     # Web assets
└── tests/                  # pytest suite at repo root /tests
```

## Commands

```bash
pip install -e ".[dev]"           # install with dev deps (pytest, ruff)

# CLI (hits remote API by default)
tradfi analyze AAPL
tradfi screen --preset graham
tradfi quarterly AAPL --periods 12
tradfi compare longs shorts
tradfi list ls | create | add | remove | note | long | short | category
tradfi watchlist ...
tradfi cache status | prefetch sp500 --delay 5 | clear
tradfi ui                         # launches Textual TUI
tradfi api --port 8000 --reload   # runs api/main.py via uvicorn
tradfi serve --port 8000          # legacy alias

# Tests / lint
pytest
pytest tests/test_screener.py             # single file
pytest tests/test_screener.py::test_name  # single test
pytest -k "graham"                        # by keyword
ruff check . && ruff format .
```

## Environment variables

| Var | Purpose |
|-----|---------|
| `TRADFI_API_URL` | Remote API endpoint for CLI/TUI (default: hosted Railway URL) |
| `TRADFI_ADMIN_KEY` | Server-side admin key + client `X-Admin-Key` for destructive ops |
| `TRADFI_ADMIN_DEV_MODE` | `1` to allow admin endpoints without a key (local dev only) |
| `TRADFI_DEV_MODE` | `1` to return magic-link tokens in HTTP responses (else email-only) |
| `TRADFI_DATA_DIR` / `TRADFI_DB_PATH` | Override SQLite location (cloud deploys) |
| `TRADFI_CACHE_TTL` | Cache TTL in seconds (default 86400) |
| `TRADFI_CORS_ORIGINS` | `*` for dev, comma-separated origins for prod, unset = no CORS |
| `TRADFI_REFRESH_HOUR` / `TRADFI_REFRESH_UNIVERSES` / `TRADFI_REFRESH_ENABLED` | Daily refresh config |
| `OPENROUTER_API_KEY` / `ANTHROPIC_API_KEY` | Deep research (SEC filings); auto-detected |

## Conventions & gotchas

- **All public functions need type annotations** (enforced by reviewer expectation, not by mypy in CI).
- **yfinance fields can return `None`** — every metric on `Stock` is `Optional`; treat `None` as "not available" rather than 0, and never assume completeness.
- **Rate limiting**: yfinance tolerates ~360 req/hr. `core/data.py` enforces a `_last_request_time` gap; `api/scheduler.py` scales `delay` based on universe size (>500 tickers ⇒ ≥3s).
- **Keep `PRESET_SCREENS` and `PRESET_INFO` in sync** — they're separate dicts in `core/screener.py`.
- **`utils/cache.py` is a single large module** with both per-user and legacy global tables. New persistence usually means adding columns/tables here, not creating new files.
- **Don't add yfinance calls to CLI/TUI code paths.** Anything that fetches market data belongs behind the API; CLI/TUI go through `RemoteDataProvider`.
- **Reconnaissance rule**: before non-trivial features, find 2 similar examples in the repo and follow that pattern.

## Self-Improvement

Claude maintains this file:
- **On correction**: add a concise rule under `## Learned Rules` to prevent the class of mistake.
- **On pattern discovery**: extend the relevant section above.
- **On failure recovery**: document the fix under `## Conventions & gotchas`.
- **Keep it lean**: this file should not exceed ~300 lines; delete stale rules.

Cross-session notes live in `/root/.claude/projects/-home-user-tradfi/memory/MEMORY.md`. Create topic-specific files (e.g. `yfinance-gotchas.md`, `tui-patterns.md`) for detailed notes and link them from MEMORY.md.

## Learned Rules

_Auto-maintained. Add rules when mistakes are corrected._
