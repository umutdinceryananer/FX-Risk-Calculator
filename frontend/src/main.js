const appRoot = document.querySelector("#app");

if (!appRoot) {
  throw new Error("Cannot bootstrap application without #app root element.");
}

const template = document.createElement("template");
template.innerHTML = `
  <div class="loading-state">
    <div class="text-center">
      <div class="spinner-border text-primary mb-3" role="status" aria-hidden="true"></div>
      <p class="text-muted mb-0">Loading FX Risk Calculator…</p>
    </div>
  </div>
`;

appRoot.appendChild(template.content.cloneNode(true));
