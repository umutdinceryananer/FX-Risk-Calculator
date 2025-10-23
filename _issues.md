# Project Summary

FX Risk Calculator is a Flask-based backend that stores portfolios and FX positions, pulls normalized exchange-rate data from configurable providers (e.g., ExchangeRate.host), and exposes health/validation endpoints to support FX risk analysis workflows.

# Issue 44: Base selection (UI + API rebase plumbing)

- State: OPEN

- Author: umutdinceryananer

- Labels: backend, frontend, calculations, api, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/44

- Estimate: 3-4h

## Description

Enable switching the portfolio view base from the UI without persisting multi-base rates by rebasing canonical USD snapshots on the fly.

**Acceptance Criteria**

- Backend: provide a `rebase_snapshot(rates_usd, new_base)` helper and use it to serve metrics when `?base=<CCY>` is supplied (default to `portfolio.base`).

- Backend: reject invalid base codes or missing `<new_base>/USD` quotes with a 422 response, and include `{"view_base": "<CCY>", "as_of_date": "<YYYY-MM-DD>"}` in metrics replies.

- Frontend: add a “View in” dropdown (e.g., USD/EUR/GBP/TRY) on the dashboard that refetches value, exposure, P&L, and timeline endpoints with `?base` and remembers the selection in `localStorage`.

**Technical Notes**

- Canonical stored base remains USD (`FX_CANONICAL_BASE`); ECB fallback must normalize to USD before persisting.

- All Decimal math should respect the shared rounding policy.

- Dropdown changes should debounce to avoid excessive refresh traffic.

**Test Notes**

- Backend unit tests covering EUR/GBP/TRY rebasing, invalid base handling, and missing quote failures.

- Frontend tests verifying dropdown selection triggers refetches and persists across reloads.

**Subtasks**

-  Backend rebase helper + validation

-  Metrics endpoint `?base` plumbing

-  Frontend dropdown + persistence

-  Docs/OpenAPI updates

---

# Issue 43: Final review & cleanup

- State: OPEN

- Author: umutdinceryananer

- Labels: meta

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/43

## Description

**Description**  

Polish release: verify health, update docs, close redundant tasks.

**Acceptance Criteria**

- Health endpoints green; demo works end-to-end.

- README & Postman reflect final endpoints.

**Technical Notes**

- Tag a lightweight release in Git.

**Test Notes**

- Manual system test pass.

**Subtasks**

-  Final QA checklist

-  Close issues

### Recommendations

- Add a scripted release gate (e.g., `make release-check`) that runs `pytest`, provider smoke tests, and health checks before tagging.

- Commit the Postman collection with the README update and version it alongside the release tag.

- Provide a small helper (e.g., `scripts/tag_release.py`) to automate creating signed Git tags for repeatable releases.

---

# Issue 42: Environment defaults (Exchange ΓåÆ ECB)

- State: OPEN

- Author: umutdinceryananer

- Labels: infra, docs

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/42

## Description

**Description**  

Default provider order and env validation.

**Acceptance Criteria**

- `.env.example`: `FX_PRIMARY_PROVIDER=exchange`, `FX_FALLBACK_PROVIDER=ecb`.

- App warns on unsupported provider values.

**Technical Notes**

- Single source of truth in `config.py`.

**Test Notes**

- Boot with only Exchange & ECB.

**Subtasks**

-  Env update

-  Config guard

### Recommendations

- Centralize supported provider identifiers in `config.py` and validate env values during boot, logging actionable errors when mismatched.

- Extend `.env.example` with a table summarizing primary/fallback providers, required variables, and behavior.

- Add a unit test that boots with Exchange + ECB values to guard against configuration regressions.

---

# Issue 41: Frontend error states

- State: OPEN

- Author: umutdinceryananer

- Labels: frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/41

## Description

**Description**  

Friendly UX for provider failures/timeouts and validation errors.

**Acceptance Criteria**

- Toasts for network/HTTP errors; retry CTA for refresh.

- Form validation messages inline for CRUD screens.

**Technical Notes**

- Map known codes (422/429/5xx) to friendly messages.

**Test Notes**

- Simulate failures with mocked responses.

**Subtasks**

-  Error handler module

-  UI toasts/messages

### Recommendations

- Ensure backend errors include structured fields (`code`, `message`, optional `retry_after`) so the frontend toast layer can map responses cleanly.

- Build a reusable client-side error utility that converts HTTP status/validation payloads into toast copy and inline form messages.

- Cover timeout, validation failure, and 5xx retry flows in UI tests (Cypress/Playwright) using mocked APIs.

---

# Issue 40: Seed demo portfolio & positions

- State: OPEN

- Author: umutdinceryananer

- Labels: docs, data

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/40

## Description

**Description**  

Add deterministic demo data for first-run experience.

**Acceptance Criteria**

- ΓÇ£Global Book (USD)ΓÇ¥ + 4ΓÇô6 diverse positions (LONG/SHORT, multiple CCYs).

- Idempotent seed (safe to re-run).

**Technical Notes**

- Provide a CLI `seed_demo` command.

**Test Notes**

- Dashboard shows values on first run.

**Subtasks**

-  Seed script

-  README instructions

### Recommendations

- Implement an idempotent `seed_demo` CLI command (e.g., `flask seed demo`) that upserts the portfolio and positions.

- Document the command in a new README "Quick Try" section guiding users through seeding and calling demo endpoints.

- Reuse the seeded portfolio within integration tests to validate risk calculations end-to-end without duplicating fixtures.

---

# Issue 39: Docs: README + Postman + API schema

- State: OPEN

- Author: umutdinceryananer

- Labels: docs

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/39

## Description

**Description**  

Write complete documentation and example requests.

**Acceptance Criteria**

- README: setup, run, seed, scheduler, provider order, stale semantics.

- Postman collection with env variables.

- Link to `/docs` (OpenAPI) and note data attribution (Exchange + ECB).

**Technical Notes**

- Include a troubleshooting section.

**Test Notes**

- New machine walkthrough.

**Subtasks**

-  README

-  Postman JSON

-  API schema export

---

# Issue 38: Performance sanity check

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, performance

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/38

## Description

**Description**  

Ensure endpoints meet basic latency budgets and avoid N+1.

**Acceptance Criteria**

- Value calc < 250 ms for ~2k positions on local dev.

- Dashboard TTFB < 2s.

- Confirm proper indexes are used.

**Technical Notes**

- Add simple timing logs; inspect query plans if needed.

**Test Notes**

- Run with generated data set.

**Subtasks**

-  Timing logs

-  Query/index review

---

# Issue 37: Integration test (E2E happy path)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, testing

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/37

## Description

**Description**  

Spin up app in test mode and verify full flow: Create portfolio ΓåÆ add positions ΓåÆ refresh ΓåÆ metrics ΓåÆ what-if.

**Acceptance Criteria**

- E2E passes using mocked providers (no external calls).

- Response contracts verified; totals sane.

**Technical Notes**

- Use Flask test client + in-memory DB or isolated test DB.

**Test Notes**

- Include fallback scenario (Exchange down ΓåÆ ECB).

**Subtasks**

-  E2E script

-  Mocks & fixtures

---

# Issue 36: Unit tests (module-based)

- State: CLOSED

- Author: umutdinceryananer

- Labels: testing

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/36

## Description

**Description**  

Comprehensive pytest suite for calculations, providers, and CRUD.

**Acceptance Criteria**

- Calculations ΓëÑ90% coverage; overall ΓëÑ80%.

- Provider tests mock HTTP with `responses`.

- Time-dependent tests use `freezegun`.

**Technical Notes**

- Organize tests by module; fixtures for standard payloads.

**Test Notes**

- Edge cases: SHORT signs, shocks, rounding, weekend gaps.

**Subtasks**

-  Calc tests

-  Provider tests

-  CRUD tests

---

# Issue 35: Docker for local development

- State: CLOSED

- Author: umutdinceryananer

- Labels: infra, devx

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/35

## Description

**Description**  

Containerize API + Postgres with `docker compose` for quick setup.

**Acceptance Criteria**

- `docker compose up` starts API + Postgres; app reachable; Alembic auto-migrates.

- Healthchecks for both services.

**Technical Notes**

- Mount code for live reload in development; environment via `.env`.

**Test Notes**

- Fresh machine smoke test.

**Subtasks**

-  Dockerfile

-  docker-compose.yml

-  Healthchecks + Makefile

---

# Issue 34: CI: GitHub Actions (lint + test + coverage badge)

- State: OPEN

- Author: umutdinceryananer

- Labels: infra, ci

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/34

## Description

**Description**  

Run tests/lint in CI with Postgres service; publish coverage badge.

**Acceptance Criteria**

- Workflow runs Python tests (pytest + coverage) and lint; frontend lint.

- Postgres service available; DB URL configured.

- Coverage gate: overall ΓëÑ80%, calc ΓëÑ90%.

- README shows badge.

**Technical Notes**

- Cache Python deps; optional matrix (3.11/3.12).

- Use `services: postgres` with healthcheck.

**Test Notes**

- Dummy PR verifies CI success.

**Subtasks**

-  Workflow YAML

-  Coverage badge in README

---

# Issue 33: Pre-commit hooks + lint + type-check

- State: CLOSED

- Author: umutdinceryananer

- Labels: infra, quality

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/33

## Description

**Description**  

Automate code quality for Python and frontend.

**Acceptance Criteria**

- Python: ruff/flake8, black, isort, mypy configured and passing.

- Frontend: ESLint + Prettier configured and passing.

- `.pre-commit-config.yaml` runs on commit.

**Technical Notes**

- Add Makefile targets: `make lint`, `make typecheck`.

**Test Notes**

- Sample failing commit verified.

**Subtasks**

-  Config files

-  Pre-commit hooks

-  Makefile targets

---

# Issue 32: Structured JSON logging & request correlation

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, infra

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/32

## Description

**Description**  

Add JSON logging with `request_id`, `duration_ms`, and basic provider timing.

**Acceptance Criteria**

- Log fields: `event, route, method, status, duration_ms, request_id, timestamp, source, stale`.

- Request ID generated per request and propagated to logs.

**Technical Notes**

- Python `logging` + JSON formatter; simple middleware for request_id.

**Test Notes**

- Unit tests for log helper; manual inspection.

**Subtasks**

-  JSON formatter

-  Request ID injector

-  Timing decorator

---

# Issue 31: CORS & refresh rate-limit

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, security

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/31

## Description

**Description**  

Allow front-end origin and throttle manual refresh.

**Acceptance Criteria**

- CORS allows `http://localhost:<port>` (configurable).

- `POST /rates/refresh` returns 429 within 60s of last success.

**Technical Notes**

- `Flask-CORS` for allowed origins; in-process timestamp gate.

**Test Notes**

- Preflight OPTIONS handled; 429 path covered.

**Subtasks**

-  CORS config

-  Throttle gate

---

# Issue 30: Rounding & numeral formatting

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, frontend

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/30

## Description

**Description**  

Consistent Decimal rounding and UI formatting policy.

**Acceptance Criteria**

- Rates: 6ΓÇô8 dp; Amounts: 2ΓÇô4 dp.

- UI uses thousands separators and fixed decimal places per field.

**Technical Notes**

- Centralize Decimal context and rounding in calc utils.

- Reuse formatting helpers in frontend.

**Test Notes**

- No float drift; reproducible rounding.

**Subtasks**

-  Rounding policy doc

-  Backend utils

-  UI helpers

---

# Issue 29: UTC consistency

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, frontend

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/29

## Description

**Description**  

Enforce UTC for storage and consistent display formatting.

**Acceptance Criteria**

- DB timestamps in UTC.

- UI shows local time with hint ΓÇ£as of UTCΓÇ¥.

- Helpers for parse/format used everywhere.

**Technical Notes**

- Moment alternatives in vanilla JS (e.g., `Intl.DateTimeFormat`).

**Test Notes**

- DST transitions; Istanbul local display sanity.

**Subtasks**

-  Backend UTC utils

-  UI format helpers

---

# Issue 28: Unpriced policy & error handling

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, frontend

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/28

## Description

**Description**  

Clear user experience for positions without available rates and API errors.

**Acceptance Criteria**

- API responses include `unpriced` count; reasons (unknown currency, missing pair).

- UI badge shows unpriced count; tooltip explains reason(s).

- Toasts for refresh failures and 429 (too frequent refresh).

**Technical Notes**

- Map HTTP codes to human-readable messages.

**Test Notes**

- Unknown currency; ECB missing USD/EUR.

**Subtasks**

-  Backend messaging

-  UI badges/toasts

-  Tests

---

# Issue 27: Positions grid (filter + sort + pagination)

- State: CLOSED

- Author: umutdinceryananer

- Labels: frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/27

## Description

**Description**  

Interactive table for positions with currency/type filters, sort, and pagination.

**Acceptance Criteria**

- Client-side or server-side pagination (choose based on dataset).

- Filters apply instantly; sort by currency/amount/type.

**Technical Notes**

- DataTables.js or custom minimal grid; a11y friendly.

**Test Notes**

- 2k rows responsiveness; keyboard nav.

**Subtasks**

-  Grid component

-  Filters/sort

-  Pagination

---

# Issue 26: Value timeline (30-day)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/26

## Description

**Description**  

Render a time-series line chart for last 30 days of portfolio value.

**Acceptance Criteria**

- Continuous line; missing days are gaps (no markers).

- Hover shows date + value.

**Technical Notes**

- Backend series endpoint computes daily close with stored rates + current positions (MVP).

**Test Notes**

- Date formatting; weekend gaps.

**Subtasks**

-  Backend `/metrics/portfolio/:id/value/series?days=30`

-  Frontend chart

---

# Issue 25: Exposure chart (Top-N + Other

- State: CLOSED

- Author: umutdinceryananer

- Labels: frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/25

## Description

**Description**  

Visualize exposure by currency as bar/pie with tooltips.

**Acceptance Criteria**

- Top-N grouping; an ΓÇ£OtherΓÇ¥ slice when enabled.

- Tooltips show native net and base equivalent.

**Technical Notes**

- Chart.js; lazy data fetch; zero-state handling.

**Test Notes**

- Single vs multi-currency datasets.

**Subtasks**

-  Chart render

-  Legends/tooltips

-  Zero-state

---

# Issue 24: Dashboard KPIs + refresh FX + stale banner

- State: CLOSED

- Author: umutdinceryananer

- Labels: frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/24

## Description

**Description**  

Show KPI cards (Value, Daily P&L, #Positions) and allow manual refresh; display source/stale/last updated.

**Acceptance Criteria**

- Header: `Source: exchange|ecb | Stale: true/false | Last updated: <date>`

- ΓÇ£Refresh FXΓÇ¥ button hits backend; success/failure toasts.

- When stale, show banner with tooltip (ΓÇ£Provider down or weekend/holidayΓÇ¥).

**Technical Notes**

- Debounce button to avoid duplicate clicks.

**Test Notes**

- Simulate failed refresh; confirm banner visibility.

**Subtasks**

-  KPI cards

-  Refresh flow

-  Stale banner

---

# Issue 23: Frontend base layout

- State: CLOSED

- Author: umutdinceryananer

- Labels: frontend, ui

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/23

## Description

**Description**  

Bootstrap 5 shell with navbar and client-side routing for `/dashboard` and `/portfolio`.

**Acceptance Criteria**

- No full page reload between sections (SPA feel).

- Mobile responsive navbar & cards.

**Technical Notes**

- Vanilla JS modules; fetch API wrappers; minimal state store.

**Test Notes**

- Chrome/Firefox/Edge smoke; mobile viewport.

**Subtasks**

-  Layout + navbar

-  Router (hash or History API)

-  Fetch helpers

---

# Issue 22: Metrics: what-if (single currency shock)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, calculations

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/22

## Description

**Description**  

Simulate a ┬▒10% shock in one currency and return impact.

**Acceptance Criteria**

- `POST /api/v1/metrics/portfolio/:id/whatif` with `{currency, shock_pct}` in [-10, 10].

- Returns `{delta_value, new_value, shocked_currency}`.

- Validation errors for out-of-range, unknown currency, or empty portfolio.

- Support an optional `?base=<CCY>` parameter so the what-if result is expressed in the requested view base and the response reports `view_base` and `as_of_date`.

**Technical Notes**

- Decimal-safe; only selected currency revalued.

**Test Notes**

- Positive/negative shocks; SHORT interactions.

**Subtasks**

-  Endpoint + validation

-  Tests

---

# Issue 21: Metrics: daily P&L

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, calculations

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/21

## Description

**Description**  

Compute P&L between today (or latest) and previous available day; flag if positions changed.

**Acceptance Criteria**

- `GET /api/v1/metrics/portfolio/:id/pnl/daily` ΓåÆ `{pnl, as_of_date, prev_date, positions_changed}`.

- Weekends/holidays handled (previous available day).

- `positions_changed` checks if composition changed since `prev_date` (basic heuristic).

- Support an optional `?base=<CCY>` parameter so the P&L is expressed in the requested view base and the response reports `view_base` and `as_of_date`.

**Technical Notes**

- Basic change detection: compare counts/sums per currency and type.

**Test Notes**

- Missing days; DST/UTC safeguards.

**Subtasks**

-  Snapshot logic

-  Endpoint

-  Tests

---

# Issue 20: Metrics: exposure by currency

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, calculations

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/20

## Description

**Description**  

Aggregate exposure per currency with optional top-N and ΓÇ£OtherΓÇ¥ grouping.

**Acceptance Criteria**

- `GET /api/v1/metrics/portfolio/:id/exposure?top_n=5`

- For each currency: `net` (native) & `base_equiv`; sorted by `abs(base_equiv)` desc.

- Optional ΓÇ£OtherΓÇ¥ bucket.

- Support an optional `?base=<CCY>` parameter so exposure values are returned in the requested view base with `view_base` and `as_of_date` alongside the totals.

**Technical Notes**

- Respect LONG/SHORT sign; ignore unpriced in base_equiv.

**Test Notes**

- LONG/SHORT mixes; ties; top-N correctness.

**Subtasks**

-  Aggregation service

-  Endpoint + params

-  Tests

---

# Issue 19: Metrics: portfolio value

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, calculations

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/19

## Description

**Description**  

Compute aggregate portfolio value in base currency.

**Acceptance Criteria**

- `GET /api/v1/metrics/portfolio/:id/value` ΓåÆ `{value_base, value, priced, unpriced}`.


- Unpriced positions excluded from total; `unpriced` count returned.
- Support an optional `?base=<CCY>` parameter (default portfolio base) that returns values in the requested view base and includes `view_base` and `as_of_date` in the response.

**Technical Notes**

- Use latest available daily snapshot (by `as_of_date`).

**Test Notes**

- Mixed priced/unpriced; rounding verified.

**Subtasks**

-  Service + endpoint

-  Tests

---

# Issue 18: Conversion utils (base conversion & LONG/SHORT sign)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, calculations

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/18

## Description

**Description**  

Pure functions to convert native amounts to base using a rates snapshot and handle sign for LONG/SHORT.

**Acceptance Criteria**

  - If `pos_ccy==base`, no lookup.

  - LONG positive, SHORT negative contribution.

  - Deterministic with given snapshot dict.

  - Provide a `rebase_snapshot(rates_usd: dict, new_base: str) -> dict` helper with Decimal-safe calculations and shared rounding.

**Technical Notes**

- One `Decimal` context (ROUND_HALF_EVEN, adequate precision).

- No floats anywhere.

**Test Notes**

- ΓëÑ90% coverage for this module; edge cases around rounding.

**Subtasks**

-  Utils

-  Unit tests

---

# Issue 17: Position CRUD API

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/17

## Description

**Description**  

Manage positions under a given portfolio with pagination and filtering.

**Acceptance Criteria**

- `POST/GET/PUT/DELETE /api/v1/portfolios/:id/positions`.

- Pagination (`page`,`page_size`), filter by `currency`, `type`.

- 422 if `amount<=0` or invalid currency; 404 for missing portfolio.

**Technical Notes**

- Store `type` as ENUM; Decimal parsing robust.

**Test Notes**

- Large numbers precision; pagination boundaries.

**Subtasks**

-  Endpoints + query params

-  Schemas & validation

-  Tests

---

# Issue 16: Portfolio CRUD API

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/16

## Description

**Description**  

REST endpoints to create/read/update/delete portfolios with base currency validation.

**Acceptance Criteria**

- `POST/GET/PUT/DELETE /api/v1/portfolios` implemented.

- 422 on invalid base CCY; 404 on unknown ID; clear error messages.

- Deleting a portfolio cascades to positions.

**Technical Notes**

- Prefer marshmallow schemas for validation; serialize Decimal safely.

**Test Notes**

- Happy path + invalid ISO + unknown ID + delete cascade.

**Subtasks**

-  Endpoints

-  Schemas & errors

-  Tests

---

# Issue 15: OpenAPI schema & interactive docs

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, docs, api

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/15

## Description

**Description**  

Generate and serve `/openapi.json` + `/docs` (Swagger UI).

  **Acceptance Criteria**

  - Every endpoint has request/response schemas + examples.

  - `/docs` renders; schema is valid (linted).

  - README links to `/docs`.

  - Metrics endpoints document an optional `?base=USD|EUR|...` query parameter (defaulting to the portfolio base) with examples for both default and explicit bases.

**Technical Notes**

- `flask-smorest` or `apispec` + marshmallow; reusable error schema.

**Test Notes**

- Contract smoke test: required fields present.

**Subtasks**

-  Schemas & examples

-  Swagger UI mount

-  Schema lint

---

# Issue 14: Rates backfill (30-day history)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, data

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/14

## Description

**Description**  

Backfill last 30 days for allowed currency set; idempotent inserts.

**Acceptance Criteria**

- Idempotent inserts; avoids duplicates.

- Completeness checks for the last 30 days.

- Backfills canonical base (USD) only; other view-bases are derived at read time.    

**Technical Notes**

- Keep inserts batched for performance (e.g., `executemany`).

**Test Notes**

- Completeness check; duplicate prevention.

**Subtasks**

-  Service + CLI

-  Tests for idempotency

---

# Issue 13: Scheduler & manual refresh endpoint

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, scheduling

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/13

## Description

**Description**  

Run APScheduler hourly; provide manual refresh `POST /api/v1/rates/refresh` with 60s throttle.

**Acceptance Criteria**

- Job calls orchestrator and UPSERTs latest rates.

- Manual hits are rejected with 429 if called within 60s of previous success.

- Only one scheduler instance runs (main-process guard).

- Scheduler fetches only canonical base (USD); no multi-base writes.

**Technical Notes**

- Use `if __name__ == "__main__"` guard; or an env flag `SCHEDULER_ENABLED=true`.

- Manual refresh does not accept base; it always refreshes canonical snapshot.

**Test Notes**

- Trigger job in tests; verify DB writes and headers in response.

**Subtasks**

-  APScheduler wiring

-  Refresh endpoint

-  Throttle state (in-process)

---

# Issue 12: HTTP client wrapper (timeouts/retries/backoff/jitter)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, infra

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/12

## Description

**Description**  

Centralize HTTP behaviors for providers.

**Acceptance Criteria**

- Default timeout=5s; retries=2; exponential backoff with jitter.

- Respect 429/5xx; do not retry on 4xx (except 429).

- Uniform exceptions with `code`, `status`, `message`.

**Technical Notes**

- Requests `Session` with `HTTPAdapter` + retry strategy; jitter via random factor.

**Test Notes**

- Simulate 429 with Retry-After; 5xx sequences.

**Subtasks**

-  Client wrapper

-  Error types

-  Tests

---

# Issue 11: Provider orchestration & stale cache

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, resiliency

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/11

## Description

**Description**  

Try Exchange ΓåÆ ECB; if both fail, return last known snapshot with `stale=true`.

**Acceptance Criteria**

- Orchestrator picks primary; on failure tries fallback; else uses last snapshot.

- `/health/rates` returns `{source, last_updated, stale}`.

- Log provider timings (ms).

- Orchestrator persists only canonical base (USD) rates. If source is ECB (EUR-base), convert to USD before persist.

**Technical Notes**

- In-memory last-known snapshot cache + persisted DB latest.

- Keep last-known-good USD-based snapshot in memory + DB. All UI view-bases are computed on demand.

**Test Notes**

- Simulated primary failure; both failure ΓåÆ stale fallback; verify health output.

**Subtasks**

-  Orchestrator service

-  Health wiring

-  Simple timing logs

---

# Issue 10: Fallback provider: ECB/Frankfurter (+ cross-rate)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, api

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/10

## Description

**Description**  

Implement ECB fallback; compute non-EUR base via cross-rate.

**Acceptance Criteria**

- For USD base: `A/USD = (A/EUR) / (USD/EUR)` within tolerance (e.g., 1e-6).

- Providers return normalized snapshots; orchestrator can rebase snapshots to any view base using helper, without hitting DB.

- Handle weekend/holiday gaps (missing days).

- Return `source='ecb'`.

**Technical Notes**

- Use daily series endpoints; if USD/EUR missing for date, skip that date or mark unpriced.

- Add rebase_snapshot(snapshot, new_base) utility:

A/new_base = (A/USD) / (new_base/USD) using canonical USD snapshot.

**Test Notes**

- Cross-rate numeric verification; gap handling.

**Subtasks**

-  Frankfurter client

-  Cross-rate util

-  Tests

---

# Issue 5: Primary provider: Fixer.io integration

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, api

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/5

## Description

**Description:** Fetch latest and historical FX rates from Fixer.io (or equivalent).

- **Acceptance Criteria**

    - `get_latest("USD")` returns timestamped rates for allowed symbols.

    - `get_history("USD","EUR",30)` returns daily series.

    - Proper headers, API key, and error handling.

- **Technical Notes**

    - Respect provider base currency limitations and quotas.

    - Map provider response to normalized schema.

- **Test Notes**

    - Use HTTP mocking (responses/httpretty) and VCR-style fixtures.

- **Subtasks**

    -  Implement client with retries/backoff.

    -  Map responses, handle errors/timeouts.

---

# Issue 4: FX provider abstraction interface

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, api

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/4

## Description

**Description:** Design provider interface to standardize real data access.

  - **Acceptance Criteria**

      - Interface methods: `get_latest(base:str)->{source, timestamp, rates{CCY:rate}}`, `get_history(base, symbol, days)->series`.

      - All providers return normalized payloads.

      - Providers return normalized snapshots that the orchestrator can rebase to any view base without writing new records.

  - **Technical Notes**

      - Add provider registry and selection via env.

      - Add a reusable `rebase_snapshot(snapshot, new_base)` utility where `A/new_base = (A/USD) / (new_base/USD)` using the canonical USD snapshot.

  - **Test Notes**

      - Contract tests for normalized output.

- **Subtasks**

    -  Define interface and dataclasses.

    -  Provider registry and factory.

---

# Issue 3: ISO-4217 currency reference & validation

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, data

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/3

## Description

**Description:** Seed reference currencies and add server-side validation.

- **Acceptance Criteria**

    - `currencies` table populated with common codes (USD, EUR, GBP, JPY, TRY, CHF, AUD, CAD, ΓÇª).

    - API rejects non-ISO codes with helpful 422 message.

- **Technical Notes**

    - Maintain allowlist in DB, load on boot into in-memory set.

- **Test Notes**

    - Positive/negative validation tests.

- **Subtasks**

    -  Seed script for `currencies`.

    -  Validation middleware/helpers.

---

# Issue 2: Database models & Alembic migrations (core)

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, db

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/2

## Description

**Description:** Implement `currencies`, `fx_rates`, `portfolios`, `positions` with indexes and constraints.

- **Acceptance Criteria**

    - Alembic `upgrade`/`downgrade` runs cleanly.

    - Uniqueness: `currencies.code` and `(base_currency, target_currency, timestamp, source)` upsert key for `fx_rates`.

    - Proper FKs: `positions.portfolio_id ΓåÆ portfolios.id`.

- **Technical Notes**

    - Indexes:

        - `fx_rates(base_currency, target_currency, timestamp desc)`

        - `positions(portfolio_id, currency)`

    - Decimal precision: `fx_rates.rate DECIMAL(18,8)`; `positions.amount DECIMAL(20,4)`.

- **Test Notes**

    - Migration smoke test on empty DB.

- **Subtasks**

    -  Define SQLAlchemy models.

    -  Generate initial migration.

    -  Add composite unique/indices.

---

# Issue 1: Project scaffolding & configuration

- State: CLOSED

- Author: umutdinceryananer

- Labels: backend, infra, docs

- Assignees: umutdinceryananer

- URL: https://github.com/umutdinceryananer/FX-Risk-Calculator/issues/1

## Description

**Description:** Create Flask app factory, base structure, environment config, and health endpoints.

- **Acceptance Criteria**

    - App factory pattern works; `run.py` starts server.

    - `.env.example` exists and documents required variables.

    - `/health` and `/health/rates` return 200 (rates can be ΓÇ£uninitializedΓÇ¥).

- **Technical Notes**

    - Packages: Flask, SQLAlchemy, Alembic, Pydantic (or marshmallow), Requests, APScheduler.

    - Config classes: Development/Production; read from env

- **Test Notes**

    - Smoke test for `/health`.

- **Subtasks**

    -  Create `app/__init__.py` with factory and blueprints.

    -  Add `config.py` and `.env.example`.

    -  Implement `/health` and `/health/rates` (stub).

    -  Update `README` quick start.

---
