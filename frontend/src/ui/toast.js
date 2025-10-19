const TOAST_CONTAINER_SELECTOR = "[data-toast-container]";

export function showToast({
  title = "Notification",
  message = "",
  variant = "primary",
  autohide = true,
  delay = 4000,
} = {}) {
  const container = document.querySelector(TOAST_CONTAINER_SELECTOR);
  if (!container) {
    console.warn("Toast container not found in DOM.");
    return;
  }

  const toastElement = document.createElement("div");
  toastElement.className = `toast align-items-center text-bg-${variant} border-0 shadow`;
  toastElement.setAttribute("role", "status");
  toastElement.setAttribute("aria-live", "polite");
  toastElement.setAttribute("aria-atomic", "true");

  toastElement.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">
        <div class="fw-semibold mb-1">${title}</div>
        <div>${message}</div>
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(toastElement);

  const bootstrapLib = window.bootstrap;
  if (!bootstrapLib) {
    console.warn("Bootstrap JS not available; showing static toast");
    return;
  }

  const toast = new bootstrapLib.Toast(toastElement, { autohide, delay });
  toast.show();

  toastElement.addEventListener("hidden.bs.toast", () => {
    toast.dispose();
    toastElement.remove();
  });
}
