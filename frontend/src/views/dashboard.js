import { subscribe, setViewBase, triggerManualRefresh, TIMELINE_DAYS } from "../state.js";
import { showToast } from "../ui/toast.js";
import {
  prepareExposureDataset,
  renderPreparedExposureChart,
  destroyExposureChart,
  DEFAULT_EXPOSURE_TOP_N,
} from "../charts/exposure.js";
import { renderTimelineChart, destroyTimelineChart } from "../charts/timeline.js";

const REFRESH_DEBOUNCE_MS = 600;

export function renderDashboardView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = template();

  const baseSelect = root.querySelector("[data-view-base]");
  const refreshButton = root.querySelector("[data-refresh-button]");
  const metricCards = Array.from(root.querySelectorAll("[data-metric-card]"));
  const banner = root.querySelector("[data-stale-banner]");
  const healthSummary = root.querySelector("[data-health-summary]");
  const sourceNode = root.querySelector("[data-health-source]");
  const staleNode = root.querySelector("[data-health-stale]");
  const updatedNode = root.querySelector("[data-health-updated]");
  const exposureCanvas = root.querySelector("[data-exposure-chart]");
  const exposureZeroState = root.querySelector("[data-exposure-zero-state]");
  const exposureTopNLabel = root.querySelector("[data-exposure-topn]");
  const exposureToggle = root.querySelector("[data-exposure-full-toggle]");
  const exposureList = root.querySelector("[data-exposure-list]");
  const timelineCanvas = root.querySelector("[data-timeline-chart]");
  const timelineZeroState = root.querySelector("[data-timeline-zero-state]");
  const timelineSummary = root.querySelector("[data-timeline-summary]");
  const tooltipInstance = initStaleTooltip(root);

  let refreshDebounceTimer = null;
  let showFullExposure = false;
  let lastExposureChartState = null;
  let lastTimelineChartState = null;

  baseSelect.addEventListener("change", (event) => {
    setViewBase(event.target.value);
  });

  refreshButton.addEventListener("click", async () => {
    if (refreshDebounceTimer) {
      return;
    }
    refreshDebounceTimer = setTimeout(() => {
      refreshDebounceTimer = null;
    }, REFRESH_DEBOUNCE_MS);

    const result = await triggerManualRefresh();
    showToast({
      title: result.ok ? "Refresh queued" : "Refresh failed",
      message: result.message,
      variant: result.ok ? "success" : "danger",
    });
  });

  if (exposureToggle) {
    exposureToggle.addEventListener("click", () => {
      if (!lastExposureChartState || !Array.isArray(lastExposureChartState.items)) {
        return;
      }
      if (lastExposureChartState.items.length <= DEFAULT_EXPOSURE_TOP_N) {
        return;
      }
      showFullExposure = !showFullExposure;
      updateExposureChart(lastExposureChartState);
    });
  }

  const unsubscribe = subscribe((state) => {
    if (baseSelect.value !== state.viewBase) {
      baseSelect.value = state.viewBase;
    }

    renderRefreshButton(refreshButton, state.refresh);
    renderMetrics(metricCards, state.metrics);
    renderBanner(banner, state.metrics, state.health, tooltipInstance);
    renderHealthSummary({
      container: healthSummary,
      sourceNode,
      staleNode,
      updatedNode,
      health: state.health,
    });

    lastExposureChartState = state.charts.exposure;
    updateExposureChart(lastExposureChartState);

    lastTimelineChartState = state.charts.timeline;
    updateTimelineChart(lastTimelineChartState);
  });

  return () => {
    if (typeof unsubscribe === "function") {
      unsubscribe();
    }
    if (tooltipInstance) {
      tooltipInstance.dispose();
    }
    destroyExposureChart();
    destroyTimelineChart();
  };

  function updateExposureChart(chartState) {
    if (!exposureCanvas) {
      return;
    }

    const totalItems = Array.isArray(chartState?.items) ? chartState.items.length : 0;
    const canExpand = totalItems > DEFAULT_EXPOSURE_TOP_N;
    if (!canExpand && showFullExposure) {
      showFullExposure = false;
    }

    const desiredTop = showFullExposure ? totalItems || DEFAULT_EXPOSURE_TOP_N : DEFAULT_EXPOSURE_TOP_N;
    const prepared = prepareExposureDataset(chartState, desiredTop);
    const hasData = prepared.data.labels.length > 0;

    if (!hasData) {
      destroyExposureChart();
      setExposureZeroState(true);
      renderExposureList(exposureList, null);
      if (exposureTopNLabel) {
        exposureTopNLabel.textContent = "0";
      }
      if (exposureToggle) {
        exposureToggle.disabled = true;
        exposureToggle.setAttribute("aria-disabled", "true");
        exposureToggle.textContent = "Show full list";
        exposureToggle.setAttribute("aria-pressed", "false");
      }
      return;
    }

    setExposureZeroState(false);

    if (exposureTopNLabel) {
      const segmentCount = prepared.meta.segments.length;
      const topCount = showFullExposure ? segmentCount : Math.min(DEFAULT_EXPOSURE_TOP_N, segmentCount);
      exposureTopNLabel.textContent = showFullExposure ? "All" : String(topCount);
    }

    if (exposureToggle) {
      exposureToggle.disabled = !canExpand;
      exposureToggle.setAttribute("aria-disabled", canExpand ? "false" : "true");
      const defaultLabel = `Show top ${Math.min(DEFAULT_EXPOSURE_TOP_N, prepared.meta.segments.length)}`;
      exposureToggle.textContent = showFullExposure ? defaultLabel : "Show full list";
      exposureToggle.setAttribute("aria-pressed", showFullExposure ? "true" : "false");
    }

    renderPreparedExposureChart(exposureCanvas, prepared);
    renderExposureList(exposureList, prepared.meta);
  }

  function setExposureZeroState(visible) {
    if (!exposureZeroState) {
      return;
    }
    if (visible) {
      exposureZeroState.classList.remove("d-none");
      exposureZeroState.classList.add("d-flex");
      exposureZeroState.setAttribute("aria-hidden", "false");
      if (exposureList) {
        exposureList.classList.add("d-none");
        exposureList.setAttribute("aria-hidden", "true");
      }
    } else {
      exposureZeroState.classList.add("d-none");
      exposureZeroState.classList.remove("d-flex");
      exposureZeroState.setAttribute("aria-hidden", "true");
      if (exposureList) {
        exposureList.classList.remove("d-none");
        exposureList.setAttribute("aria-hidden", "false");
      }
    }
  }

  function renderExposureList(container, meta) {
    if (!container) {
      return;
    }

    if (!meta || !Array.isArray(meta.segments) || meta.segments.length === 0) {
      container.innerHTML = "";
      container.classList.add("d-none");
      container.setAttribute("aria-hidden", "true");
      return;
    }

    container.classList.remove("d-none");
    container.setAttribute("aria-hidden", "false");

    const items = meta.segments.map((segment) => {
      const toneClass =
        segment.baseValue < 0 ? "text-danger" : segment.baseValue > 0 ? "text-success" : "text-body";
      const baseLine = `<strong class="${toneClass}">${formatCurrency(segment.baseValue, meta.viewBase)}</strong>`;

      const nativeLine =
        segment.nativeCurrency != null && segment.nativeCurrency !== ""
          ? `<small>Native (${segment.nativeCurrency}): ${formatCurrency(segment.nativeValue, segment.nativeCurrency)}</small>`
          : "";

      const breakdownLine =
        Array.isArray(segment.constituents) && segment.constituents.length > 0
          ? `<small>Includes ${segment.constituents.length} ${
              segment.constituents.length === 1 ? "currency" : "currencies"
            }</small>`
          : "";

      return `
        <li>
          <span class="exposure-label">${segment.label}</span>
          <span class="exposure-values">
            ${baseLine}
            ${nativeLine}
            ${breakdownLine}
          </span>
        </li>
      `;
    });

    container.innerHTML = items.join("");
  }

  function updateTimelineChart(chartState) {
    if (!timelineCanvas) {
      return;
    }

    const hasData =
      chartState &&
      Array.isArray(chartState.labels) &&
      chartState.labels.length > 0 &&
      Array.isArray(chartState.data) &&
      chartState.data.some((value) => value !== null);

    if (!hasData) {
      destroyTimelineChart();
      setTimelineZeroState(true);
      renderTimelineSummary(timelineSummary, null);
      return;
    }

    setTimelineZeroState(false);
    renderTimelineSummary(timelineSummary, chartState);
    renderTimelineChart(timelineCanvas, chartState);
  }

  function setTimelineZeroState(visible) {
    if (!timelineZeroState) {
      return;
    }
    if (visible) {
      timelineZeroState.classList.remove("d-none");
      timelineZeroState.classList.add("d-flex");
      timelineZeroState.setAttribute("aria-hidden", "false");
    } else {
      timelineZeroState.classList.add("d-none");
      timelineZeroState.classList.remove("d-flex");
      timelineZeroState.setAttribute("aria-hidden", "true");
    }
  }

  function renderTimelineSummary(container, chartState) {
    if (!container) {
      return;
    }

    if (!chartState || !Array.isArray(chartState.points) || chartState.points.length === 0) {
      container.textContent = `Last ${TIMELINE_DAYS} days`;
      return;
    }

    const firstPoint = chartState.points[0];
    const latestPoint = chartState.points[chartState.points.length - 1];
    const rangeText = `${formatShortDateLabel(firstPoint.date)} -> ${formatShortDateLabel(latestPoint.date)}`;
    const latestValue = formatCurrency(latestPoint.value, chartState.viewBase);
    container.textContent = `${rangeText} | Latest ${latestValue}`;
  }

  function formatShortDateLabel(iso) {
    if (!iso) {
      return "--";
    }
    try {
      const date = new Date(`${iso}T00:00:00Z`);
      return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return iso;
    }
  }
}

function template() {
  return `
    <section class="mb-4">
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-3">
        <div>
          <h1 class="h3 mb-1 fw-semibold">Portfolio Overview</h1>
          <p class="text-muted mb-0">Track value, P&L, and exposure across currencies.</p>
        </div>
        <div class="d-flex flex-column align-items-md-end gap-2">
          <div class="d-flex align-items-center gap-3 justify-content-end flex-wrap text-muted small" data-health-summary>
            <span>Source: <span class="fw-semibold text-body" data-health-source>--</span></span>
            <span>Stale: <span class="fw-semibold text-body" data-health-stale>--</span></span>
            <span>Last updated: <span class="fw-semibold text-body" data-health-updated>--</span></span>
          </div>
          <div class="d-flex align-items-center gap-3">
            <div class="d-flex align-items-center gap-2">
              <label class="text-muted small mb-0">View in</label>
              <select class="form-select form-select-sm shadow-sm" data-view-base>
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="GBP">GBP</option>
                <option value="TRY">TRY</option>
              </select>
            </div>
            <button class="btn btn-primary shadow-sm d-flex align-items-center gap-2" type="button" data-refresh-button>
              <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true" data-refresh-spinner></span>
              <i class="bi bi-arrow-clockwise" data-refresh-icon></i>
              <span data-refresh-label>Refresh FX</span>
            </button>
          </div>
        </div>
      </header>

      <div class="alert alert-warning d-none" role="alert" data-stale-banner>
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-exclamation-triangle-fill"></i>
          <span>Provider currently stale. Using last available snapshot.</span>
          <i class="bi bi-info-circle" data-stale-tooltip tabindex="-1" data-bs-toggle="tooltip" title="Provider down or weekend/holiday"></i>
        </div>
      </div>

      <div class="row g-4">
        ${[
          { key: "value", title: "Portfolio Value" },
          { key: "pnl", title: "Daily P&L" },
          { key: "exposure", title: "# Positions" },
        ]
          .map(renderMetricSkeleton)
          .join("")}
      </div>
    </section>

    <section class="mb-5">
      <div class="card border-0">
        <div class="card-body p-4">
          <div class="row g-4">
            <div class="col-12 col-xl-6">
              <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
                <div>
                  <h2 class="h5 mb-0">Value Timeline</h2>
                  <p class="text-muted small mb-0" data-timeline-summary>Last ${TIMELINE_DAYS} days</p>
                </div>
              </div>
              <div class="chart-area">
                <div class="ratio ratio-16x9">
                  <canvas data-timeline-chart></canvas>
                </div>
                <div
                  class="chart-zero-state d-none flex-column align-items-center justify-content-center text-muted small"
                  data-timeline-zero-state
                  aria-hidden="true"
                >
                  <p class="fw-semibold mb-1">No timeline data yet</p>
                  <p class="mb-0">Collect rate snapshots to visualize trends.</p>
                </div>
              </div>
            </div>
            <div class="col-12 col-xl-6">
              <div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
                <div>
                  <h2 class="h5 mb-0">Exposure by Currency</h2>
                  <p class="text-muted small mb-0">Net exposure expressed in base equivalent.</p>
                </div>
                <div class="d-flex align-items-center gap-2 small text-muted">
                  <span>Top <span data-exposure-topn>${DEFAULT_EXPOSURE_TOP_N}</span> currencies</span>
                  <span class="text-body-secondary">|</span>
                  <button class="btn btn-link btn-sm p-0" type="button" data-exposure-full-toggle>Show full list</button>
                </div>
              </div>
              <div class="chart-area">
                <div class="ratio ratio-1x1">
                  <canvas data-exposure-chart></canvas>
                </div>
                <div
                  class="chart-zero-state d-none flex-column align-items-center justify-content-center text-muted small"
                  data-exposure-zero-state
                  aria-hidden="true"
                >
                  <p class="fw-semibold mb-1">No exposure data yet</p>
                  <p class="mb-0">Add positions to see currency exposure.</p>
                </div>
              </div>
              <ul class="exposure-list text-muted small d-none" data-exposure-list aria-hidden="true"></ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderMetricSkeleton({ key, title }) {
  return `
    <div class="col-12 col-md-6 col-xl-4">
      <div class="card h-100 kpi-card" data-metric-card="${key}">
        <div class="card-body p-4">
          <p class="text-muted text-uppercase fw-semibold small mb-2">${title}</p>
          <div class="placeholder-glow">
            <span class="placeholder col-7 display-6 d-block"></span>
          </div>
          <p class="text-muted small mt-3 mb-0">Loading data...</p>
        </div>
      </div>
    </div>
  `;
}

function renderMetrics(cardNodes, metrics) {
  cardNodes.forEach((card) => {
    const metricKey = card.getAttribute("data-metric-card");
    const body = card.querySelector(".card-body");

    if (metrics.loading) {
      body.innerHTML = `
        <p class="text-muted text-uppercase fw-semibold small mb-2">${titleFor(metricKey)}</p>
        <div class="placeholder-glow">
          <span class="placeholder col-7 display-6 d-block"></span>
        </div>
        <p class="text-muted small mt-3 mb-0">Refreshing data...</p>
      `;
      return;
    }

    if (metrics.error) {
      body.innerHTML = `
        <p class="text-muted text-uppercase fw-semibold small mb-2">${titleFor(metricKey)}</p>
        <p class="text-danger fw-semibold">Unable to load metrics</p>
        <p class="text-muted small mb-0">${metrics.error.message || "Please try again later."}</p>
      `;
      return;
    }

    const content = metrics[metricKey];
    if (!content) {
      body.innerHTML = `
        <p class="text-muted text-uppercase fw-semibold small mb-2">${titleFor(metricKey)}</p>
        <p class="text-muted">No data available.</p>
      `;
      return;
    }

    body.innerHTML = metricMarkup(metricKey, content);
  });
}

function metricMarkup(key, payload) {
  switch (key) {
    case "value": {
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2">Portfolio Value</p>
        <div class="metric-value display-6 mb-2">${formatCurrency(payload.value, payload.view_base)}</div>
        <p class="text-muted metric-footnote mb-1">Priced: ${payload.priced} / Unpriced: ${payload.unpriced}</p>
        <p class="text-muted metric-footnote mb-0">As of ${formatAsOf(payload.as_of)}</p>
      `;
    }
    case "pnl": {
      const pnlNumber = Number(payload.pnl || 0);
      const toneClass = pnlNumber < 0 ? "text-danger" : pnlNumber > 0 ? "text-success" : "text-body";
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2">Daily P&L</p>
        <div class="metric-value display-6 mb-1 ${toneClass}">
          ${formatCurrency(payload.pnl, payload.view_base)}
        </div>
        <p class="text-muted metric-footnote mb-1">Prev value: ${formatCurrency(payload.value_previous ?? "0", payload.view_base)}</p>
        <p class="text-muted metric-footnote mb-0">As of ${formatAsOf(payload.as_of)}</p>
      `;
    }
    case "exposure": {
      const priced = Number(payload.priced || 0);
      const unpriced = Number(payload.unpriced || 0);
      const totalPositions = priced + unpriced;
      const uniqueCurrencies = Array.isArray(payload.exposures) ? payload.exposures.length : 0;
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2"># Positions</p>
        <div class="metric-value display-6 mb-2">${totalPositions}</div>
        <p class="text-muted metric-footnote mb-1">Priced positions: ${priced}</p>
        <p class="text-muted metric-footnote mb-1">Awaiting pricing: ${unpriced}</p>
        <p class="text-muted metric-footnote mb-0">Tracked currencies: ${uniqueCurrencies}</p>
      `;
    }
    default:
      return "";
  }
}

function renderBanner(bannerNode, metrics, health, tooltipInstance) {
  if (!bannerNode) {
    return;
  }

  const isStale =
    Boolean(health?.data?.stale) ||
    Boolean(metrics.value && metrics.value.priced === 0 && !metrics.loading && !metrics.error);

  bannerNode.classList.toggle("d-none", !isStale);

  const trigger = bannerNode.querySelector("[data-stale-tooltip]");
  if (trigger && tooltipInstance) {
    trigger.setAttribute("tabindex", isStale ? "0" : "-1");
    if (isStale) {
      tooltipInstance.enable();
    } else {
      tooltipInstance.disable();
    }
  }
}

function renderRefreshButton(button, refreshState) {
  if (!button) {
    return;
  }

  const spinner = button.querySelector("[data-refresh-spinner]");
  const icon = button.querySelector("[data-refresh-icon]");
  const label = button.querySelector("[data-refresh-label]");
  const loading = Boolean(refreshState?.loading);

  button.disabled = loading;
  if (spinner) {
    spinner.classList.toggle("d-none", !loading);
  }
  if (icon) {
    icon.classList.toggle("d-none", loading);
  }
  if (label) {
    label.textContent = loading ? "Refreshing..." : "Refresh FX";
  }
}

function renderHealthSummary({ container, sourceNode, staleNode, updatedNode, health }) {
  if (!container) {
    return;
  }

  if (health.loading) {
    container.classList.add("text-muted");
    container.classList.remove("text-danger");
    updateText(sourceNode, "Loading...");
    updateText(staleNode, "Loading...");
    updateText(updatedNode, "Loading...");
    return;
  }

  if (health.error) {
    container.classList.remove("text-muted");
    container.classList.add("text-danger");
    updateText(sourceNode, "Unavailable");
    updateText(staleNode, "--");
    updateText(updatedNode, health.error.message || "Error");
    return;
  }

  container.classList.remove("text-muted");
  container.classList.remove("text-danger");
  const snapshot = health.data;
  updateText(sourceNode, snapshot?.source ?? "--");
  updateText(staleNode, formatBoolean(snapshot?.stale));
  updateText(updatedNode, formatAsOf(snapshot?.last_updated));
}

function titleFor(key) {
  switch (key) {
    case "value":
      return "Portfolio Value";
    case "pnl":
      return "Daily P&L";
    case "exposure":
      return "# Positions";
    default:
      return "";
  }
}

function initStaleTooltip(root) {
  const trigger = root.querySelector("[data-stale-tooltip]");
  const bootstrap = window.bootstrap;
  if (!trigger || !bootstrap?.Tooltip) {
    return null;
  }

  return bootstrap.Tooltip.getOrCreateInstance(trigger, {
    title: trigger.getAttribute("title") || "Provider down or weekend/holiday",
    placement: "top",
    trigger: "hover focus",
  });
}

function updateText(node, value) {
  if (node) {
    node.textContent = value ?? "--";
  }
}

function formatBoolean(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return value ? "true" : "false";
}

function formatCurrency(value, currency) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: (currency || "USD").toUpperCase(),
      maximumFractionDigits: 2,
    }).format(Number(value || 0));
  } catch {
    return `${value} ${currency ?? ""}`;
  }
}

function formatAsOf(iso) {
  if (!iso) {
    return "n/a";
  }
  try {
    const date = new Date(iso);
    return date.toLocaleString();
  } catch {
    return iso;
  }
}
