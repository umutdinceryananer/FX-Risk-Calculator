import {
  subscribe,
  getState,
  refreshPositions,
  setPositionsFilters,
  clearPositionsFilters,
  setPositionsSort,
  setPositionsPage,
  setPositionsPageSize,
} from "../state.js";
import { showToast } from "../ui/toast.js";
import { formatDateTimeLocal } from "../utils/datetime.js";
import { formatNativeAmount } from "../utils/numeral.js";

const FILTER_DEBOUNCE_MS = 250;
const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export function renderPortfolioView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = template();

  const elements = {
    currencyInput: root.querySelector("[data-filter-currency]"),
    sideSelect: root.querySelector("[data-filter-side]"),
    clearFiltersButton: root.querySelector("[data-clear-filters]"),
    tableBody: root.querySelector("[data-positions-body]"),
    emptyState: root.querySelector("[data-empty-state]"),
    paginationSummary: root.querySelector("[data-page-summary]"),
    prevButton: root.querySelector("[data-page-prev]"),
    nextButton: root.querySelector("[data-page-next]"),
    pageSizeSelect: root.querySelector("[data-page-size]"),
    sortButtons: Array.from(root.querySelectorAll("[data-sort-button]")),
  };

  let filterTimer = null;
  let currentPositions = normalizePositions(getState()?.positions);

  const unsubscribe = subscribe((stateSnapshot, meta) => {
    const positions = normalizePositions(stateSnapshot?.positions);
    currentPositions = positions;
    syncFilterControls(elements, positions);
    renderPositionsTable(elements.tableBody, positions);
    toggleEmptyState(elements.emptyState, positions);
    updateSortIndicators(elements.sortButtons, positions);
    renderPaginationControls(elements, positions);

    if (meta?.type === "positions_error" && positions.error) {
      showToast({
        title: "Positions unavailable",
        message: positions.error.message ?? "Unable to load positions.",
        variant: "danger",
      });
    }
  });

  const onCurrencyInput = (event) => {
    const value = (event.target.value || "").toUpperCase();
    event.target.value = value;
    if (filterTimer) {
      clearTimeout(filterTimer);
    }
    filterTimer = setTimeout(() => {
      setPositionsFilters({
        currency: value,
        side: elements.sideSelect?.value,
      });
    }, FILTER_DEBOUNCE_MS);
  };

  const onSideChange = (event) => {
    setPositionsFilters({
      currency: elements.currencyInput?.value,
      side: event.target.value,
    });
  };

  const onClearFilters = () => {
    if (filterTimer) {
      clearTimeout(filterTimer);
      filterTimer = null;
    }
    clearPositionsFilters();
    if (elements.currencyInput) {
      elements.currencyInput.value = "";
      elements.currencyInput.focus();
    }
    if (elements.sideSelect) {
      elements.sideSelect.value = "";
    }
  };

  const onSortButtonClick = (event) => {
    const sortField = event.currentTarget.getAttribute("data-sort-button");
    if (!sortField) {
      return;
    }
    setPositionsSort(sortField);
  };

  const changePage = (offset) => {
    const totalPages = computeTotalPages(currentPositions);
    const nextPage = Math.min(Math.max(currentPositions.page + offset, 1), totalPages);
    if (nextPage !== currentPositions.page) {
      setPositionsPage(nextPage);
    }
  };

  const onPrevClick = () => changePage(-1);
  const onNextClick = () => changePage(1);

  const onPageSizeChange = (event) => {
    const nextSize = Number(event.target.value);
    setPositionsPageSize(nextSize);
  };

  if (elements.currencyInput) {
    elements.currencyInput.addEventListener("input", onCurrencyInput);
  }
  if (elements.sideSelect) {
    elements.sideSelect.addEventListener("change", onSideChange);
  }
  if (elements.clearFiltersButton) {
    elements.clearFiltersButton.addEventListener("click", onClearFilters);
  }
  elements.sortButtons.forEach((button) => {
    button.addEventListener("click", onSortButtonClick);
  });
  if (elements.prevButton) {
    elements.prevButton.addEventListener("click", onPrevClick);
  }
  if (elements.nextButton) {
    elements.nextButton.addEventListener("click", onNextClick);
  }
  if (elements.pageSizeSelect) {
    elements.pageSizeSelect.addEventListener("change", onPageSizeChange);
  }

  refreshPositions();

  return () => {
    if (filterTimer) {
      clearTimeout(filterTimer);
    }
    unsubscribe();
    if (elements.currencyInput) {
      elements.currencyInput.removeEventListener("input", onCurrencyInput);
    }
    if (elements.sideSelect) {
      elements.sideSelect.removeEventListener("change", onSideChange);
    }
    if (elements.clearFiltersButton) {
      elements.clearFiltersButton.removeEventListener("click", onClearFilters);
    }
    elements.sortButtons.forEach((button) => {
      button.removeEventListener("click", onSortButtonClick);
    });
    if (elements.prevButton) {
      elements.prevButton.removeEventListener("click", onPrevClick);
    }
    if (elements.nextButton) {
      elements.nextButton.removeEventListener("click", onNextClick);
    }
    if (elements.pageSizeSelect) {
      elements.pageSizeSelect.removeEventListener("change", onPageSizeChange);
    }
  };
}

function template() {
  return `
    <section class="positions-section mb-4">
      <header class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
        <div>
          <h1 class="h3 mb-1 fw-semibold">Portfolio Positions</h1>
          <p class="text-muted mb-0">
            Inspect open positions with quick filters, sorting, and pagination.
          </p>
        </div>
        <button class="btn btn-outline-primary shadow-sm d-flex align-items-center gap-2" type="button" disabled>
          <i class="bi bi-plus-circle"></i>
          Add Position (coming soon)
        </button>
      </header>

      <div class="card border-0 positions-card">
        <div class="positions-toolbar d-flex flex-column flex-lg-row align-items-lg-end gap-3">
          <div class="form-floating positions-filter-field">
            <input
              type="text"
              class="form-control"
              id="positionsCurrencyFilter"
              maxlength="3"
              autocomplete="off"
              autocapitalize="characters"
              spellcheck="false"
              placeholder="Currency"
              data-filter-currency
            />
            <label for="positionsCurrencyFilter">Currency</label>
          </div>
          <div class="form-floating positions-filter-field">
            <select class="form-select" id="positionsSideFilter" data-filter-side>
              <option value="">All sides</option>
              <option value="LONG">Long</option>
              <option value="SHORT">Short</option>
            </select>
            <label for="positionsSideFilter">Side</label>
          </div>
          <div class="d-flex gap-2 ms-lg-auto">
            <button class="btn btn-outline-secondary" type="button" data-clear-filters>
              <i class="bi bi-x-circle"></i>
              Clear filters
            </button>
          </div>
        </div>

        <div class="table-responsive positions-table-wrapper">
          <table class="table table-hover align-middle mb-0 positions-table">
            <thead>
              <tr>
                <th scope="col">
                  <button type="button" class="positions-sort-button text-start" data-sort-button="currency">
                    <span class="positions-sort-label">Currency</span>
                    <i class="bi bi-arrow-down-up positions-sort-icon" aria-hidden="true" data-sort-icon></i>
                  </button>
                </th>
                <th scope="col" class="text-end">
                  <button type="button" class="positions-sort-button justify-content-end" data-sort-button="amount">
                    <span class="positions-sort-label">Amount</span>
                    <i class="bi bi-arrow-down-up positions-sort-icon" aria-hidden="true" data-sort-icon></i>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="positions-sort-button text-start" data-sort-button="side">
                    <span class="positions-sort-label">Side</span>
                    <i class="bi bi-arrow-down-up positions-sort-icon" aria-hidden="true" data-sort-icon></i>
                  </button>
                </th>
                <th scope="col">
                  <button type="button" class="positions-sort-button text-start" data-sort-button="created_at">
                    <span class="positions-sort-label">Created</span>
                    <i class="bi bi-arrow-down-up positions-sort-icon" aria-hidden="true" data-sort-icon></i>
                  </button>
                </th>
              </tr>
            </thead>
            <tbody data-positions-body>
              ${renderSkeletonRows()}
            </tbody>
          </table>
        </div>

        <div class="positions-empty alert alert-info d-none" data-empty-state>
          <i class="bi bi-info-circle-fill me-2"></i>
          No positions yet. Add positions or adjust your filters to populate this table.
        </div>

        <div class="positions-pagination d-flex flex-column flex-lg-row align-items-lg-center gap-3">
          <div class="d-flex align-items-center gap-2">
            <label class="form-label mb-0 text-muted small" for="positionsPageSize">Rows per page</label>
            <select class="form-select form-select-sm shadow-sm" id="positionsPageSize" data-page-size>
              ${renderPageSizeOptions()}
            </select>
          </div>
          <div class="ms-lg-auto d-flex align-items-center gap-3">
            <span class="text-muted small" data-page-summary>Showing 0 of 0 positions</span>
            <div class="btn-group btn-group-sm" role="group" aria-label="Positions pagination controls">
              <button type="button" class="btn btn-outline-secondary" data-page-prev>
                <i class="bi bi-chevron-left"></i>
              </button>
              <button type="button" class="btn btn-outline-secondary" data-page-next>
                <i class="bi bi-chevron-right"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderPageSizeOptions() {
  return PAGE_SIZE_OPTIONS.map((size) => `<option value="${size}">${size}</option>`).join("");
}

function normalizePositions(snapshot) {
  const base = defaultPositionsSnapshot();
  if (!snapshot) {
    return base;
  }

  base.items = Array.isArray(snapshot.items) ? snapshot.items : base.items;
  base.total = coerceNonNegativeInteger(snapshot.total, base.total);
  base.page = coercePositiveInteger(snapshot.page, base.page);
  base.pageSize = Math.min(coercePositiveInteger(snapshot.pageSize, base.pageSize), 200);
  base.currency =
    typeof snapshot.currency === "string" ? snapshot.currency.toUpperCase() : base.currency;
  base.side = typeof snapshot.side === "string" ? snapshot.side.toUpperCase() : base.side;
  base.sort = typeof snapshot.sort === "string" ? snapshot.sort : base.sort;
  base.direction = typeof snapshot.direction === "string" ? snapshot.direction : base.direction;
  base.loading = Boolean(snapshot.loading);
  base.error = snapshot.error ? { ...snapshot.error } : null;
  return base;
}

function defaultPositionsSnapshot() {
  return {
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
}

function syncFilterControls(elements, positions) {
  if (elements.currencyInput && elements.currencyInput.value !== positions.currency) {
    elements.currencyInput.value = positions.currency;
  }
  if (elements.sideSelect && elements.sideSelect.value !== positions.side) {
    elements.sideSelect.value = positions.side;
  }
  if (elements.clearFiltersButton) {
    const hasFilters = Boolean(positions.currency || positions.side);
    elements.clearFiltersButton.disabled = !hasFilters;
  }
}

function renderPositionsTable(tbody, positions) {
  if (!tbody) {
    return;
  }

  if (positions.loading) {
    tbody.innerHTML = renderSkeletonRows(positions);
    return;
  }

  if (positions.error) {
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-danger py-4">
          ${escapeHtml(positions.error.message || "Unable to load positions")}
        </td>
      </tr>
    `;
    return;
  }

  const items = Array.isArray(positions.items) ? positions.items : [];
  if (!items.length) {
    const message =
      positions.total === 0
        ? "No positions match the current filters."
        : "No positions on this page.";
    tbody.innerHTML = `
      <tr>
        <td colspan="4" class="text-center text-muted py-4">${escapeHtml(message)}</td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = items.map(renderPositionRow).join("");
}

function renderPositionRow(item) {
  const currency = escapeHtml(item?.currency_code || "--");
  const amount = formatNativeAmount(item?.amount);
  const side = (item?.side || "").toUpperCase();
  const sideContent = side
    ? `<span class="badge ${
        side === "SHORT" ? "text-bg-danger" : "text-bg-success"
      } positions-side-badge">${escapeHtml(side)}</span>`
    : `<span class="text-muted">--</span>`;
  const createdAtRaw = item?.created_at;
  const createdAt = formatDateTime(createdAtRaw);
  const createdTitle = escapeHtml(createdAtRaw || "");

  return `
    <tr>
      <td class="fw-semibold">${currency}</td>
      <td class="text-end">${escapeHtml(amount)}</td>
      <td>${sideContent}</td>
      <td class="text-muted small" title="${createdTitle}">${escapeHtml(createdAt)}</td>
    </tr>
  `;
}

function renderSkeletonRows(positions = defaultPositionsSnapshot()) {
  const rowCount = Math.min(Math.max(positions.pageSize || 5, 3), 8);
  return Array.from({ length: rowCount })
    .map(
      () => `
        <tr class="placeholder-glow">
          <td><span class="placeholder col-6"></span></td>
          <td class="text-end"><span class="placeholder col-7"></span></td>
          <td><span class="placeholder col-4"></span></td>
          <td><span class="placeholder col-8"></span></td>
        </tr>
      `
    )
    .join("");
}

function toggleEmptyState(banner, positions) {
  if (!banner) {
    return;
  }
  const shouldShow = !positions.loading && !positions.error && positions.total === 0;
  banner.classList.toggle("d-none", !shouldShow);
}

function updateSortIndicators(sortButtons, positions) {
  sortButtons.forEach((button) => {
    const field = button.getAttribute("data-sort-button");
    const icon = button.querySelector("[data-sort-icon]");
    const headerCell = button.closest("th");
    const isActive = field === positions.sort;
    const direction = positions.direction === "desc" ? "desc" : "asc";

    button.classList.toggle("positions-sort-button-active", isActive);
    button.setAttribute("aria-pressed", isActive ? "true" : "false");

    if (headerCell) {
      headerCell.setAttribute(
        "aria-sort",
        isActive ? (direction === "desc" ? "descending" : "ascending") : "none"
      );
    }

    if (!icon) {
      return;
    }

    icon.className = "positions-sort-icon bi bi-arrow-down-up";
    if (isActive) {
      icon.className =
        direction === "desc"
          ? "positions-sort-icon bi bi-caret-down-fill"
          : "positions-sort-icon bi bi-caret-up-fill";
    }
  });
}

function renderPaginationControls(elements, positions) {
  const totalPages = computeTotalPages(positions);

  if (elements.paginationSummary) {
    if (positions.total === 0) {
      elements.paginationSummary.textContent = "Showing 0 of 0 positions";
    } else {
      const start = (positions.page - 1) * positions.pageSize + 1;
      const end = Math.min(positions.total, positions.page * positions.pageSize);
      elements.paginationSummary.textContent = `Showing ${start}-${end} of ${positions.total} positions`;
    }
  }

  if (elements.pageSizeSelect && elements.pageSizeSelect.value !== String(positions.pageSize)) {
    elements.pageSizeSelect.value = String(positions.pageSize);
  }

  if (elements.prevButton) {
    elements.prevButton.disabled = positions.loading || positions.page <= 1;
  }
  if (elements.nextButton) {
    elements.nextButton.disabled = positions.loading || positions.page >= totalPages;
  }
}

function computeTotalPages(positions) {
  if (!positions.total) {
    return 1;
  }
  const pageSize = Math.max(positions.pageSize || 1, 1);
  return Math.max(1, Math.ceil(positions.total / pageSize));
}

function formatDateTime(value) {
  return formatDateTimeLocal(value, { includeUtcHint: true });
}

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return "";
  }
  return String(value).replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char] || char);
}

function coercePositiveInteger(value, fallback = 1) {
  const numeric = Number(value);
  if (Number.isFinite(numeric) && numeric >= 1) {
    return Math.floor(numeric);
  }
  return fallback;
}

function coerceNonNegativeInteger(value, fallback = 0) {
  const numeric = Number(value);
  if (Number.isFinite(numeric) && numeric >= 0) {
    return Math.floor(numeric);
  }
  return fallback;
}

const HTML_ESCAPE_MAP = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};
