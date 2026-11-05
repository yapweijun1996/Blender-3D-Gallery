/** A native modal stays above viewers and Game menus without dismissing them. */
export function createUpdateUi() {
  const dialog = document.createElement("dialog");
  dialog.id = "pwa-update-dialog";
  dialog.className = "pwa-update-dialog";
  dialog.setAttribute("aria-labelledby", "pwa-update-title");
  dialog.setAttribute("aria-describedby", "pwa-update-status");
  dialog.innerHTML =
    '<div class="pwa-update-mark" aria-hidden="true">✳</div><p class="eyebrow">BLENDER 3D GALLERY</p><h2 id="pwa-update-title" class="pwa-update-title" tabindex="-1">Updating your gallery.</h2><p id="pwa-update-status" class="pwa-update-status" role="status" aria-live="polite"></p><progress class="pwa-update-progress" aria-hidden="true"></progress><div class="pwa-update-actions" hidden><button type="button" data-update-action="retry">Retry update</button><button type="button" data-update-action="close">Back to current page</button></div>';
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
  const show = (phase, message, remote = false) => {
    busy = phase !== "error";
    dialog.dataset.phase = phase;
    dialog.setAttribute("aria-busy", String(busy));
    title.textContent = remote
      ? "Another tab is updating."
      : phase === "error"
        ? "Update needs another try."
        : "Updating your gallery.";
    status.textContent = message;
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
  return {
    dialog,
    show,
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
