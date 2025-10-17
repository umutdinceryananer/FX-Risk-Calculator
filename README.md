# FX Risk Calculator

Lightweight Flask service scaffold for monitoring FX risk. The project uses an
application factory pattern with environment-driven configuration and modular
blueprints.

## Quick Start
1. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate    # On Windows
   # source .venv/bin/activate # On macOS/Linux
   ```
2. Install dependencies:
   ```bash
   pip install Flask python-dotenv pytest
   ```
3. Copy the sample environment file and adjust values as needed:
   ```bash
   copy .env.example .env
   ```
4. Run the development server:
   ```bash
   python run.py
   ```
   The API will listen on `http://127.0.0.1:5000` by default.

## Configuration
- `APP_ENV` selects the config class (`development` or `production`).
- `DATABASE_URL`, `SECRET_KEY`, `SCHEDULER_TIMEZONE`, and other variables are
  documented in `.env.example`.
- Optional dependency `python-dotenv` auto-loads `.env` when present.
- Database migrations are managed with Alembic. Ensure Alembic is installed and
  run `alembic upgrade head` to apply the latest schema.
- `FX_RATE_PROVIDER` switches between data sources (`mock`, `exchangerate_host`, or `frankfurter_ecb`).
  ExchangeRate.host is keyless; the ECB fallback uses Frankfurter (`FRANKFURTER_API_BASE_URL`).
- `FX_FALLBACK_PROVIDER` optionally selects a secondary provider when the primary fails.
- `REQUEST_TIMEOUT_SECONDS`, `RATES_API_*`, and `FRANKFURTER_API_*` share the unified HTTP client
  (retries with exponential backoff plus jitter).
- `FX_CANONICAL_BASE` defines the stored canonical base (default `USD`); other view bases are computed on demand via rebasing helpers.

- `SCHEDULER_ENABLED` toggles APScheduler integration. `RATES_REFRESH_CRON` sets the cron expression.
- CLI backfill: `flask --app app.cli.backfill backfill-rates --days 30 --base USD`
## Endpoints
- `GET /health` returns general service health information.
- `GET /health/rates` reports the FX rates pipeline status (stubbed as
  `uninitialized` while no scheduler jobs run).

## Testing
Run the smoke test suite with:
```bash
pytest
```

Contract tests for the ExchangeRate.host provider rely on mocked HTTP responses:
```bash
pytest tests/test_exchangerate_provider.py
```

To validate migrations locally:
```bash
pytest tests/migrations
```

### Manual Refresh Endpoint
Trigger an on-demand rates refresh:
```bash
curl -X POST http://127.0.0.1:5000/rates/refresh
```
Scheduler uses APScheduler; disable it via `SCHEDULER_ENABLED=false` or adjust cron with `RATES_REFRESH_CRON`.

## API Documentation
- Swagger UI: http://127.0.0.1:5000/docs/
- OpenAPI spec: http://127.0.0.1:5000/docs/openapi.json

## Portfolio API
- `GET /api/v1/portfolios?page=<page>&page_size=<limit>` lists portfolios with pagination metadata.
- `POST /api/v1/portfolios` creates a portfolio. Example:
  ```bash
  curl -X POST http://127.0.0.1:5000/api/v1/portfolios \
    -H "Content-Type: application/json" \
    -d '{"name":"Global Book","base_currency":"USD"}'
  ```
- `GET /api/v1/portfolios/<id>` retrieves a single portfolio.
- `PUT /api/v1/portfolios/<id>` updates the name and/or base currency.
- `DELETE /api/v1/portfolios/<id>` removes a portfolio and cascades to positions.

Validation rules:
- The `base_currency` must be an ISO-4217 code present in the seeded currency registry; otherwise a 422 response is returned.
- Unknown portfolio identifiers result in 404 responses.

## Position API
- `GET /api/v1/portfolios/<portfolio_id>/positions?page=<page>&page_size=<limit>&currency=<CCY>&side=<LONG|SHORT>` lists positions with optional filters.
- `POST /api/v1/portfolios/<portfolio_id>/positions` creates a position. Example:
  ```bash
  curl -X POST http://127.0.0.1:5000/api/v1/portfolios/1/positions \
    -H "Content-Type: application/json" \
    -d '{"currency_code":"EUR","amount":"2500.00","side":"SHORT"}'
  ```
- `GET /api/v1/portfolios/<portfolio_id>/positions/<position_id>` retrieves a position.
- `PUT /api/v1/portfolios/<portfolio_id>/positions/<position_id>` updates currency, amount, and/or side.
- `DELETE /api/v1/portfolios/<portfolio_id>/positions/<position_id>` removes the position.

Validation rules:
- `currency_code` must be a supported ISO code; otherwise a 422 response is returned.
- `amount` must be a positive decimal string; zero/negative values yield a 422 with a helpful message.
- `side` accepts `LONG` or `SHORT` (case-insensitive).
