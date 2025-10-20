export function parseUtc(value) {
  if (!value) {
    return null;
  }
  if (value instanceof Date) {
    return value;
  }
  try {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function formatDateTimeLocal(iso, { includeUtcHint = false } = {}) {
  const date = parseUtc(iso);
  if (!date) {
    return "n/a";
  }

  const local = new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);

  if (!includeUtcHint) {
    return local;
  }

  const utcFormatter = new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    timeStyle: "short",
    hourCycle: "h23",
  });
  const utcTime = utcFormatter.format(date);
  return `${local} (UTC ${utcTime})`;
}

export function formatDate(iso, options = {}) {
  const date = parseUtc(iso);
  if (!date) {
    return "n/a";
  }
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    ...options,
  }).format(date);
}
