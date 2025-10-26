const TOAST_CONTAINER_SELECTOR = "[data-toast-container]";

function logWarning(message, ...args) {
  // eslint-disable-next-line no-console
  console.warn(message, ...args);
}

function logError(message, ...args) {
  // eslint-disable-next-line no-console
  console.error(message, ...args);
}

export function showToast({
  title = "Notification",
  message = "",
  variant = "primary",
  autohide,
  delay = 4000,
  actions = [],
} = {}) {
  const container = document.querySelector(TOAST_CONTAINER_SELECTOR);
  if (!container) {
    logWarning("Toast container not found in DOM.");
    return;
  }

  const actionList = Array.isArray(actions) ? actions.filter(Boolean) : [];
  const hasActions = actionList.length > 0;
  const shouldAutoHide = typeof autohide === "boolean" ? autohide : !hasActions;

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
        ${
          hasActions
            ? '<div class="toast-actions mt-3 d-flex flex-wrap gap-2" data-toast-actions></div>'
            : ""
        }
      </div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  container.appendChild(toastElement);

  const bootstrapLib = window.bootstrap;
  let toastInstance = null;
  if (bootstrapLib && bootstrapLib.Toast) {
    toastInstance = new bootstrapLib.Toast(toastElement, { autohide: shouldAutoHide, delay });
    toastInstance.show();
  } else {
    logWarning("Bootstrap JS not available; showing static toast");
    if (shouldAutoHide) {
      setTimeout(() => {
        toastElement.remove();
      }, delay);
    }
  }

  if (hasActions) {
    const actionsContainer = toastElement.querySelector("[data-toast-actions]");
    actionList.forEach((action) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `btn btn-sm btn-${action.variant || "light"}`;
      button.textContent = action.label || "Action";
      button.addEventListener("click", (event) => {
        event.preventDefault();
        try {
          if (typeof action.onClick === "function") {
            action.onClick();
          }
        } catch (err) {
          logError("Toast action handler failed", err);
        }
        if (action.dismiss !== false) {
          if (toastInstance) {
            toastInstance.hide();
          } else {
            toastElement.remove();
          }
        }
      });
      actionsContainer?.appendChild(button);
    });
  }

  if (toastInstance) {
    toastElement.addEventListener("hidden.bs.toast", () => {
      toastInstance.dispose();
      toastElement.remove();
    });
  }
}
