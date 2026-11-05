export function setupScrollToTop(getPage) {
  const button = document.createElement("button");
  button.id = "scroll-to-top";
  button.className = "scroll-to-top";
  button.type = "button";
  button.textContent = "↑ Back to top";
  button.hidden = true;
  document.body.append(button);
  let queued = false;
  const update = () => {
    queued = false;
    const staticPage = ["gallery", "demos", "about"].includes(getPage());
    const overlayOpen =
      document.querySelector("dialog[open], .pwa-notice:not([hidden])") ||
      document.body.classList.contains("pwa-updating");
    const longPage = document.documentElement.scrollHeight > innerHeight * 1.5;
    const hidden =
      !staticPage ||
      overlayOpen ||
      !longPage ||
      scrollY < Math.max(320, innerHeight * 0.8);
    if (button.hidden !== Boolean(hidden)) button.hidden = Boolean(hidden);
  };
  const refresh = () => {
    // This visibility check must not add a second animation frame to a demo.
    if (!["gallery", "demos", "about"].includes(getPage())) {
      if (!button.hidden) button.hidden = true;
      return;
    }
    if (!queued) {
      queued = true;
      queueMicrotask(update);
    }
  };
  window.addEventListener("scroll", refresh, { passive: true });
  window.addEventListener("resize", refresh);
  const observer = new MutationObserver(refresh);
  observer.observe(document.body, {
    subtree: true,
    attributes: true,
    attributeFilter: ["open", "hidden", "class"],
  });
  button.addEventListener("click", () => {
    window.scrollTo({
      top: 0,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
    });
    const heading = document.querySelector("main:not([hidden]) h1");
    heading?.setAttribute("tabindex", "-1");
    heading?.focus({ preventScroll: true });
  });
  refresh();
  return refresh;
}
