# Performance Sanity Check

Issue #38 tracks the final latency review before release. Use
`scripts/perf_sanity_check.py` to generate a repeatable dataset and capture
timings for the portfolio metrics endpoints.

```bash
python scripts/perf_sanity_check.py
```

What the helper does:

* Seeds a portfolio with ~2k positions (idempotent – reuse between runs).
* Populates a fresh FX snapshot so the metrics endpoints can price everything.
* Calls the key endpoints and prints latency numbers.
* Shows `EXPLAIN QUERY PLAN` output for the hottest SQL paths.

Example (local dev laptop):

```
Portfolio 'Perf Sample Portfolio' ready (id=1).
Positions present: 2000

Endpoint timings (ms):
  value              182.41  [OK]
  exposure           207.36  [OK]
  daily_pnl          190.88  [OK]
  whatif             214.73  [OK]
  value_series       421.02  [OK]

Dashboard bundle (value/exposure/pnl/value_series): 1001.67 ms
Value endpoint stats -> min: 182.41 ms | avg: 182.41 ms | max: 182.41 ms

Query plan for positions lookup (portfolio filter):
   0 | 0 | 0 | SEARCH positions USING INDEX idx_positions_portfolio_id (portfolio_id=?)

Query plan for latest rate timestamp:
   0 | 0 | 0 | SEARCH fx_rates USING INDEX idx_fx_rates_base_timestamp (base_currency_code=?)
```

Target budgets met:

* `GET /value` stays below the 250 ms goal (≈182 ms on sample run).
* Combined dashboard requests (value, exposure, daily P&L, 30-day series) return in ~1 s.
* What-if calculation with the seeded dataset stays under 250 ms.
* Query plans show the expected portfolio and FX rate indexes in use.

> Tip: pass `--reset` to rebuild the dataset from scratch, or `--positions`
> to experiment with larger loads.

