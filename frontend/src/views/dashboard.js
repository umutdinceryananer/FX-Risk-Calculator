import { subscribe, setViewBase } from "../state.js";

export function renderDashboardView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = template();

  const baseSelect = root.querySelector("[data-view-base]");
  baseSelect.addEventListener("change", (event) => {
    setViewBase(event.target.value);
  });

  const metricCards = Array.from(root.querySelectorAll("[data-metric-card]"));
  const banner = root.querySelector("[data-stale-banner]");

  const unsubscribe = subscribe((state) => {
    if (baseSelect.value !== state.viewBase) {
      baseSelect.value = state.viewBase;
    }
    renderMetrics(metricCards, state.metrics);
    renderBanner(banner, state.metrics);
  });

  return () => unsubscribe();
}

function template() {
  return `
    <section class="mb-4">
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 class="h3 mb-1 fw-semibold">Portfolio Overview</h1>
          <p class="text-muted mb-0">Track value, P&L, and exposure across currencies.</p>
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
          <button class="btn btn-primary shadow-sm d-flex align-items-center gap-2" type="button" disabled>
            <i class="bi bi-arrow-clockwise"></i>
            Refresh FX (coming soon)
          </button>
        </div>
      </header>

      <div class="alert alert-warning d-none" role="alert" data-stale-banner>
        <div class="d-flex align-items-center gap-2">
          <i class="bi bi-exclamation-triangle-fill"></i>
          <span>Provider currently stale. Using last available snapshot.</span>
        </div>
      </div>

      <div class="row g-4">
        ${[
          { key: "value", title: "Portfolio Value" },
          { key: "pnl", title: "Daily P&L" },
          { key: "exposure", title: "Open Positions" },
        ]
          .map(renderMetricSkeleton)
          .join("")}
      </div>
    </section>

    <section class="mb-5">
      <div class="card border-0">
        <div class="card-body p-4">
          <div class="d-flex align-items-center justify-content-between mb-3">
            <h2 class="h5 mb-0">Value Timeline</h2>
            <span class="badge text-bg-secondary">Chart placeholder</span>
          </div>
          <div class="placeholder-glow">
            <div class="ratio ratio-16x9 bg-body-secondary rounded-4"></div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderMetricSkeleton({ key, title }) {
  return `
    <div class="col-12 col-md-6 col-xl-4">
      <div class="card h-100" data-metric-card="${key}">
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
    case "value":
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2">Portfolio Value</p>
        <h3 class="display-6 mb-3">${formatCurrency(payload.value, payload.view_base)}</h3>
        <p class="text-muted small mb-2">Priced: ${payload.priced} / Unpriced: ${payload.unpriced}</p>
        <p class="text-muted small mb-0">As of ${formatAsOf(payload.as_of)}</p>
      `;
    case "pnl":
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2">Daily P&L</p>
        <h3 class="display-6 mb-0 ${Number(payload.pnl) < 0 ? "text-danger" : "text-success"}">
          ${formatCurrency(payload.pnl, payload.view_base)}
        </h3>
        <p class="text-muted small mb-1">Prev value: ${formatCurrency(payload.value_previous ?? "0", payload.view_base)}</p>
        <p class="text-muted small mb-0">As of ${formatAsOf(payload.as_of)}</p>
      `;
    case "exposure":
      return `
        <p class="text-muted text-uppercase fw-semibold small mb-2">Open Positions</p>
        <h3 class="display-6 mb-3">${payload.exposures?.length ?? 0}</h3>
        <p class="text-muted small mb-1">Priced positions: ${payload.priced}</p>
        <p class="text-muted small mb-0">As of ${formatAsOf(payload.as_of)}</p>
      `;
    default:
      return "";
  }
}

function renderBanner(bannerNode, metrics) {
  if (!bannerNode) {
    return;
  }

  const shouldShow = Boolean(metrics.value && metrics.value.priced === 0 && !metrics.loading && !metrics.error);
  bannerNode.classList.toggle("d-none", !shouldShow);
}

function titleFor(key) {
  switch (key) {
    case "value":
      return "Portfolio Value";
    case "pnl":
      return "Daily P&L";
    case "exposure":
      return "Open Positions";
    default:
      return "";
  }
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
