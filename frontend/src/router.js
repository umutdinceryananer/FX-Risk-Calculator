import { renderDashboardView } from "./views/dashboard.js";
import { renderNotFoundView } from "./views/not-found.js";
import { renderPortfolioView } from "./views/portfolio.js";

const DEFAULT_ROUTE = "/dashboard";

const routes = {
  "/dashboard": renderDashboardView,
  "/portfolio": renderPortfolioView,
};

let currentCleanup = null;

export function initRouter(viewRoot) {
  if (!viewRoot) {
    throw new Error("Router requires a view root element.");
  }

  function handleNavigation() {
    if (typeof currentCleanup === "function") {
      currentCleanup();
      currentCleanup = null;
    }

    const path = normalizePath(window.location.hash);
    const renderView = routes[path] ?? renderNotFoundView;

    viewRoot.innerHTML = "";
    currentCleanup = renderView(viewRoot, { path }) || null;
    highlightActiveLink(path);
  }

  if (!window.location.hash) {
    window.location.replace(`#${DEFAULT_ROUTE}`);
  }

  window.addEventListener("hashchange", handleNavigation);
  handleNavigation();
}

function normalizePath(hash) {
  const value = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!value) {
    return DEFAULT_ROUTE;
  }
  const [path] = value.split("?");
  return path.toLowerCase();
}

function highlightActiveLink(activePath) {
  const links = document.querySelectorAll("[data-nav-link]");
  links.forEach((link) => {
    const href = link.getAttribute("href") || "";
    const normalized = normalizePath(href);
    link.classList.toggle("active", normalized === activePath);
  });
}
