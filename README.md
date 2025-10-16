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
  ExchangeRate.host is keyless; the ECB fallback uses Frankfurter (`FRANKFURTER_API_BASE_URL`, retries/backoff).
- `FX_CANONICAL_BASE` defines the stored canonical base (default `USD`); other view bases are computed on demand via rebasing helpers.

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
