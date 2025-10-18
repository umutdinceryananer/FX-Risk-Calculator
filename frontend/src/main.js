import { renderAppShell } from "./layout.js";
import { initRouter } from "./router.js";

const appRoot = document.querySelector("#app");
renderAppShell(appRoot);

const viewRoot = appRoot.querySelector("#view-root");
initRouter(viewRoot);

setupNavCollapse();

function setupNavCollapse() {
  const collapseElement = document.querySelector("#appNavbar");
  const bootstrapLib = window.bootstrap;
  if (!collapseElement || !bootstrapLib) {
    return;
  }

  const collapse = bootstrapLib.Collapse.getOrCreateInstance(collapseElement, {
    toggle: false,
  });

  document.querySelectorAll("[data-nav-link]").forEach((link) => {
    link.addEventListener("click", () => {
      if (collapseElement.classList.contains("show")) {
        collapse.hide();
      }
    });
  });
}
