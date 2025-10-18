import { getJson } from "./api.js";

const subscribers = new Set();

const state = {
  viewBase: "USD",
  portfolioId: null,
  metrics: {
    value: null,
    pnl: null,
    exposure: null,
    loading: true,
    error: null,
  },
};

export function initState({ defaultPortfolioId, defaultViewBase } = {}) {
  if (defaultPortfolioId) {
    state.portfolioId = defaultPortfolioId;
  }
  if (defaultViewBase) {
    state.viewBase = defaultViewBase;
  }
}

export function getState() {
  return cloneState();
}

export function subscribe(listener) {
  subscribers.add(listener);
  listener(getState());
  return () => subscribers.delete(listener);
}

export async function refreshMetrics() {
  if (!state.portfolioId) {
    return;
  }
  updateState((draft) => {
    draft.metrics.loading = true;
    draft.metrics.error = null;
  });

  try {
    const query = new URLSearchParams({ base: state.viewBase });
    const [value, pnl, exposure] = await Promise.all([
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/value?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/pnl/daily?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/exposure?${query}`),
    ]);
    updateState((draft) => {
      draft.metrics.value = value;
      draft.metrics.pnl = pnl;
      draft.metrics.exposure = exposure;
      draft.metrics.loading = false;
      draft.metrics.error = null;
    });
  } catch (error) {
    updateState((draft) => {
      draft.metrics.loading = false;
      draft.metrics.error = {
        message: error?.message || "Unable to load metrics",
        status: error?.status,
      };
    });
  }
}

export function setViewBase(newBase) {
  if (!newBase || newBase === state.viewBase) {
    return;
  }
  updateState((draft) => {
    draft.viewBase = newBase;
  });
  refreshMetrics();
}

export function setPortfolioId(id) {
  if (!id || id === state.portfolioId) {
    return;
  }
  updateState((draft) => {
    draft.portfolioId = id;
  });
  refreshMetrics();
}

function updateState(mutator) {
  const draft = cloneState();
  mutator(draft);
  state.viewBase = draft.viewBase;
  state.portfolioId = draft.portfolioId;
  state.metrics = { ...draft.metrics };
  notify();
}

function notify() {
  const snapshot = cloneState();
  subscribers.forEach((listener) => listener(snapshot));
}

function cloneState() {
  return {
    viewBase: state.viewBase,
    portfolioId: state.portfolioId,
    metrics: {
      value: state.metrics.value,
      pnl: state.metrics.pnl,
      exposure: state.metrics.exposure,
      loading: state.metrics.loading,
      error: state.metrics.error ? { ...state.metrics.error } : null,
    },
  };
}

