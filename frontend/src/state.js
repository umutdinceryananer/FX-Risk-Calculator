import { getJson, postJson } from "./api.js";

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
  health: {
    data: null,
    loading: true,
    error: null,
  },
  refresh: {
    loading: false,
    error: null,
  },
  charts: {
    exposure: {
      labels: [],
      datasets: [],
    },
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

export async function refreshData() {
  if (!state.portfolioId) {
    return;
  }

  updateState((draft) => {
    draft.metrics.loading = true;
    draft.metrics.error = null;
    draft.health.loading = true;
    draft.health.error = null;
  });

  try {
    const query = new URLSearchParams({ base: state.viewBase });
    const [value, pnl, exposure, health] = await Promise.all([
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/value?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/pnl/daily?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/exposure?${query}`),
      getJson("/health/rates"),
    ]);

    updateState((draft) => {
      draft.metrics.value = value;
      draft.metrics.pnl = pnl;
      draft.metrics.exposure = exposure;
      draft.metrics.loading = false;
      draft.metrics.error = null;

      draft.health.data = health;
      draft.health.loading = false;
      draft.health.error = null;
      draft.refresh.error = null;

      draft.charts.exposure = buildExposureChartData(exposure);
    });
  } catch (error) {
    updateState((draft) => {
      draft.metrics.loading = false;
      draft.metrics.error = {
        message: error?.message || "Unable to load metrics",
        status: error?.status,
      };

      draft.health.loading = false;
      draft.health.error = {
        message: error?.message || "Unable to load health status",
        status: error?.status,
      };
      draft.refresh.error = {
        message: error?.message || "Unable to refresh data",
        status: error?.status,
      };
    });
  }
}

export async function triggerManualRefresh() {
  if (state.refresh.loading) {
    return { ok: false, message: "Refresh already in progress." };
  }

  updateState((draft) => {
    draft.refresh.loading = true;
    draft.refresh.error = null;
  });

  try {
    const response = await postJson("/rates/refresh", {});
    await refreshData();
    updateState((draft) => {
      draft.refresh.loading = false;
    });
    return { ok: true, message: response?.message || "Refresh triggered." };
  } catch (error) {
    updateState((draft) => {
      draft.refresh.loading = false;
      draft.refresh.error = {
        message: error?.message || "Unable to refresh FX rates.",
        status: error?.status,
      };
    });
    return { ok: false, message: error?.message || "Unable to refresh FX rates." };
  }
}

export function setViewBase(newBase) {
  if (!newBase || newBase === state.viewBase) {
    return;
  }
  updateState((draft) => {
    draft.viewBase = newBase;
  });
  refreshData();
}

export function setPortfolioId(id) {
  if (!id || id === state.portfolioId) {
    return;
  }
  updateState((draft) => {
    draft.portfolioId = id;
  });
  refreshData();
}

function updateState(mutator) {
  const draft = cloneState();
  mutator(draft);
  state.viewBase = draft.viewBase;
  state.portfolioId = draft.portfolioId;
  state.metrics = { ...draft.metrics };
  state.health = { ...draft.health };
  state.refresh = { ...draft.refresh };
  state.charts = { exposure: cloneExposureChartData(draft.charts?.exposure) };
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
    health: {
      data: state.health.data ? { ...state.health.data } : null,
      loading: state.health.loading,
      error: state.health.error ? { ...state.health.error } : null,
    },
    refresh: {
      loading: state.refresh.loading,
      error: state.refresh.error ? { ...state.refresh.error } : null,
    },
    charts: {
      exposure: cloneExposureChartData(state.charts.exposure),
    },
  };
}

function buildExposureChartData(exposure) {
  const viewBase = (exposure?.view_base || state.viewBase || "USD").toUpperCase();
  const exposures = Array.isArray(exposure?.exposures) ? exposure.exposures : [];
  const palette = buildPalette(exposures.length);

  const items = exposures.map((item, index) => ({
    label: item.currency_code,
    baseValue: toNumber(item.base_equivalent),
    nativeValue: toNumber(item.net_native),
    nativeCurrency: item.currency_code,
    color: palette[index] || "#94a3b8",
  }));

  return { items, viewBase };
}

function buildPalette(count) {
  const baseColors = [
    "#2563eb",
    "#10b981",
    "#f59e0b",
    "#f97316",
    "#8b5cf6",
    "#ec4899",
    "#22d3ee",
  ];

  if (count <= baseColors.length) {
    return baseColors.slice(0, count);
  }

  const colors = [];
  for (let i = 0; i < count; i += 1) {
    const hue = Math.floor((360 / Math.max(count, 1)) * i);
    colors.push(`hsl(${hue} 70% 55%)`);
  }
  return colors;
}

function toNumber(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function cloneExposureChartData(chart) {
  if (!chart) {
    return { viewBase: (state.viewBase || "USD").toUpperCase(), items: [] };
  }
  return {
    viewBase: chart.viewBase,
    items: Array.isArray(chart.items) ? chart.items.map((item) => ({ ...item })) : [],
  };
}

