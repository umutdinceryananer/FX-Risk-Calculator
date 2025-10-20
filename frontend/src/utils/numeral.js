const DEFAULT_LOCALE = undefined;

export const DECIMAL_PLACES = Object.freeze({
  baseAmount: { min: 2, max: 2 },
  nativeAmount: { min: 4, max: 4 },
  rate: { min: 6, max: 6 },
});

export function coerceNumber(value) {
  if (value === null || value === undefined) {
    return null;
  }
  if (typeof value === "number") {
    return Number.isFinite(value) ? value : null;
  }
  if (typeof value === "bigint") {
    return Number(value);
  }
  const normalized = String(value).replace(/,/g, "").trim();
  if (!normalized) {
    return null;
  }
  const numeric = Number(normalized);
  return Number.isFinite(numeric) ? numeric : null;
}

export function formatDecimal(
  value,
  {
    minimumFractionDigits,
    maximumFractionDigits,
    useGrouping = true,
    fallback = "--",
    signDisplay,
  } = {}
) {
  const numeric = coerceNumber(value);
  if (numeric === null) {
    return fallback;
  }

  const resolvedMax =
    typeof maximumFractionDigits === "number"
      ? maximumFractionDigits
      : typeof minimumFractionDigits === "number"
      ? minimumFractionDigits
      : undefined;

  const options = {
    useGrouping,
  };

  if (typeof minimumFractionDigits === "number") {
    options.minimumFractionDigits = minimumFractionDigits;
  }
  if (typeof resolvedMax === "number") {
    options.maximumFractionDigits = resolvedMax;
  }
  if (signDisplay) {
    options.signDisplay = signDisplay;
  }

  try {
    return new Intl.NumberFormat(DEFAULT_LOCALE, options).format(numeric);
  } catch {
    return basicFormat(numeric, {
      fractionDigits: resolvedMax ?? 2,
      useGrouping,
      signDisplay,
    });
  }
}

export function formatBaseAmount(value, options = {}) {
  return formatDecimal(value, {
    minimumFractionDigits: DECIMAL_PLACES.baseAmount.min,
    maximumFractionDigits: DECIMAL_PLACES.baseAmount.max,
    ...options,
  });
}

export function formatNativeAmount(value, options = {}) {
  return formatDecimal(value, {
    minimumFractionDigits: DECIMAL_PLACES.nativeAmount.min,
    maximumFractionDigits: DECIMAL_PLACES.nativeAmount.max,
    ...options,
  });
}

export function formatRate(value, options = {}) {
  return formatDecimal(value, {
    minimumFractionDigits: DECIMAL_PLACES.rate.min,
    maximumFractionDigits: DECIMAL_PLACES.rate.max,
    ...options,
  });
}

export function formatPercent(
  value,
  { minimumFractionDigits = 2, maximumFractionDigits = 2, signDisplay = "always", ...rest } = {}
) {
  return formatDecimal(value, {
    minimumFractionDigits,
    maximumFractionDigits,
    signDisplay,
    ...rest,
  });
}

export function formatCurrencyAmount(
  value,
  currency,
  {
    minimumFractionDigits = DECIMAL_PLACES.baseAmount.min,
    maximumFractionDigits = DECIMAL_PLACES.baseAmount.max,
    fallback = "--",
    signDisplay,
    useGrouping = true,
  } = {}
) {
  const numeric = coerceNumber(value);
  if (numeric === null) {
    return fallback;
  }

  const normalizedCurrency = (currency || "").toString().trim().toUpperCase();

  const options = {
    style: "currency",
    currency: normalizedCurrency || "USD",
    minimumFractionDigits,
    maximumFractionDigits,
    useGrouping,
  };

  if (signDisplay) {
    options.signDisplay = signDisplay;
  }

  try {
    return new Intl.NumberFormat(DEFAULT_LOCALE, options).format(numeric);
  } catch {
    const formatted = formatDecimal(numeric, {
      minimumFractionDigits,
      maximumFractionDigits,
      useGrouping,
      signDisplay,
      fallback,
    });
    return normalizedCurrency ? `${formatted} ${normalizedCurrency}`.trim() : formatted;
  }
}

export function formatCurrencyNativeAmount(value, currency, options = {}) {
  return formatCurrencyAmount(value, currency, {
    minimumFractionDigits: DECIMAL_PLACES.nativeAmount.min,
    maximumFractionDigits: DECIMAL_PLACES.nativeAmount.max,
    ...options,
  });
}

function basicFormat(value, { fractionDigits = 2, useGrouping, signDisplay }) {
  const sign = value < 0 ? "-" : signDisplay === "always" ? "+" : signDisplay === "never" ? "" : "";
  const absValue = Math.abs(value);
  const fixed = absValue.toFixed(fractionDigits);
  let [integer, fraction] = fixed.split(".");

  if (useGrouping) {
    integer = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  return fraction ? `${sign}${integer}.${fraction}` : `${sign}${integer}`;
}
