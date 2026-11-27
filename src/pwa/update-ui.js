import { localize, mountMarkup } from "../i18n/index.js";

/** A native modal stays above viewers and Game menus without dismissing them. */
export function createUpdateUi() {
  const dialog = document.createElement("dialog");
  dialog.id = "pwa-update-dialog";
  dialog.className = "pwa-update-dialog";
  dialog.setAttribute("aria-labelledby", "pwa-update-title");
  dialog.setAttribute("aria-describedby", "pwa-update-status");
  mountMarkup(dialog, '<div class="pwa-update-mark" aria-hidden="true"><svg viewBox="0 0 120 120" focusable="false" fill="none" stroke="currentColor" stroke-linecap="round"><circle class="pwa-ring-track" cx="60" cy="60" r="52" stroke-width="6"/><circle class="pwa-ring-arc" cx="60" cy="60" r="52" stroke-width="6" stroke-dasharray="90 237"/><g class="pwa-ring-star" stroke-width="7"><path d="M60 36v48M36 60h48M43 43l34 34M77 43L43 77"/></g></svg></div><p class="eyebrow">BLENDER 3D GALLERY</p><h2 id="pwa-update-title" class="pwa-update-title" tabindex="-1" data-i18n="pwa.updatingTitle"></h2><p class="pwa-update-version" hidden></p><p id="pwa-update-status" class="pwa-update-status" role="status" aria-live="polite"></p><progress class="pwa-update-progress" aria-hidden="true"></progress><div class="pwa-update-actions" hidden><button type="button" data-update-action="retry" data-i18n="pwa.retry"></button><button type="button" data-update-action="close" data-i18n="pwa.back"></button></div>');
  document.body.append(dialog);
  const title = dialog.querySelector("h2"),
    status = dialog.querySelector('[role="status"]'),
    actions = dialog.querySelector(".pwa-update-actions");
  let previousFocus,
    busy = false;
  dialog.addEventListener("cancel", (event) => {
    if (busy) event.preventDefault();
  });
  // Game's global shortcuts must not open a second modal above this one.
  window.addEventListener(
    "keydown",
    (event) => {
      if (!dialog.open) return;
      event.stopImmediatePropagation();
      if (busy && event.key === "Escape") event.preventDefault();
    },
    true,
  );
  dialog.addEventListener("close", () => {
    document.body.classList.remove("pwa-updating");
    if (previousFocus?.isConnected) previousFocus.focus();
  });
  const show = (phase, key, remote = false) => {
    // Another tab's update has its own target: never show this tab's earlier version pill for it.
    if (remote) {
      const pill = dialog.querySelector(".pwa-update-version");
      pill.textContent = "";
      pill.hidden = true;
    }
    busy = phase !== "error";
    dialog.dataset.phase = phase;
    dialog.setAttribute("aria-busy", String(busy));
    localize(title, remote ? "pwa.remoteTitle" : phase === "error" ? "pwa.errorTitle" : "pwa.updatingTitle");
    localize(status, key);
    actions.hidden = busy;
    document.body.classList.toggle("pwa-updating", busy);
    if (!dialog.open) {
      previousFocus = document.activeElement;
      dialog.showModal();
      title.focus();
    }
    if (busy) title.focus();
    else actions.querySelector("button").focus();
  };
  const versions = dialog.querySelector(".pwa-update-version");
  return {
    dialog,
    show,
    /** Name the running and target versions; hidden when the target is unknown. */
    setVersions(text) {
      versions.textContent = text;
      versions.hidden = !text;
    },
    close() {
      busy = false;
      if (dialog.open) dialog.close();
      document.body.classList.remove("pwa-updating");
    },
    onRetry(handler) {
      dialog.querySelector('[data-update-action="retry"]').onclick = handler;
    },
    onClose(handler) {
      dialog.querySelector('[data-update-action="close"]').onclick = handler;
    },
  };
}
