const NAV_ITEMS = [
  { href: "#/dashboard", label: "Dashboard", icon: "speedometer2" },
  { href: "#/portfolio", label: "Portfolio", icon: "folder2" },
];

function buildNavItem(item) {
  return `
    <li class="nav-item">
      <a class="nav-link" href="${item.href}" data-nav-link>
        <i class="bi bi-${item.icon} me-2" aria-hidden="true"></i>
        <span>${item.label}</span>
      </a>
    </li>
  `;
}

export function renderNavbar() {
  return `
    <nav class="navbar navbar-expand-lg navbar-light bg-white shadow-sm">
      <div class="container-fluid px-3 px-lg-4">
        <a class="navbar-brand d-flex align-items-center gap-2" href="#/dashboard">
          <span class="badge text-bg-primary rounded-pill fw-semibold">FX</span>
          <span>Risk Calculator</span>
        </a>
        <button
          class="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#appNavbar"
          aria-controls="appNavbar"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="appNavbar">
          <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
            ${NAV_ITEMS.map(buildNavItem).join("")}
          </ul>
        </div>
      </div>
    </nav>
  `;
}
