let motionPage = null;
let shelfInspectorPage = null;
import "./style.css";
import catalog from "virtual:gallery-catalog";
import demos from "virtual:gallery-demos";
import { setupPwa } from "./pwa/register.js";
import { setupMenu } from "./navigation.js";
import { getPageHeading, setupScrollToTop } from "./scroll-to-top.js";
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
const demoPages = ["game", "solar", "product-studio", "shelf-inspector", "chibi-motion", "tripo-motion"];
const motionDemos = {
  "chibi-motion": { assetId: "gjh-chibi-motion" },
  "tripo-motion": {
    assetId: "tripo-chibi-motion",
    subtitle: "Tripo rigged character",
    clips: ["idle", "wave", "nod", "jump", "dance", "run", "walk"],
    cameraPosition: [.82, .77, 3.32],
    cameraTarget: [0, .54, .47],
  },
};
const dialog = $("#viewer"),
  viewport = $("#viewport"),
  status = $("#viewer-status");
const closeMenu = setupMenu();
let viewerController, activeViewer, activeAsset, opener;
let gamePage = null,
  solarPage = null,
  productStudioPage = null,
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

const hasInteractiveControls = (asset) =>
  asset.id === "interactive-shopping-cart" || asset.id === "gjh-mall-visitor-v2" || asset.id === "gjh-visitor-v3" || asset.collectionId === "singapore-fish";
const isSearchMode = () => {
  const params = new URL(location.href).searchParams;
  return params.get("page") === "models" || (!params.has("page") && ["q", "theme", "category", "collection", "feature"].some((key) => params.has(key)));
};

function createCard(asset, searchMode) {
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
  const heading = element(searchMode ? "h3" : "h4", "asset-title");
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
  const tags = element("div", "asset-tags");
  if (asset.animations > 0) tags.append(element("span", "", "Animated GLB"));
  if (hasInteractiveControls(asset)) tags.append(element("span", "", "Interactive"));
  if (tags.childElementCount) body.append(tags);
  if (asset.downloadable !== false) body.append(download);
  card.append(link, body);
  return card;
}
function modelUrl(asset) {
  const url = new URL(location.href);
  url.searchParams.set("model", asset.slug ?? asset.id);
  url.hash = "";
  return url.pathname + url.search;
}
function renderModels() {
  const searchMode = isSearchMode();
  $("#gallery-page").classList.toggle("search-mode", searchMode);
  const feature = $("#model-feature").value;
  const filtered = assets.filter((a) =>
    matches(a, $("#model-search").value, $("#model-category").value,
      $("#model-collection").value, $("#model-theme").value) &&
    (!feature || (feature === "animated" ? a.animations > 0 : feature === "interactive" && hasInteractiveControls(a))),
  );
  const query = $("#model-search").value.trim();
  const activeFilters = [...$("#advanced-filters").querySelectorAll("select")].filter(select => select.value);
  const filtering = Boolean(query || activeFilters.length);
  $("#gallery-page .intro").hidden = searchMode;
  $("#collection-title").hidden = searchMode;
  $("#library-page-title").hidden = !searchMode;
  $("#collection").setAttribute("aria-labelledby", searchMode ? "library-page-title" : "collection-title");
  $("#filter-count").hidden = !activeFilters.length;
  $("#filter-count").textContent = String(activeFilters.length);
  $("#clear-model-filters").hidden = !filtering;
  $("#model-count").textContent = filtering
    ? `${filtered.length} of ${assets.length} models`
    : `${assets.length} models`;

  const categoryFilters = activeFilters.filter(select => ["theme", "category"].includes(select.name));
  const currentUrl = new URL(location.href);
  for (const link of $("#category-navigation").children) {
    const { key, value } = link.dataset;
    const selected = key
      ? categoryFilters.length === 1 && categoryFilters[0].name === key && categoryFilters[0].value === value
      : !categoryFilters.length;
    if (selected)
      link.setAttribute("aria-current", "true");
    else link.removeAttribute("aria-current");

    const url = new URL(currentUrl);
    for (const param of ["model", "theme", "category"]) url.searchParams.delete(param);
    url.searchParams.set("page", "models");
    if (key) url.searchParams.set(key, value);
    url.hash = "";
    link.href = url.pathname + url.search;
  }
  const fragment = document.createDocumentFragment();
  const groups = new Map();
  for (const asset of filtered) {
    if (!groups.has(asset.browseCategory)) groups.set(asset.browseCategory, []);
    groups.get(asset.browseCategory).push(asset);
  }
  for (const [category, items] of [...groups].sort(([a], [b]) => a.localeCompare(b))) {
    const section = element("section", "asset-collection");
    section.setAttribute("aria-label", category);
    const heading = element("div", "collection-title");
    heading.append(
      element(searchMode ? "h2" : "h3", "group-title", category),
      element("p", "", `${items.length} ${items.length === 1 ? "model" : "models"}`),
    );
    const grid = element("div", "asset-grid");
    for (const asset of items) grid.append(createCard(asset, searchMode));
    section.append(heading, grid);
    fragment.append(section);
  }
  if (!filtered.length)
    fragment.append(emptyState("No models found.", "Try another keyword or clear your filters."));
  $("#catalog").replaceChildren(fragment);
}
const categoryLinks = [
  ["All categories", "", ""], ["Products", "theme", "Product Packaging"],
  ["Vehicles", "category", "Vehicles"], ["Buildings", "theme", "Buildings & Architecture"],
  ["Characters", "theme", "People & Characters"], ["Retail & Mall", "theme", "Shopping Mall"],
  ["Nature", "theme", "Nature"],
];
for (const [label, key, value] of categoryLinks) {
  const link = element("a", "category-link", label);
  link.dataset.key = key;
  link.dataset.value = value;
  $("#category-navigation").append(link);
}
const heroAsset = assetById.get("proton-saga-1985");
if (heroAsset) {
  const feature = $("#featured-model");
  feature.href = `?model=${encodeURIComponent(heroAsset.slug ?? heroAsset.id)}`;
  feature.dataset.assetId = heroAsset.id;
  feature.setAttribute("aria-label", `View featured model ${heroAsset.name} in 3D`);
  feature.querySelector(".hero-frame").append(poster(heroAsset.thumbnail, heroAsset.name));
  feature.querySelector("strong").textContent = heroAsset.name;
  feature.hidden = false;
}
function renderDemos() {
  const filtered = demos.filter((d) =>
    matches(d, $("#demo-search").value, $("#demo-category").value),
  );
  $("#demo-count").textContent = filtered.length === demos.length
    ? `${demos.length} ${demos.length === 1 ? "demo" : "demos"}`
    : `${filtered.length} of ${demos.length} ${demos.length === 1 ? "demo" : "demos"}`;
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
  $("#model-theme"),
  assets.map((a) => a.browseCategory),
);
options(
  $("#model-category"),
  assets.map((a) => a.category),
);
// Keep previously shared category URLs usable without offering outdated labels for new searches.
for (const value of [...new Set(assets.map((a) => a.previousCategory).filter(Boolean))]) {
  const option = element("option", "", `${value} (previous category)`);
  option.value = value;
  option.hidden = true;
  $("#model-category").append(option);
}
for (const collection of catalog.collections) {
  const option = element("option", "", collection.name);
  option.value = collection.id;
  $("#model-collection").append(option);
}
options(
  $("#demo-category"),
  demos.map((d) => d.category),
);
$("#filter-toggle").addEventListener("click", () => {
  const panel = $("#advanced-filters");
  panel.hidden = !panel.hidden;
  $("#filter-toggle").setAttribute("aria-expanded", String(!panel.hidden));
});
function preserveLibraryMode() {
  const url = new URL(location.href);
  if (url.searchParams.has("page")) return;
  if (isSearchMode()) {
    // A shared filter-only URL still belongs to the focused library when its last filter is cleared.
    url.searchParams.set("page", "models");
    history.replaceState(history.state, "", url);
  } else {
    url.searchParams.set("page", "gallery");
    history.pushState({}, "", url);
  }
}
$("#model-filters").addEventListener("input", preserveLibraryMode);
$("#model-filters").addEventListener("reset", () => {
  preserveLibraryMode();
  $("#model-search").focus();
});
const syncModelFilters = setupFilters(
  $("#model-filters"),
  {
    q: $("#model-search"),
    theme: $("#model-theme"),
    category: $("#model-category"),
    collection: $("#model-collection"),
    feature: $("#model-feature"),
  },
  renderModels,
);
const syncDemoFilters = setupFilters(
  $("#demo-filters"),
  { dq: $("#demo-search"), dc: $("#demo-category") },
  renderDemos,
);

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
    document.querySelector(`#catalog [data-asset-id="${asset.id}"]`) ||
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
  for (const attribution of asset.details?.attribution ?? []) {
    for (const [label, value] of [["Source", attribution.url], ["License", attribution.license_url]]) {
      if (typeof value !== "string" || !value.startsWith("https://")) continue;
      const link = element("a", "", label);
      link.href = value;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      $("#viewer-description").append(" ", link);
    }
  }
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
    : document.querySelector(`#catalog [data-asset-id="${closingId}"]`) || $(".brand");
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
  return [...demoPages, "demos", "about"].includes(page) ? page : "gallery";
}
async function syncRoute() {
  const page = route(),
    previous = mountedRoute;
  const isDemo = demoPages.includes(page);
  const motion = motionDemos[page];
  const previousSearchMode = $("#gallery-page").classList.contains("search-mode");
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
    ![...demoPages, "demos", "about", "gallery", "models"].includes(raw)
  ) {
    notice.hidden = false;
    notice.textContent =
      "This page could not be found. Explore the 3D model library below.";
  }
  for (const name of ["gallery", "demos", "about", ...demoPages])
    $(`#${name}-page`).hidden = name !== page;
  $("#demo-breadcrumb").hidden = !isDemo;
  $(".footer").hidden = page === "game";
  document.body.classList.toggle("game-page", page === "game");
  const active = isDemo ? "demos" : page;
  for (const link of document.querySelectorAll("nav [data-page]")) {
    if (link.dataset.page === active) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  }
  if (page === "gallery") syncModelFilters();
  if (page === "demos") syncDemoFilters();
  const title = isDemo
    ? demos.find(demo => demo.route === `?page=${page}`).title
    : page === "gallery" ? "3D Models" : page === "demos" ? "Interactive Demos" : "About";
  document.title = `${title} · Blender 3D Gallery`;
  if (page === mountedRoute && (gamePage || solarPage || productStudioPage || shelfInspectorPage || motionPage || pageController))
    return;
  const run = ++routeRun;
  pageController?.abort();
  pageController = null;
  gamePage?.dispose();
  solarPage?.dispose();
  productStudioPage?.dispose();
  motionPage?.dispose();
  motionPage = null;
  shelfInspectorPage?.dispose();
  gamePage = solarPage = productStudioPage = shelfInspectorPage = null;
  mountedRoute = page;
  if (isDemo) {
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
      else if (page === "solar") module = await import("./solar/page.js");
      else if (motion) module = await import("./chibi-motion/page.js");
      else if (page === "shelf-inspector") module = await import("./shelf-inspector/page.js");
      else module = await import("./product-studio/page.js");
      if (run !== routeRun || controller.signal.aborted) return;
      const result =
        page === "game"
          ? await module.mountGame(root, assets, controller.signal, () =>
              navigate("gallery", true),
            )
          : motion
            ? await module.mountMotion(root, assetById.get(motion.assetId), controller.signal, { ...motion, title })
          : page === "shelf-inspector"
            ? await module.mountShelfInspector(root, controller.signal)
          : page === "product-studio"
            ? await module.mountProductStudio(root, assetById.get("demo-food-tin"), controller.signal, [assetById.get("demo-beverage-can")].filter(Boolean))
          : await module.mountSolar(
              root,
              module.solarSceneAssets(assets),
              controller.signal,
            );
      if (controller.signal.aborted) {
        result.dispose();
        return;
      }
      if (page === "game") gamePage = result;
      else if (page === "solar") solarPage = result;
      else if (motion) motionPage = result;
      else if (page === "shelf-inspector") shelfInspectorPage = result;
      else productStudioPage = result;
      window.dispatchEvent(new CustomEvent(`${page}-mounted`));
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
  const libraryViewChanged = page === "gallery" && previousSearchMode !== isSearchMode();
  if (previous && (previous !== page || libraryViewChanged)) {
    const heading = getPageHeading($(`#${page}-page`));
    heading?.setAttribute("tabindex", "-1");
    heading?.focus({ preventScroll: true });
  }
}
function navigate(page, alreadyConfirmed = false, hash = "", home = false) {
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
  else if (!home) url.searchParams.set("page", "models");
  if (home) for (const key of ["q", "theme", "category", "collection", "feature"]) url.searchParams.delete(key);
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
    navigate("gallery", false, "", true);
  }
});
window.addEventListener("popstate", () => void syncRoute());
window.addEventListener("hashchange", () => void syncRoute());
void syncRoute();
