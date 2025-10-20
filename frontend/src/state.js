import { getJson, postJson } from "./api.js";

export const TIMELINE_DAYS = 30;

const POSITION_SORT_FIELDS = ["currency", "amount", "side", "created_at"];
const POSITION_DIRECTION_VALUES = ["asc", "desc"];
const POSITION_SIDE_VALUES = ["LONG", "SHORT"];
const POSITIONS_DEFAULTS = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 25,
  currency: "",
  side: "",
  sort: "created_at",
  direction: "asc",
  loading: false,
  error: null,
};

let positionsRequestToken = 0;

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
  positions: {
    items: [],
    total: 0,
    page: 1,
    pageSize: 25,
    currency: "",
    side: "",
    sort: "created_at",
    direction: "asc",
    loading: false,
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
    await refreshPositions();
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
    draft.positions = clonePositionsState(POSITIONS_DEFAULTS);
  });
  refreshData();
  refreshPositions({ resetPage: true });
}

export async function refreshPositions({ resetPage = false } = {}) {
  if (!state.portfolioId) {
    return;
  }

  const requestToken = ++positionsRequestToken;

  updateState((draft) => {
    if (resetPage) {
      draft.positions.page = 1;
    }
    draft.positions.loading = true;
    draft.positions.error = null;
  });

  const queryString = buildPositionsQueryParams();

  try {
    const result = await getJson(
      `/api/v1/portfolios/${state.portfolioId}/positions?${queryString}`
    );
    if (requestToken !== positionsRequestToken) {
      return;
    }
    updateState((draft) => {
      draft.positions.items = Array.isArray(result?.items)
        ? result.items.map((item) => ({ ...item }))
        : [];
      draft.positions.total = toPositiveInteger(result?.total) || 0;
      draft.positions.page = toPositiveInteger(result?.page) || draft.positions.page;
      const serverPageSize =
        toPositiveInteger(result?.page_size ?? result?.pageSize) || draft.positions.pageSize;
      draft.positions.pageSize = serverPageSize;
      draft.positions.loading = false;
      draft.positions.error = null;
    });
  } catch (error) {
    if (requestToken !== positionsRequestToken) {
      return;
    }
    updateState((draft) => {
      draft.positions.loading = false;
      draft.positions.error = {
        message: error?.message || "Unable to load positions",
        status: error?.status,
      };
    });
  }
}

export function setPositionsPage(page) {
  const nextPage = toPositiveInteger(page);
  if (!nextPage || nextPage === state.positions.page) {
    return;
  }
  updateState((draft) => {
    draft.positions.page = nextPage;
  });
  refreshPositions();
}

export function setPositionsPageSize(pageSize) {
  const nextSize = Math.min(toPositiveInteger(pageSize) || state.positions.pageSize, 200);
  if (!nextSize || nextSize === state.positions.pageSize) {
    return;
  }
  updateState((draft) => {
    draft.positions.pageSize = nextSize;
    draft.positions.page = 1;
  });
  refreshPositions();
}

export function setPositionsSort(sort, direction) {
  const normalizedSort = normalizeSortField(sort);
  if (!normalizedSort) {
    return;
  }

  let nextDirection = normalizeSortDirection(direction);
  if (!nextDirection) {
    if (normalizedSort === state.positions.sort) {
      nextDirection = state.positions.direction === "asc" ? "desc" : "asc";
    } else {
      nextDirection = "asc";
    }
  }

  if (
    normalizedSort === state.positions.sort &&
    nextDirection === state.positions.direction
  ) {
    return;
  }

  updateState((draft) => {
    draft.positions.sort = normalizedSort;
    draft.positions.direction = nextDirection;
    draft.positions.page = 1;
  });
  refreshPositions();
}

export function setPositionsFilters({ currency, side } = {}) {
  const normalizedCurrency = normalizeCurrencyFilter(currency);
  const normalizedSide = normalizeSideFilter(side);

  if (
    normalizedCurrency === state.positions.currency &&
    normalizedSide === state.positions.side
  ) {
    return;
  }

  updateState((draft) => {
    draft.positions.currency = normalizedCurrency;
    draft.positions.side = normalizedSide;
    draft.positions.page = 1;
  });
  refreshPositions({ resetPage: true });
}

export function clearPositionsFilters() {
  setPositionsFilters({ currency: "", side: "" });
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
  state.positions = clonePositionsState(draft.positions);
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
    positions: clonePositionsState(state.positions),
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

function clonePositionsState(source) {
  const base = source || POSITIONS_DEFAULTS;
  return {
    items: Array.isArray(base.items) ? base.items.map((item) => ({ ...item })) : [],
    total: toPositiveInteger(base.total),
    page: toPositiveInteger(base.page) || POSITIONS_DEFAULTS.page,
    pageSize: Math.min(toPositiveInteger(base.pageSize) || POSITIONS_DEFAULTS.pageSize, 200),
    currency: normalizeCurrencyFilter(base.currency),
    side: normalizeSideFilter(base.side),
    sort: normalizeSortField(base.sort) || POSITIONS_DEFAULTS.sort,
    direction: normalizeSortDirection(base.direction) || POSITIONS_DEFAULTS.direction,
    loading: Boolean(base.loading),
    error: base.error ? { ...base.error } : null,
  };
}

function buildPositionsQueryParams() {
  const params = new URLSearchParams({
    page: String(state.positions.page),
    page_size: String(state.positions.pageSize),
    sort: state.positions.sort || POSITIONS_DEFAULTS.sort,
    direction: state.positions.direction || POSITIONS_DEFAULTS.direction,
  });

  if (state.positions.currency) {
    params.set("currency", state.positions.currency);
  }
  if (state.positions.side) {
    params.set("side", state.positions.side);
  }

  return params.toString();
}

function normalizeSortField(value) {
  if (!value) {
    return null;
  }
  const normalized = String(value).trim().toLowerCase().replace(/[\s-]+/g, "_");
  if (normalized === "createdat") {
    return "created_at";
  }
  if (POSITION_SORT_FIELDS.includes(normalized)) {
    return normalized;
  }
  return null;
}

function normalizeSortDirection(value) {
  if (!value) {
    return null;
  }
  const normalized = String(value).trim().toLowerCase();
  if (POSITION_DIRECTION_VALUES.includes(normalized)) {
    return normalized;
  }
  return null;
}

function normalizeCurrencyFilter(value) {
  if (!value) {
    return "";
  }
  const normalized = String(value).trim().toUpperCase();
  if (/^[A-Z]{3}$/.test(normalized)) {
    return normalized;
  }
  return "";
}

function normalizeSideFilter(value) {
  if (!value) {
    return "";
  }
  const normalized = String(value).trim().toUpperCase();
  if (POSITION_SIDE_VALUES.includes(normalized)) {
    return normalized;
  }
  return "";
}

function toPositiveInteger(value) {
  if (value === 0) {
    return 0;
  }
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return 0;
  }
  if (numeric <= 0) {
    return 0;
  }
  return Math.floor(numeric);
}

