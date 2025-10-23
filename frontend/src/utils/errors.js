const STATUS_TITLES = {
  400: "Request Error",
  401: "Authentication Required",
  403: "Access Denied",
  404: "Not Found",
  409: "Conflict",
  422: "Validation Error",
  429: "Slow Down",
  500: "Unexpected Error",
  502: "Provider Error",
  503: "Service Unavailable",
  504: "Timeout",
};

const STATUS_MESSAGES = {
  400: "Request could not be processed.",
  404: "Resource not found.",
  422: "Submitted data is invalid.",
  429: "Too many requests. Please try again shortly.",
  502: "Upstream provider unavailable.",
  503: "Service temporarily unavailable. Please retry in a moment.",
};

export function normalizeApiError(response, payload = null) {
  const status = response?.status ?? 0;
  const title = STATUS_TITLES[status] || (status >= 500 ? "Server Error" : "Request Error");
  const message =
    (payload && payload.message) ||
    response?.statusText ||
    STATUS_MESSAGES[status] ||
    "Request failed.";

  return {
    status,
    title,
    message,
    code: payload?.code ?? null,
    retryAfter: parseRetryAfter(payload, response),
    fieldErrors: extractFieldErrors(payload),
    details: payload ?? null,
    response,
    isValidationError: status === 422,
    isThrottled: status === 429,
    isNetworkError: false,
  };
}

export function normalizeNetworkError(error) {
  const title = "Network Error";
  const message = "Unable to reach FX Risk Calculator. Check your connection and retry.";
  return {
    status: 0,
    title,
    message,
    code: null,
    retryAfter: null,
    fieldErrors: {},
    details: { message: error?.message },
    response: null,
    isValidationError: false,
    isThrottled: false,
    isNetworkError: true,
  };
}

export function parseRetryAfter(payload, response) {
  if (payload && typeof payload.retry_after !== "undefined") {
    const value = Number(payload.retry_after);
    if (!Number.isNaN(value) && value >= 0) {
      return value;
    }
  }

  const headerValue = response?.headers?.get?.("Retry-After");
  if (headerValue) {
    const value = Number(headerValue);
    if (!Number.isNaN(value) && value >= 0) {
      return value;
    }
  }

  return null;
}

export function extractFieldErrors(payload) {
  if (!payload || typeof payload !== "object") {
    return {};
  }

  const possible = payload.errors || payload.field_errors || payload.validationErrors;
  if (possible && typeof possible === "object") {
    return possible;
  }

  return {};
}
