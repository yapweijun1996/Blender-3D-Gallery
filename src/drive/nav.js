/** Switch to another demo page without a full reload (the app listens for popstate). */
export function goToPage(page) {
  const url = new URL(location.href);
  url.searchParams.set("page", page);
  history.pushState({}, "", url);
  dispatchEvent(new PopStateEvent("popstate"));
}
