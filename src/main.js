import "./style.css";
import catalog from "virtual:gallery-catalog";
import demos from "virtual:gallery-demos";
import { setupPwa } from "./pwa/register.js";
import { setupMenu } from "./navigation.js";
import { setupScrollToTop } from "./scroll-to-top.js";
import {
  element,
  poster,
  options,
  matches,
  emptyState,
  setupFilters,
  formatBytes,
} from "./library/browse.js";

const $ = (selector) => document.querySelector(selector);
const assets = catalog.collections.flatMap((c) => c.assets);
const assetById = new Map(
  assets.flatMap((a) => [
    [a.id, a],
    [a.slug ?? a.id, a],
  ]),
);
const dialog = $("#viewer"),
  viewport = $("#viewport"),
  status = $("#viewer-status");
const closeMenu = setupMenu();
let viewerController, activeViewer, activeAsset, opener;
let gamePage = null,
  solarPage = null,
  pageController = null,
  routeRun = 0,
  mountedRoute = null;
let lastRouteUrl = location.href;
let modelReturnUrl = null;
const notice = $("#route-notice");
let pwaState = null;
const refreshScrollToTop = setupScrollToTop(route);

function refreshDemoOfflineStatus() {
  for (const badge of document.querySelectorAll(".demo-offline-status")) {
    const isGame = badge.dataset.demoId === "game";
    badge.textContent = !isGame
      ? "Requires an online connection · not included in the offline Game pack"
      : pwaState?.offlinePack === "ready"
        ? "Offline ready · verified Game pack saved on this device"
        : pwaState?.offlinePack === "preparing"
          ? "Preparing the offline Game pack…"
          : "Offline Game pack not ready · prepare it in Game while connected";
  }
}

function createCard(asset) {
  const card = element("article", "asset-card");
  const link = element("a", "asset-image");
  link.href = modelUrl(asset);
  link.dataset.assetId = asset.id;
  link.setAttribute("aria-label", `Preview ${asset.name} in 3D`);
  link.append(
    poster(asset.thumbnail, asset.name),
    element("span", "asset-image-label", "VIEW IN 3D ↗"),
  );
  const body = element("div", "asset-body");
  const heading = element("h4");
  const name = element("a", "", asset.name);
  name.href = modelUrl(asset);
  name.dataset.assetId = asset.id;
  heading.append(name);
  const download = element("a", "asset-download", "Download GLB ↓");
  download.href = asset.file;
  download.download = `${asset.id}.glb`;
  download.setAttribute("aria-label", `Download ${asset.name} GLB`);
  body.append(
    element("p", "asset-category", asset.category),
    heading,
    element(
      "p",
      "asset-metrics",
      `${asset.triangles.toLocaleString()} triangles · ${formatBytes(asset.bytes)}`,
    ),
  );
  if (asset.downloadable !== false) body.append(download);
  card.append(link, body);
  return card;
}
function modelUrl(asset) {
  const url = new URL(location.href);
  url.searchParams.delete("page");
  url.searchParams.set("model", asset.slug ?? asset.id);
  url.hash = "";
  return url.pathname + url.search;
}
function renderModels() {
  const filtered = assets.filter((a) =>
    matches(
      a,
      $("#model-search").value,
      $("#model-category").value,
      $("#model-collection").value,
    ),
  );
  $("#model-count").textContent =
    `${filtered.length} ${filtered.length === 1 ? "model" : "models"} · ${assets.length} in the library`;
  const fragment = document.createDocumentFragment();
  for (const collection of catalog.collections) {
    const items = filtered.filter(
      (a) =>
        a.collectionId === collection.id ||
        collection.assets.some((original) => original.id === a.id),
    );
    if (!items.length) continue;
    const section = element("section", "asset-collection");
    section.setAttribute("aria-label", collection.name);
    const heading = element("div", "collection-title");
    heading.append(
      element("h3", "", collection.name),
      element("p", "", collection.description),
    );
    const grid = element("div", "asset-grid");
    for (const asset of items) grid.append(createCard(asset));
    section.append(heading, grid);
    fragment.append(section);
  }
  if (!filtered.length)
    fragment.append(
      emptyState(
        "No models found.",
        "Try another keyword or clear your filters.",
      ),
    );
  $("#catalog").replaceChildren(fragment);
}
function renderDemos() {
  const filtered = demos.filter((d) =>
    matches(d, $("#demo-search").value, $("#demo-category").value),
  );
  $("#demo-count").textContent =
    `${filtered.length} ${filtered.length === 1 ? "demo" : "demos"} · ${demos.length} to explore`;
  const cards = filtered.map((demo) => {
    const card = element("article", "demo-card");
    card.dataset.demoId = demo.id;
    const image = element("a", "asset-image demo-image");
    image.href = demo.route;
    image.dataset.page = new URL(demo.route, location.href).searchParams.get(
      "page",
    );
    image.setAttribute("aria-label", `Launch ${demo.title}`);
    image.append(poster(demo.thumbnail, demo.title));
    const body = element("div", "demo-body");
    const heading = element("h2");
    const link = element("a", "", demo.title);
    link.href = demo.route;
    link.dataset.page = image.dataset.page;
    heading.append(link);
    body.append(
      element("p", "asset-category", demo.category),
      heading,
      element("p", "demo-description", demo.description),
      element(
        "p",
        "demo-technology",
        (demo.technologies ?? demo.technology ?? []).join(" · "),
      ),
      element(
        "p",
        "demo-availability",
        demo.status === "available"
          ? "Available in your browser"
          : "Currently unavailable",
      ),
    );
    const offlineStatus = element("p", "demo-offline-status");
    offlineStatus.dataset.demoId = demo.id;
    body.append(offlineStatus);
    if (demo.status === "available") {
      const launch = element("a", "outline-button", `Launch ${demo.title} ↗`);
      launch.href = demo.route;
      launch.dataset.page = image.dataset.page;
      body.append(launch);
    }
    if (demo.status !== "available") {
      image.removeAttribute("href");
      image.removeAttribute("data-page");
      link.removeAttribute("href");
      link.removeAttribute("data-page");
    }
    card.append(image, body);
    return card;
  });
  $("#demo-catalog").replaceChildren(
    ...(cards.length
      ? cards
      : [
          emptyState(
            "No demos found.",
            "Try another keyword or clear your filters.",
          ),
        ]),
  );
  refreshDemoOfflineStatus();
}
options(
  $("#model-category"),
  assets.map((a) => a.category),
);
for (const collection of catalog.collections) {
  const option = element("option", "", collection.name);
  option.value = collection.id;
  $("#model-collection").append(option);
}
options(
  $("#demo-category"),
  demos.map((d) => d.category),
);
const syncModelFilters = setupFilters(
  $("#model-filters"),
  {
    q: $("#model-search"),
    category: $("#model-category"),
    collection: $("#model-collection"),
  },
  renderModels,
);
const syncDemoFilters = setupFilters(
  $("#demo-filters"),
  { dq: $("#demo-search"), dc: $("#demo-category") },
  renderDemos,
);
syncModelFilters();
syncDemoFilters();

function metadata(asset) {
  const dl = $("#viewer-metadata");
  dl.replaceChildren();
  const rows = [
    ["Collection", asset.collectionName],
    ["Category", asset.category],
    ["Format", asset.format ?? "GLB"],
    ["File size", formatBytes(asset.bytes)],
    ["Triangles", asset.triangles?.toLocaleString()],
    ["Vertices", asset.vertices?.toLocaleString()],
    ["Materials", asset.materials],
    ["Animations", asset.animations === 0 ? "None in GLB" : asset.animations],
    [
      "License",
      asset.license ??
        asset.details?.rights ??
        "Redistribution terms pending owner decision.",
    ],
  ];
  for (const [label, value] of rows)
    if (value !== undefined && value !== null && value !== "") {
      const group = element("div");
      group.append(element("dt", "", label), element("dd", "", String(value)));
      dl.append(group);
    }
}
async function openViewer(asset, trigger, updateUrl = true) {
  viewerController?.abort();
  activeViewer?.dispose();
  activeViewer = null;
  activeAsset = asset;
  viewerController = new AbortController();
  const { signal } = viewerController;
  opener =
    trigger ||
    document.querySelector(`[data-asset-id="${asset.id}"]`) ||
    $(".brand");
  $("#viewer-title").textContent = asset.name;
  $("#viewer-category").textContent =
    `${asset.category.toUpperCase()} / INTERACTIVE 3D`;
  const notes = [
    asset.description,
    asset.details?.accuracy_notes,
    ...(asset.details?.attribution ?? []).map((a) => a.credit),
  ].filter(Boolean);
  $("#viewer-description").textContent = [...new Set(notes)].join(" ");
  metadata(asset);
  $("#viewer-download").href = asset.file;
  $("#viewer-download").download = `${asset.id}.glb`;
  $("#viewer-download").hidden = asset.downloadable === false;
  const preview = $("#viewer-poster");
  preview.hidden = false;
  preview.src = asset.thumbnail;
  preview.alt = `${asset.name} reference preview`;
  preview.onerror = () => {
    preview.hidden = true;
  };
  $("#reset-view").disabled = true;
  $("#retry-view").hidden = true;
  $("#fullscreen-view").hidden = !viewport.requestFullscreen;
  const related = $("#viewer-related");
  related.replaceChildren(element("h3", "", "From the same collection"));
  const links = element("div", "related-links");
  for (const other of assets
    .filter((a) => a.collectionId === asset.collectionId && a.id !== asset.id)
    .slice(0, 3)) {
    const link = element("a", "text-link", other.name + " ↗");
    link.href = modelUrl(other);
    link.dataset.assetId = other.id;
    links.append(link);
  }
  related.append(links);
  if (!dialog.open) {
    dialog.showModal();
    document.body.classList.add("viewer-open");
  }
  $("#close-viewer").focus();
  if (updateUrl) {
    if (!new URL(location.href).searchParams.has("model"))
      modelReturnUrl = location.href;
    history.pushState({}, "", modelUrl(asset));
  }
  status.textContent = "Loading the 3D model…";
  try {
    const { default: createViewer } = await import("./viewer.js");
    if (signal.aborted) return;
    const viewer = await createViewer(
      viewport,
      asset.file,
      status,
      signal,
      asset,
    );
    if (signal.aborted) {
      viewer.dispose();
      return;
    }
    activeViewer = viewer;
    preview.hidden = true;
    $("#reset-view").disabled = false;
    $("#reset-view").onclick = viewer.reset;
  } catch (error) {
    if (signal.aborted) return;
    status.textContent =
      "3D view unavailable. The preview and model information are still available.";
    $("#retry-view").hidden = false;
  }
}
function closeViewer(updateUrl = true) {
  const closingId = activeAsset?.id;
  viewerController?.abort();
  activeViewer?.dispose();
  activeViewer = null;
  activeAsset = null;
  $("#reset-view").onclick = null;
  if (dialog.open) dialog.close();
  document.body.classList.remove("viewer-open");
  if (updateUrl) {
    const url = new URL(location.href);
    url.searchParams.delete("model");
    history.replaceState({}, "", modelReturnUrl ?? url);
  }
  modelReturnUrl = null;
  const restore = opener?.isConnected
    ? opener
    : document.querySelector(`[data-asset-id="${closingId}"]`) || $(".brand");
  restore?.focus();
}
$("#close-viewer").addEventListener("click", () => closeViewer());
dialog.addEventListener("cancel", (e) => {
  e.preventDefault();
  closeViewer();
});
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (
      event.clientX < r.left ||
      event.clientX > r.right ||
      event.clientY < r.top ||
      event.clientY > r.bottom
    )
      closeViewer();
  }
});
$("#retry-view").addEventListener("click", () => {
  if (activeAsset) void openViewer(activeAsset, opener, false);
});
$("#fullscreen-view").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await viewport.requestFullscreen();
  } catch {
    status.textContent = "Fullscreen is unavailable in this browser.";
  }
});
function syncModelUrl() {
  const id = new URL(location.href).searchParams.get("model");
  if (id && assetById.has(id)) {
    if (activeAsset?.id !== assetById.get(id).id)
      void openViewer(assetById.get(id), null, false);
  } else {
    if (dialog.open) closeViewer(false);
    if (id) {
      notice.hidden = false;
      notice.textContent =
        "This model could not be found. Browse the library below or try another search.";
    }
  }
}

const pwaRuntime = setupPwa(() => gamePage);
pwaState = pwaRuntime.getState?.() ?? null;
refreshDemoOfflineStatus();
window.addEventListener("pwa-state-change", (event) => {
  pwaState = event.detail;
  refreshDemoOfflineStatus();
  refreshScrollToTop();
});
function route() {
  const url = new URL(location.href);
  const page = url.searchParams.get("page");
  if (!page && url.hash === "#about") return "about";
  return ["game", "solar", "demos", "about"].includes(page) ? page : "gallery";
}
async function syncRoute() {
  const page = route(),
    previous = mountedRoute;
  refreshScrollToTop();
  if (page !== "game" && gamePage && !gamePage.beforeLeave()) {
    history.replaceState({}, "", lastRouteUrl);
    return;
  }
  lastRouteUrl = location.href;
  notice.hidden = true;
  const raw = new URL(location.href).searchParams.get("page");
  if (
    raw &&
    !["game", "solar", "demos", "about", "gallery", "models"].includes(raw)
  ) {
    notice.hidden = false;
    notice.textContent =
      "This page could not be found. Explore the 3D model library below.";
  }
  for (const name of ["gallery", "demos", "about", "game", "solar"])
    $(`#${name}-page`).hidden = name !== page;
  $("#demo-breadcrumb").hidden = !["game", "solar"].includes(page);
  $(".footer").hidden = page === "game";
  document.body.classList.toggle("game-page", page === "game");
  const active = ["game", "solar"].includes(page) ? "demos" : page;
  for (const link of document.querySelectorAll("nav [data-page]")) {
    if (link.dataset.page === active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  syncModelFilters();
  syncDemoFilters();
  document.title = `${page === "gallery" ? "3D Models" : page === "demos" ? "Interactive Demos" : page === "game" ? "Game" : page === "solar" ? "Solar System" : "About"} · Blender 3D Gallery`;
  if (page === mountedRoute && (gamePage || solarPage || pageController))
    return;
  const run = ++routeRun;
  pageController?.abort();
  pageController = null;
  gamePage?.dispose();
  solarPage?.dispose();
  gamePage = solarPage = null;
  mountedRoute = page;
  if (page === "game" || page === "solar") {
    if (dialog.open) closeViewer(false);
    const cleanUrl = new URL(location.href);
    cleanUrl.searchParams.delete("model");
    history.replaceState({}, "", cleanUrl);
    const controller = new AbortController();
    pageController = controller;
    const root = $(`#${page}-page`);
    root.replaceChildren(
      element("p", "route-loading", "Loading the experience…"),
    );
    try {
      let module;
      if (page === "game") module = await import("./game/page.js");
      else module = await import("./solar/page.js");
      if (run !== routeRun || controller.signal.aborted) return;
      const result =
        page === "game"
          ? await module.mountGame(root, assets, controller.signal, () =>
              navigate("gallery", true),
            )
          : await module.mountSolar(
              root,
              assets.filter((a) => a.family === "solar-system"),
              controller.signal,
            );
      if (controller.signal.aborted) {
        result.dispose();
        return;
      }
      if (page === "game") gamePage = result;
      else solarPage = result;
      window.dispatchEvent(
        new CustomEvent(page === "game" ? "game-mounted" : "solar-mounted"),
      );
    } catch (error) {
      if (controller.signal.aborted) return;
      controller.abort();
      pageController = null;
      root.replaceChildren(
        emptyState(
          "This experience could not start.",
          "Reconnect and try again, or return to Interactive Demos.",
        ),
      );
      const retry = element("button", "outline-button", "Retry experience");
      retry.addEventListener("click", () => void syncRoute());
      root.append(retry);
    }
  } else {
    if (dialog.open && page !== "gallery") closeViewer(false);
    if (page === "gallery") syncModelUrl();
  }
  if (previous && previous !== page) {
    const heading = $(`#${page}-page h1`);
    heading?.setAttribute("tabindex", "-1");
    heading?.focus({ preventScroll: true });
  }
}
function navigate(page, alreadyConfirmed = false, hash = "") {
  if (
    page !== "game" &&
    gamePage &&
    !alreadyConfirmed &&
    !gamePage.beforeLeave()
  )
    return;
  // The game itself has already saved/confirmed on its explicit leave action.
  if (page !== "game" && gamePage) {
    pageController?.abort();
    pageController = null;
    gamePage.dispose();
    gamePage = null;
  }
  const url = new URL(location.href);
  url.searchParams.delete("model");
  url.searchParams.delete("page");
  if (page !== "gallery") url.searchParams.set("page", page);
  else url.searchParams.set("page", "models");
  url.hash = hash;
  history.pushState({}, "", url);
  closeMenu(false);
  window.scrollTo(0, 0);
  void syncRoute().then(() => {
    if (hash) document.querySelector(hash)?.scrollIntoView();
  });
}
document.addEventListener("click", (event) => {
  const link = event.target.closest("a");
  if (
    !link ||
    event.defaultPrevented ||
    event.button !== 0 ||
    event.metaKey ||
    event.ctrlKey ||
    event.shiftKey ||
    event.altKey
  )
    return;
  if (link.dataset.assetId) {
    event.preventDefault();
    void openViewer(assetById.get(link.dataset.assetId), link);
    return;
  }
  if (link.dataset.page) {
    event.preventDefault();
    navigate(link.dataset.page, false, link.hash);
    return;
  }
  if (link.classList.contains("brand")) {
    event.preventDefault();
    navigate("gallery");
  }
});
window.addEventListener("popstate", () => void syncRoute());
window.addEventListener("hashchange", () => void syncRoute());
void syncRoute();
