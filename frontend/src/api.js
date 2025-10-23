import { normalizeApiError, normalizeNetworkError } from "./utils/errors.js";

const JSON_HEADERS = { "Content-Type": "application/json" };

export async function getJson(path, options = {}) {
  const url = new URL(path, window.location.origin);
  let response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: JSON_HEADERS,
      ...options,
    });
  } catch (networkError) {
    throw buildNetworkError(networkError);
  }

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw buildError(response, errorBody);
  }

  return response.json();
}

export async function putJson(path, body, options = {}) {
  const url = new URL(path, window.location.origin);
  let response;
  try {
    response = await fetch(url, {
      method: "PUT",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
      ...options,
    });
  } catch (networkError) {
    throw buildNetworkError(networkError);
  }

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw buildError(response, errorBody);
  }

  return response.json();
}

export async function postJson(path, body, options = {}) {
  const url = new URL(path, window.location.origin);
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: JSON_HEADERS,
      body: JSON.stringify(body),
      ...options,
    });
  } catch (networkError) {
    throw buildNetworkError(networkError);
  }

  if (!response.ok) {
    const errorBody = await safeJson(response);
    throw buildError(response, errorBody);
  }

  return response.json();
}

function buildError(response, payload) {
  const normalized = normalizeApiError(response, payload);
  const error = new Error(normalized.message);
  return Object.assign(error, normalized);
}

function buildNetworkError(originalError) {
  const normalized = normalizeNetworkError(originalError);
  const error = new Error(normalized.message);
  return Object.assign(error, normalized);
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}
