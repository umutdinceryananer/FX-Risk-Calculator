import { subscribe } from "../state.js";

export function renderPortfolioView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = template();

  const tableBody = root.querySelector("[data-exposure-body]");
  const emptyState = root.querySelector("[data-empty-state]");

  const unsubscribe = subscribe((state) => {
    renderExposureTable(tableBody, state.metrics);
    toggleEmptyState(emptyState, state.metrics);
  });

  return () => unsubscribe();
}

function template() {
  return `
    <section class="mb-4">
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 class="h3 mb-1 fw-semibold">Portfolio Positions</h1>
          <p class="text-muted mb-0">
            Review open positions, exposure, and risk concentrations.
          </p>
        </div>
        <button class="btn btn-outline-primary shadow-sm d-flex align-items-center gap-2" type="button" disabled>
          <i class="bi bi-plus-circle"></i>
          Add Position (coming soon)
        </button>
      </header>

      <div class="card border-0">
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr>
                  <th scope="col">Currency</th>
                  <th scope="col">Net Native</th>
                  <th scope="col">Base Equivalent</th>
                  <th scope="col" class="text-end">Share</th>
                </tr>
              </thead>
              <tbody data-exposure-body>
                ${Array.from({ length: 3 }).map(() => renderSkeletonRow()).join("")}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div class="alert alert-info mt-3 d-none" data-empty-state>
        <i class="bi bi-info-circle-fill me-2"></i>
        Once portfolio positions are priced, they will appear here.
      </div>
    </section>
  `;
}

function renderExposureTable(tbody, metrics) {
  if (!tbody) {
    return;
  }

  if (metrics.loading) {
    tbody.innerHTML = Array.from({ length: 3 }).map(() => renderSkeletonRow()).join("");
    return;
  }

  if (metrics.error) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-danger text-center py-4">
          Unable to load exposures: ${metrics.error.message || "unexpected error"}
        </td>
      </tr>
    `;
    return;
  }

  const exposure = metrics.exposure;
  if (!exposure || !Array.isArray(exposure.exposures) || exposure.exposures.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center py-4 text-muted">No priced positions yet.</td>
      </tr>
    `;
    return;
  }

  const totalBase = exposure.exposures.reduce((acc, item) => acc + Math.abs(Number(item.base_equivalent || 0)), 0);

  tbody.innerHTML = exposure.exposures
    .map((item) => {
      const share = totalBase > 0 ? (Math.abs(Number(item.base_equivalent || 0)) / totalBase) * 100 : 0;
      return `
        <tr>
          <td class="fw-semibold">${item.currency_code}</td>
          <td>${formatDecimal(item.net_native)}</td>
          <td>${formatCurrency(item.base_equivalent, exposure.view_base)}</td>
          <td class="text-end">
            <span class="badge text-bg-light border">
              ${share.toFixed(1)}%
            </span>
          </td>
        </tr>
      `;
    })
    .join("");
}

function toggleEmptyState(banner, metrics) {
  if (!banner) {
    return;
  }
  const hasExposure = Boolean(metrics.exposure && Array.isArray(metrics.exposure.exposures) && metrics.exposure.exposures.length > 0);
  const shouldShow = !metrics.loading && !metrics.error && !hasExposure;
  banner.classList.toggle("d-none", !shouldShow);
}

function renderSkeletonRow() {
  return `
    <tr class="placeholder-glow">
      <td><span class="placeholder col-6"></span></td>
      <td><span class="placeholder col-7"></span></td>
      <td><span class="placeholder col-8"></span></td>
      <td class="text-end"><span class="placeholder col-5"></span></td>
    </tr>
  `;
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

function formatDecimal(value) {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}
