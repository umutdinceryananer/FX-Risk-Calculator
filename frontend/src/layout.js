import { renderNavbar } from "./components/navbar.js";

export function renderAppShell(rootEl) {
  if (!rootEl) {
    throw new Error("Cannot render application without host element.");
  }

  rootEl.innerHTML = `
    <div class="app-shell">
      ${renderNavbar()}
      <main class="app-content py-4 py-lg-5">
        <div class="container px-3 px-lg-4">
          <div id="view-root" class="view-root">
            <div class="placeholder-state text-center text-muted py-5">
              <div class="spinner-border text-primary mb-3" role="status" aria-hidden="true"></div>
              <p class="fw-semibold">Preparing dashboard…</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  `;
}

