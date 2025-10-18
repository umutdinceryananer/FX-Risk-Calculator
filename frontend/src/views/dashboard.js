export function renderDashboardView() {
  return `
    <section class="mb-4">
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 class="h3 mb-1 fw-semibold">Portfolio Overview</h1>
          <p class="text-muted mb-0">Track value, P&amp;L, and exposure across currencies.</p>
        </div>
        <button class="btn btn-primary shadow-sm d-flex align-items-center gap-2" type="button" disabled>
          <i class="bi bi-arrow-clockwise"></i>
          Refresh FX (coming soon)
        </button>
      </header>

      <div class="row g-4">
        ${["Portfolio Value", "Daily P&L", "Open Positions"].map(renderMetricCard).join("")}
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

function renderMetricCard(title) {
  const subtitleMap = {
    "Portfolio Value": "As of last FX snapshot.",
    "Daily P&L": "Change vs previous trading day.",
    "Open Positions": "Positions priced in current base.",
  };

  return `
    <div class="col-12 col-md-6 col-xl-4">
      <div class="card h-100">
        <div class="card-body p-4">
          <p class="text-muted text-uppercase fw-semibold small mb-2">${title}</p>
          <h3 class="display-6 mb-3">$0.00</h3>
          <p class="text-muted small mb-0">${subtitleMap[title]}</p>
        </div>
      </div>
    </div>
  `;
}
