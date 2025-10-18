const API_ROOT = "/api/v1";
const JSON_HEADERS = { "Content-Type": "application/json" };

export async function getJson(path, options = {}) {
  const url = new URL(path, window.location.origin);
  const response = await fetch(url, {
    method: "GET",
    headers: JSON_HEADERS,
    ...options,
  });

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw buildError(response, errorBody);
  }

  return response.json();
}

export async function postJson(path, body, options = {}) {
  const url = new URL(path, window.location.origin);
  const response = await fetch(url, {
    method: "POST",
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
    ...options,
  });

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw buildError(response, errorBody);
  }

  return response.json();
}

function buildError(response, payload) {
  const error = new Error(payload?.message || response.statusText || "Request failed");
  error.status = response.status;
  error.payload = payload;
  return error;
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}
