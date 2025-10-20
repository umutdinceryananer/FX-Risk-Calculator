# Rounding & Formatting Policy

This project uses Decimal math everywhere we perform financial calculations.
To keep results predictable, every component should follow the same rules:

- **Rates** (FX quotes, conversion factors): keep **6 to 8 decimal places**.
- **Monetary amounts** (position sizes, portfolio values, P&L): show **2 to 4 decimal places**.
- **Thousands separators** must be applied anywhere values are shown in the UI.
- All arithmetic should rely on the shared `get_decimal_context()` helper so the precision and rounding mode stay consistent.

## Decimal Context

The global context is configured in `app/services/fx_conversion.py`:

```python
context.prec = 28
context.rounding = ROUND_HALF_EVEN
```

Any new service or helper should call `get_decimal_context()` (or use a convenience wrapper) before doing Decimal math to avoid drift.

## Backend Expectations

When returning data from the API:

- Quantize rates to 6 or 8 decimal places (`Decimal("0.000001")` or `Decimal("0.00000001")` depending on the source).
- Quantize amounts to 2 or 4 decimal places (`Decimal("0.01")` or `Decimal("0.0001")`), depending on the business field.
- Always convert to strings when serialising decimals in JSON to preserve exact precision.

Persisted database values should follow the same policy, using the existing Numeric column definitions (`DECIMAL(18, 8)` for rates, `DECIMAL(20, 4)` for amounts).

## Frontend Expectations

The UI must mirror the backend rules:

- Use the shared number-format helper (`frontend/src/utils/numberFormat.js`, to be added) so thousand separators and decimal counts are consistent.
- Do not rely on locale defaults for precision; explicitly pass the required number of decimal digits.

## Testing

Add tests whenever you introduce new calculations or formatting to make sure:

- Decimal operations honour the shared context (no float comparisons).
- API responses emit values with the expected number of decimal places.
- UI formatting helpers produce the correct string given representative numbers.

Keeping this policy in sync across backend and frontend avoids “off by one cent” bugs and keeps the UX consistent.
