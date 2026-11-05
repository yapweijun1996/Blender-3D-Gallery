export function setupMenu() {
  const dialog = document.querySelector("#mobile-menu"),
    trigger = document.querySelector("#menu-trigger");
  let previousOverflow = "";
  let restoreFocus = true;
  const close = (restore = true) => {
    restoreFocus = restore;
    if (dialog.open) dialog.close();
  };
  trigger.addEventListener("click", () => {
    restoreFocus = true;
    previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    dialog.showModal();
    trigger.setAttribute("aria-expanded", "true");
    dialog.querySelector("nav a").focus();
  });
  document.querySelector("#close-menu").addEventListener("click", close);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const rect = dialog.getBoundingClientRect();
      if (
        event.clientX < rect.left ||
        event.clientX > rect.right ||
        event.clientY < rect.top ||
        event.clientY > rect.bottom
      )
        close();
    }
  });
  dialog.addEventListener("close", () => {
    document.body.style.overflow = previousOverflow;
    trigger.setAttribute("aria-expanded", "false");
    if (restoreFocus) trigger.focus();
  });
  const media = matchMedia("(min-width: 901px)");
  media.addEventListener("change", (e) => {
    if (e.matches) close();
  });
  return close;
}
