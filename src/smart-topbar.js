const TOP_THRESHOLD = 80;
const SCROLL_DELTA = 8;

export function setupSmartTopbar() {
  const bar = document.querySelector(".topbar");
  let lastY = 0;
  const reveal = () => {
    delete bar.dataset.scrollHidden;
    lastY = Math.max(0, scrollY);
  };
  const dialogOpen = () => document.querySelector("dialog[open]");

  window.addEventListener("scroll", () => {
    if (!bar.hasAttribute("data-smart")) return;
    const y = Math.max(0, scrollY);
    if (y <= TOP_THRESHOLD || bar.matches(":focus-within") || dialogOpen()) {
      reveal();
    } else if (Math.abs(y - lastY) >= SCROLL_DELTA) {
      bar.toggleAttribute("data-scroll-hidden", y > lastY);
      lastY = y;
    }
  }, { passive: true });
  bar.addEventListener("focusin", reveal);
  new MutationObserver(() => {
    if (dialogOpen()) reveal();
  }).observe(document.body, {
    subtree: true,
    attributes: true,
    attributeFilter: ["open"],
  });

  return (enabled) => {
    if (bar.hasAttribute("data-smart") === enabled) return;
    bar.toggleAttribute("data-smart", enabled);
    reveal();
  };
}
