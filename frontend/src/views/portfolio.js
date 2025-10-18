export function renderPortfolioView() {
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
                  <th scope="col">Amount</th>
                  <th scope="col">Side</th>
                  <th scope="col">Base Equivalent</th>
                  <th scope="col" class="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                ${renderSkeletonRow()}
                ${renderSkeletonRow()}
                ${renderSkeletonRow()}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  `;
}

function renderSkeletonRow() {
  return `
    <tr class="placeholder-glow">
      <td><span class="placeholder col-6"></span></td>
      <td><span class="placeholder col-8"></span></td>
      <td><span class="placeholder col-5"></span></td>
      <td><span class="placeholder col-9"></span></td>
      <td class="text-end"><span class="placeholder col-4"></span></td>
    </tr>
  `;
}
