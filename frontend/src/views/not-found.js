export function renderNotFoundView(root) {
  if (!root) {
    return;
  }

  root.innerHTML = `
    <section class="py-5">
      <div class="card border-0 mx-auto" style="max-width: 560px;">
        <div class="card-body p-5 text-center">
          <div class="display-6 text-primary mb-3">404</div>
          <h2 class="h4 fw-semibold mb-2">Looks like you\'re off course</h2>
          <p class="text-muted mb-4">
            The page you requested is not part of the FX Risk Calculator dashboard. Use the navigation above to continue.
          </p>
          <a class="btn btn-primary" href="#/dashboard">
            <i class="bi bi-compass me-2"></i>
            Back to Dashboard
          </a>
        </div>
      </div>
    </section>
  `;
}
