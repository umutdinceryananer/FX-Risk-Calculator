import { subscribe, setViewBase, triggerManualRefresh } from "../state.js";
import { showToast } from "../ui/toast.js";
import { formatDateTimeLocal } from "../utils/datetime.js";
import { formatCurrencyAmount, formatCurrencyNativeAmount } from "../utils/numeral.js";
import { renderExposureChart, destroyExposureChart } from "../charts/exposure.js";
import { renderTimelineChart, destroyTimelineChart } from "../charts/timeline.js";

const VIEW_BASE_PATTERN = /^[A-Z]{3}$/;

export function renderDashboardView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = template();

  const elements = {
    staleBanner: root.querySelector("[data-stale-banner]"),
    viewBaseForm: root.querySelector("[data-view-base-form]"),
    viewBaseInput: root.querySelector("[data-view-base-input]"),
    refreshButton: root.querySelector("[data-refresh-button]"),
    refreshStatus: root.querySelector("[data-refresh-status]"),

    valueCard: root.querySelector("[data-value-card]"),
    valueTotal: root.querySelector("[data-value-total]"),
    valueAsOf: root.querySelector("[data-value-asof]"),
    valueStatus: root.querySelector("[data-value-status]"),
    valueUnpriced: root.querySelector("[data-value-unpriced]"),

    pnlCard: root.querySelector("[data-pnl-card]"),
    pnlTotal: root.querySelector("[data-pnl-total]"),
    pnlAsOf: root.querySelector("[data-pnl-asof]"),
    pnlStatus: root.querySelector("[data-pnl-status]"),
    pnlCurrent: root.querySelector("[data-pnl-current]"),
    pnlPrevious: root.querySelector("[data-pnl-previous]"),
    pnlPrevDate: root.querySelector("[data-pnl-prev-date]"),
    pnlUnpriced: root.querySelector("[data-pnl-unpriced]"),

    ratesCard: root.querySelector("[data-rates-card]"),
    ratesSource: root.querySelector("[data-rates-source]"),
    ratesBase: root.querySelector("[data-rates-base]"),
    ratesUpdated: root.querySelector("[data-rates-updated]"),
    ratesStatus: root.querySelector("[data-rates-status]"),

    exposureStatus: root.querySelector("[data-exposure-status]"),
    exposureAsOf: root.querySelector("[data-exposure-asof]"),
    exposureUnpriced: root.querySelector("[data-exposure-unpriced]"),
    exposureList: root.querySelector("[data-exposure-list]"),
    exposureEmpty: root.querySelector("[data-exposure-empty]"),
    exposureCanvas: root.querySelector("[data-exposure-canvas]"),
    exposureZero: root.querySelector("[data-exposure-zero]"),

    timelineCanvas: root.querySelector("[data-timeline-canvas]"),
    timelineZero: root.querySelector("[data-timeline-zero]"),
  };

  let lastMetricsError = null;
  let lastRefreshError = null;
  let lastHealthError = null;

  const unsubscribe = subscribe((stateSnapshot) => {
    syncViewBaseInput(elements.viewBaseInput, stateSnapshot.viewBase);
    renderRefreshControls(elements, stateSnapshot.refresh);
    renderStaleBanner(elements, stateSnapshot.health);

    renderValueCard(elements, stateSnapshot.metrics);
    renderPnlCard(elements, stateSnapshot.metrics);
    renderRatesCard(elements, stateSnapshot.health);

    renderExposureSection(elements, stateSnapshot.metrics, stateSnapshot.charts);
    renderTimelineSection(elements, stateSnapshot.charts);

    ({ lastMetricsError, lastRefreshError, lastHealthError } = maybeAnnounceErrors(stateSnapshot, {
      metrics: lastMetricsError,
      refresh: lastRefreshError,
      health: lastHealthError,
    }));
  });

  const onViewBaseInput = (event) => {
    event.target.value = (event.target.value || "").toUpperCase().slice(0, 3);
  };

  const onViewBaseSubmit = (event) => {
    event.preventDefault();
    const value = (elements.viewBaseInput?.value || "").trim().toUpperCase();
    if (!VIEW_BASE_PATTERN.test(value)) {
      showToast({
        title: "Invalid base currency",
        message: "Please enter a 3-letter ISO currency code.",
        variant: "warning",
      });
      return;
    }
    setViewBase(value);
  };

  const onRefreshClick = async () => {
    const result = await triggerManualRefresh();
    if (!result.ok) {
      lastRefreshError = result.message;
    }
    showToast({
      title: result.ok ? "Rates refresh triggered" : "Refresh failed",
      message: result.message,
      variant: result.ok ? "success" : "danger",
    });
  };

  if (elements.viewBaseInput) {
    elements.viewBaseInput.addEventListener("input", onViewBaseInput);
  }
  if (elements.viewBaseForm) {
    elements.viewBaseForm.addEventListener("submit", onViewBaseSubmit);
  }
  if (elements.refreshButton) {
    elements.refreshButton.addEventListener("click", onRefreshClick);
  }

  return () => {
    unsubscribe();
    if (elements.viewBaseInput) {
      elements.viewBaseInput.removeEventListener("input", onViewBaseInput);
    }
    if (elements.viewBaseForm) {
      elements.viewBaseForm.removeEventListener("submit", onViewBaseSubmit);
    }
    if (elements.refreshButton) {
      elements.refreshButton.removeEventListener("click", onRefreshClick);
    }
    destroyExposureChart();
    destroyTimelineChart();
  };
}

function template() {
  return `
    <section class="mb-4">
      <header class="d-flex flex-column flex-lg-row justify-content-between align-items-lg-center gap-3 mb-4">
        <div>
          <h1 class="h3 mb-2 fw-semibold">Portfolio Dashboard</h1>
          <p class="text-muted mb-0">
            Monitor portfolio value, daily performance, and currency exposures in the selected base currency.
          </p>
        </div>
        <div class="d-flex flex-column flex-sm-row align-items-stretch gap-2">
          <form class="d-flex gap-2" data-view-base-form>
            <div class="form-floating">
              <input
                type="text"
                class="form-control"
                id="dashboardViewBase"
                name="viewBase"
                maxlength="3"
                autocomplete="off"
                autocapitalize="characters"
                placeholder="Base"
                data-view-base-input
              />
              <label for="dashboardViewBase">View base</label>
            </div>
            <button type="submit" class="btn btn-outline-primary">Apply</button>
          </form>
          <button type="button" class="btn btn-primary" data-refresh-button>
            <i class="bi bi-arrow-repeat me-2" aria-hidden="true"></i>
            Refresh Rates
          </button>
        </div>
      </header>

      <div class="alert alert-warning d-flex align-items-center gap-3 d-none" role="alert" data-stale-banner>
        <i class="bi bi-exclamation-triangle-fill fs-4" aria-hidden="true"></i>
        <div>
          <strong>FX rates look stale.</strong>
          <div class="small">The latest snapshot is older than expected. Consider triggering a manual refresh.</div>
        </div>
      </div>

      <p class="small text-muted mb-4" data-refresh-status></p>

      <div class="row g-4">
        <div class="col-12 col-lg-4">
          <div class="card kpi-card h-100 shadow-sm" data-value-card>
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h2 class="h6 text-uppercase text-muted mb-2">Portfolio Value</h2>
                  <div class="metric-value fs-3 mb-1" data-value-total>--</div>
                  <p class="metric-footnote mb-0 text-muted small" data-value-asof></p>
                </div>
                <span class="badge rounded-pill text-bg-secondary" data-value-status>--</span>
              </div>
              <div class="metric-unpriced-group mt-3 d-none" data-value-unpriced></div>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="card kpi-card h-100 shadow-sm" data-pnl-card>
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h2 class="h6 text-uppercase text-muted mb-2">Daily P&L</h2>
                  <div class="metric-value fs-3 mb-1" data-pnl-total>--</div>
                  <p class="metric-footnote mb-0 text-muted small" data-pnl-asof></p>
                </div>
                <span class="badge rounded-pill text-bg-secondary" data-pnl-status>--</span>
              </div>
              <ul class="list-unstyled small text-muted mt-3 mb-0">
                <li>Current value: <span data-pnl-current>--</span></li>
                <li>Previous value: <span data-pnl-previous>--</span></li>
                <li>Previous date: <span data-pnl-prev-date>--</span></li>
              </ul>
              <div class="metric-unpriced-group mt-3 d-none" data-pnl-unpriced></div>
            </div>
          </div>
        </div>

        <div class="col-12 col-lg-4">
          <div class="card kpi-card h-100 shadow-sm" data-rates-card>
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start">
                <div>
                  <h2 class="h6 text-uppercase text-muted mb-2">Rates Snapshot</h2>
                  <div class="metric-value fs-5 mb-1" data-rates-status>--</div>
                  <p class="metric-footnote mb-0 text-muted small" data-rates-updated></p>
                </div>
                <span class="badge rounded-pill text-bg-light" data-rates-base>--</span>
              </div>
              <p class="text-muted small mt-3 mb-0">
                Source: <span class="fw-semibold" data-rates-source>--</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="mb-4">
      <div class="row g-4">
        <div class="col-12 col-xl-6">
          <div class="card h-100 shadow-sm">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                  <h2 class="h5 mb-1">Exposure Mix</h2>
                  <p class="text-muted small mb-0" data-exposure-asof></p>
                </div>
                <span class="badge text-bg-light" data-exposure-status>--</span>
              </div>
              <div class="chart-area" style="height: 320px;">
                <canvas data-exposure-canvas></canvas>
                <div class="chart-zero-state d-flex flex-column justify-content-center align-items-center text-muted gap-2 d-none" data-exposure-zero>
                  <i class="bi bi-pie-chart fs-1" aria-hidden="true"></i>
                  <span>No priced exposures to display.</span>
                </div>
              </div>
              <ul class="exposure-list mt-4" data-exposure-list></ul>
              <p class="text-muted small mb-0 d-none" data-exposure-empty>No priced exposures available.</p>
              <div class="metric-unpriced-group mt-3 d-none" data-exposure-unpriced></div>
            </div>
          </div>
        </div>

        <div class="col-12 col-xl-6">
          <div class="card h-100 shadow-sm">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-3">
                <div>
                  <h2 class="h5 mb-1">Value Trend</h2>
                  <p class="text-muted small mb-0">Last 30 days</p>
                </div>
              </div>
              <div class="chart-area" style="height: 320px;">
                <canvas data-timeline-canvas></canvas>
                <div class="chart-zero-state d-flex flex-column justify-content-center align-items-center text-muted gap-2 d-none" data-timeline-zero>
                  <i class="bi bi-graph-up fs-1" aria-hidden="true"></i>
                  <span>No timeline data available.</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function syncViewBaseInput(input, viewBase) {
  if (!input) {
    return;
  }
  const normalized = (viewBase || "").toUpperCase();
  if (document.activeElement === input) {
    return;
  }
  input.value = normalized;
}

function renderRefreshControls(elements, refresh) {
  const isLoading = Boolean(refresh?.loading);
  if (elements.refreshButton) {
    elements.refreshButton.disabled = isLoading;
    elements.refreshButton.classList.toggle("disabled", isLoading);
  }
  if (elements.refreshStatus) {
    if (isLoading) {
      elements.refreshStatus.textContent = "Refreshing FX rates…";
      elements.refreshStatus.classList.remove("text-danger");
    } else if (refresh?.error) {
      elements.refreshStatus.textContent = refresh.error.message;
      elements.refreshStatus.classList.add("text-danger");
    } else {
      elements.refreshStatus.textContent = "";
      elements.refreshStatus.classList.remove("text-danger");
    }
  }
}

function renderStaleBanner(elements, healthState) {
  const banner = elements.staleBanner;
  if (!banner) {
    return;
  }
  const stale = Boolean(healthState?.data?.stale);
  banner.classList.toggle("d-none", !stale);
}

function renderValueCard(elements, metricsState) {
  const { valueCard, valueTotal, valueAsOf, valueStatus, valueUnpriced } = elements;
  if (!valueCard) {
    return;
  }

  if (metricsState.loading) {
    valueTotal.textContent = "Loading…";
    valueAsOf.textContent = "";
    valueStatus.textContent = "Loading";
    hideUnpriced(valueUnpriced);
    return;
  }

  if (metricsState.error || !metricsState.value) {
    valueTotal.textContent = "--";
    valueAsOf.textContent = metricsState.error?.message || "Unable to load portfolio value.";
    valueStatus.textContent = "Unavailable";
    hideUnpriced(valueUnpriced);
    return;
  }

  const payload = metricsState.value;
  const baseCurrency = payload.view_base || payload.portfolio_base || "";

  valueTotal.textContent = formatCurrencyAmount(payload.value, baseCurrency);
  valueAsOf.textContent = payload.as_of
    ? `As of ${formatDateTimeLocal(payload.as_of, { includeUtcHint: true })}`
    : "As of n/a";
  valueStatus.textContent = `Priced ${payload.priced} / Unpriced ${payload.unpriced}`;
  valueStatus.classList.toggle("text-bg-secondary", payload.unpriced === 0);
  valueStatus.classList.toggle("text-bg-warning", payload.unpriced > 0);

  renderUnpricedReasons(valueUnpriced, payload.unpriced_reasons);
}

function renderPnlCard(elements, metricsState) {
  const {
    pnlCard,
    pnlTotal,
    pnlAsOf,
    pnlStatus,
    pnlCurrent,
    pnlPrevious,
    pnlPrevDate,
    pnlUnpriced,
  } = elements;

  if (!pnlCard) {
    return;
  }

  if (metricsState.loading) {
    pnlTotal.textContent = "Loading…";
    pnlAsOf.textContent = "";
    pnlStatus.textContent = "Loading";
    pnlCurrent.textContent = "--";
    pnlPrevious.textContent = "--";
    pnlPrevDate.textContent = "--";
    hideUnpriced(pnlUnpriced);
    return;
  }

  if (metricsState.error || !metricsState.pnl) {
    pnlTotal.textContent = "--";
    pnlAsOf.textContent = metricsState.error?.message || "Unable to load daily P&L.";
    pnlStatus.textContent = "Unavailable";
    pnlCurrent.textContent = "--";
    pnlPrevious.textContent = "--";
    pnlPrevDate.textContent = "--";
    hideUnpriced(pnlUnpriced);
    return;
  }

  const pnl = metricsState.pnl;
  const baseCurrency = pnl.view_base || "";

  pnlTotal.textContent = formatCurrencyAmount(pnl.pnl, baseCurrency, { signDisplay: "always" });
  pnlAsOf.textContent = pnl.as_of
    ? `As of ${formatDateTimeLocal(pnl.as_of, { includeUtcHint: true })}`
    : "As of n/a";
  pnlStatus.textContent = `Positions changed: ${pnl.positions_changed ? "Yes" : "No"}`;
  pnlStatus.classList.toggle("text-bg-secondary", !pnl.positions_changed);
  pnlStatus.classList.toggle("text-bg-info", pnl.positions_changed);

  pnlCurrent.textContent = formatCurrencyAmount(pnl.value_current, baseCurrency);
  pnlPrevious.textContent =
    pnl.value_previous != null ? formatCurrencyAmount(pnl.value_previous, baseCurrency) : "--";
  pnlPrevDate.textContent = pnl.prev_date
    ? formatDateTimeLocal(pnl.prev_date, { includeUtcHint: true })
    : "--";

  const badges = [
    ...collectReasonBadges(pnl.unpriced_current_reasons, "Current"),
    ...collectReasonBadges(pnl.unpriced_previous_reasons, "Previous"),
  ];
  renderBadges(pnlUnpriced, badges);
}

function renderRatesCard(elements, healthState) {
  const { ratesCard, ratesSource, ratesBase, ratesUpdated, ratesStatus } = elements;
  if (!ratesCard) {
    return;
  }

  if (healthState.loading) {
    ratesStatus.textContent = "Loading…";
    ratesSource.textContent = "--";
    ratesBase.textContent = "--";
    ratesUpdated.textContent = "";
    return;
  }

  if (healthState.error || !healthState.data) {
    ratesStatus.textContent = "Unavailable";
    ratesSource.textContent = healthState.error?.message || "--";
    ratesBase.textContent = "--";
    ratesUpdated.textContent = "";
    return;
  }

  const data = healthState.data;
  ratesStatus.textContent = data.status === "ok" ? "Healthy" : data.status ?? "Unknown";
  ratesStatus.classList.toggle("text-bg-secondary", data.status === "ok");
  ratesStatus.classList.toggle("text-bg-warning", data.status !== "ok");
  ratesSource.textContent = data.source || "N/A";
  ratesBase.textContent = data.base_currency ? data.base_currency.toUpperCase() : "--";
  ratesUpdated.textContent = data.last_updated
    ? `Last updated ${formatDateTimeLocal(data.last_updated, { includeUtcHint: true })}`
    : "Last updated n/a";
}

function renderExposureSection(elements, metricsState, chartsState) {
  const {
    exposureStatus,
    exposureAsOf,
    exposureUnpriced,
    exposureList,
    exposureEmpty,
    exposureCanvas,
    exposureZero,
  } = elements;

  const exposureMetrics = metricsState.exposure;
  const chartData = chartsState.exposure;
  const viewBase =
    chartData?.viewBase || exposureMetrics?.view_base || metricsState.value?.view_base || "USD";

  if (metricsState.loading) {
    exposureStatus.textContent = "Loading…";
    exposureAsOf.textContent = "";
    hideUnpriced(exposureUnpriced);
    if (exposureList) {
      exposureList.innerHTML = "";
    }
    if (exposureEmpty) {
      exposureEmpty.classList.add("d-none");
    }
  } else if (metricsState.error || !exposureMetrics) {
    exposureStatus.textContent = "Unavailable";
    exposureAsOf.textContent = metricsState.error?.message || "Unable to load exposure metrics.";
    hideUnpriced(exposureUnpriced);
    if (exposureList) {
      exposureList.innerHTML = "";
    }
    if (exposureEmpty) {
      exposureEmpty.classList.add("d-none");
    }
  } else {
    exposureStatus.textContent = `Priced ${exposureMetrics.priced} / Unpriced ${exposureMetrics.unpriced}`;
    exposureStatus.classList.toggle("text-bg-light", exposureMetrics.unpriced === 0);
    exposureStatus.classList.toggle("text-bg-warning", exposureMetrics.unpriced > 0);
    exposureAsOf.textContent = exposureMetrics.as_of
      ? `As of ${formatDateTimeLocal(exposureMetrics.as_of, { includeUtcHint: true })}`
      : "As of n/a";
    renderUnpricedReasons(exposureUnpriced, exposureMetrics.unpriced_reasons);
  }

  const renderedChart = exposureCanvas ? renderExposureChart(exposureCanvas, chartData) : null;
  togglePlaceholder(exposureZero, Boolean(renderedChart));

  renderExposureList(exposureList, exposureEmpty, chartData?.items, viewBase);
}

function renderTimelineSection(elements, chartsState) {
  const timelineChart = elements.timelineCanvas
    ? renderTimelineChart(elements.timelineCanvas, chartsState.timeline)
    : null;
  togglePlaceholder(elements.timelineZero, Boolean(timelineChart));
}

function renderExposureList(listEl, emptyEl, items, viewBase) {
  if (!listEl) {
    return;
  }
  const entries = Array.isArray(items) ? items : [];
  if (!entries.length) {
    listEl.innerHTML = "";
    if (emptyEl) {
      emptyEl.classList.remove("d-none");
    }
    return;
  }

  if (emptyEl) {
    emptyEl.classList.add("d-none");
  }

  listEl.innerHTML = entries
    .map((item) => {
      const baseLabel = formatCurrencyAmount(item.baseValue, viewBase, { fallback: "--" });
      const nativeCurrency = (item.nativeCurrency || "").toUpperCase();
      const nativeLabel = nativeCurrency
        ? formatCurrencyNativeAmount(item.nativeValue, nativeCurrency, { fallback: "--" })
        : null;
      return `
        <li class="d-flex justify-content-between align-items-start gap-3">
          <div>
            <div class="fw-semibold">${escapeHtml(item.label || "--")}</div>
            ${
              nativeLabel
                ? `<small class="text-muted">Native (${escapeHtml(nativeCurrency)}): ${escapeHtml(
                    nativeLabel
                  )}</small>`
                : ""
            }
          </div>
          <div class="exposure-values">
            <span class="fw-semibold">${escapeHtml(baseLabel)}</span>
          </div>
        </li>
      `;
    })
    .join("");
}

function renderUnpricedReasons(container, reasons) {
  if (!container) {
    return;
  }
  const badges = collectReasonBadges(reasons);
  renderBadges(container, badges);
}

function collectReasonBadges(reasons, prefix = null) {
  if (!reasons || typeof reasons !== "object") {
    return [];
  }
  return Object.entries(reasons)
    .filter(([, values]) => Array.isArray(values) && values.length)
    .map(([reason, values]) => {
      const label = prefix ? `${prefix} ${formatReason(reason)}` : formatReason(reason);
      return `${label}: ${values.map((value) => value.toUpperCase()).join(", ")}`;
    });
}

function renderBadges(container, badges) {
  if (!container) {
    return;
  }
  if (!badges.length) {
    hideUnpriced(container);
    return;
  }
  container.classList.remove("d-none");
  container.innerHTML = badges
    .map((text) => `<span class="metric-unpriced-badge">${escapeHtml(text)}</span>`)
    .join("");
}

function hideUnpriced(container) {
  if (container) {
    container.innerHTML = "";
    container.classList.add("d-none");
  }
}

function togglePlaceholder(element, hasData) {
  if (!element) {
    return;
  }
  element.classList.toggle("d-none", hasData);
}

function formatReason(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function maybeAnnounceErrors(stateSnapshot, lastKnown) {
  const nextMetricsError = stateSnapshot.metrics.error?.message || null;
  if (nextMetricsError && nextMetricsError !== lastKnown.metrics) {
    showToast({
      title: "Metrics unavailable",
      message: nextMetricsError,
      variant: "danger",
    });
  }

  const nextRefreshError = stateSnapshot.refresh.error?.message || null;
  if (nextRefreshError && nextRefreshError !== lastKnown.refresh) {
    showToast({
      title: "Refresh error",
      message: nextRefreshError,
      variant: "danger",
    });
  }

  const nextHealthError = stateSnapshot.health.error?.message || null;
  if (nextHealthError && nextHealthError !== lastKnown.health) {
    showToast({
      title: "Health status unavailable",
      message: nextHealthError,
      variant: "danger",
    });
  }

  return {
    lastMetricsError: nextMetricsError || null,
    lastRefreshError: nextRefreshError || null,
    lastHealthError: nextHealthError || null,
  };
}

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char] || char);
}

const HTML_ESCAPE_MAP = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};
