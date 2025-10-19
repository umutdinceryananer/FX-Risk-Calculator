import { getJson, postJson } from "./api.js";

export const TIMELINE_DAYS = 30;

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
    timeline: {
      labels: [],
      data: [],
      viewBase: "USD",
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
    const timelineQuery = new URLSearchParams({ base: state.viewBase, days: String(TIMELINE_DAYS) });
    const [value, pnl, exposure, health, timeline] = await Promise.all([
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/value?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/pnl/daily?${query}`),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/exposure?${query}`),
      getJson("/health/rates"),
      getJson(`/api/v1/metrics/portfolio/${state.portfolioId}/value/series?${timelineQuery}`),
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
      draft.charts.timeline = buildTimelineChartData(timeline, TIMELINE_DAYS);
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
  state.charts = {
    exposure: cloneExposureChartData(draft.charts?.exposure),
    timeline: cloneTimelineChartData(draft.charts?.timeline),
  };
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
      timeline: cloneTimelineChartData(state.charts.timeline),
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

function buildTimelineChartData(seriesResponse, days = TIMELINE_DAYS) {
  const viewBase = (seriesResponse?.view_base || state.viewBase || "USD").toUpperCase();
  const rawPoints = Array.isArray(seriesResponse?.series) ? seriesResponse.series : [];

  if (!rawPoints.length || days <= 0) {
    return { viewBase, labels: [], data: [], points: [] };
  }

  const parsedPoints = rawPoints
    .map((point) => {
      const iso = normalizeDateString(point.date);
      if (!iso) {
        return null;
      }
      return {
        date: iso,
        value: toNumber(point.value),
        dateObj: new Date(`${iso}T00:00:00Z`),
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.dateObj - b.dateObj);

  if (!parsedPoints.length) {
    return { viewBase, labels: [], data: [], points: [] };
  }

  const endDate = parsedPoints[parsedPoints.length - 1].dateObj;
  const dayCount = Math.min(Math.max(days, parsedPoints.length), 365);
  const startDate = new Date(endDate);
  startDate.setUTCDate(endDate.getUTCDate() - (dayCount - 1));

  const lookup = new Map(parsedPoints.map((point) => [point.date, point.value]));

  const labels = [];
  const data = [];
  const points = [];

  for (let i = 0; i < dayCount; i += 1) {
    const current = new Date(startDate);
    current.setUTCDate(startDate.getUTCDate() + i);
    const iso = current.toISOString().slice(0, 10);
    labels.push(iso);

    if (lookup.has(iso)) {
      const value = lookup.get(iso);
      data.push(value);
      points.push({ date: iso, value });
    } else {
      data.push(null);
    }
  }

  return { viewBase, labels, data, points };
}

function cloneTimelineChartData(chart) {
  if (!chart) {
    return { viewBase: (state.viewBase || "USD").toUpperCase(), labels: [], data: [], points: [] };
  }
  return {
    viewBase: chart.viewBase,
    labels: Array.isArray(chart.labels) ? [...chart.labels] : [],
    data: Array.isArray(chart.data) ? [...chart.data] : [],
    points: Array.isArray(chart.points) ? chart.points.map((point) => ({ ...point })) : [],
  };
}

function normalizeDateString(value) {
  if (!value) {
    return null;
  }
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return value;
  }
  try {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return null;
    }
    return date.toISOString().slice(0, 10);
  } catch {
    return null;
  }
}

