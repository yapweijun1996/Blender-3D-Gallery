let motionPage = null;
let dressupPage = null;
let drivePage = null;
let worldPage = null;
let mrtPage = null;
let commercePage = null;
let cityPage = null;
let shelfInspectorPage = null;
import "virtual:gallery-palette-colors.css";
import "./style.css";
import catalog from "virtual:gallery-catalog";
import demos from "virtual:gallery-demos";
import { demoRoutes } from "./demo-routes.js";
import { interactionKind } from "./model-interaction.js";
import { setupPwa } from "./pwa/register.js";
import { updateLabelVersion } from "./pwa/update-state.js";
import { pwaCopy } from "./pwa/copy.js";
import { getLanguage, localize, localizeTree, number, onLanguageChange, plural, syncLanguageAcrossTabs, t } from "./i18n/index.js";
import { setupLanguagePicker } from "./i18n/picker.js";
import { setupMenu } from "./navigation.js";
import { setupSmartTopbar } from "./smart-topbar.js";
import { setupPalettePicker } from "./design/palette-picker.js";
import { getPageHeading, setupScrollToTop } from "./scroll-to-top.js";
import {
  categoryKey,
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
const demoPages = Object.keys(demoRoutes);
const demoLoaders = import.meta.glob("./*/page.js");
const demosByRoute = new Map(demos.map(demo => [demo.route, demo]));
const motionDemos = {
  "chibi-motion": { assetId: "gjh-chibi-motion" },
  "tripo-motion": {
    assetId: "tripo-chibi-motion",
    subtitleKey: "motion.tripoSubtitle",
    clips: ["idle", "wave", "nod", "jump", "dance", "run", "walk"],
    cameraPosition: [.82, .77, 3.32],
    cameraTarget: [0, .54, .47],
  },
};
const dialog = $("#viewer"),
  viewport = $("#viewport"),
  status = $("#viewer-status");
localizeTree();
syncLanguageAcrossTabs();
setupLanguagePicker();
const closeMenu = setupMenu();
const setSmartTopbar = setupSmartTopbar();
setupPalettePicker();
let viewerController, activeViewer, activeAsset, opener;
let gamePage = null,
  solarPage = null,
  productStudioPage = null,
  pageController = null,
  routeRun = 0,
  mountedRoute = null,
  mountedTunnel = false;
let lastRouteUrl = location.href;
let modelReturnUrl = null;
const notice = $("#route-notice");
const noticeText = $("#route-notice-text");
let pwaState = null;
const refreshScrollToTop = setupScrollToTop(route);

function refreshDemoOfflineStatus() {
  for (const badge of document.querySelectorAll(".demo-offline-status")) {
    const isGame = badge.dataset.demoId === "game";
    localize(badge, !isGame
      ? "demos.onlineOnly"
      : pwaState?.offlinePack === "ready"
        ? "demos.offlineReady"
        : pwaState?.offlinePack === "preparing"
          ? "demos.preparing"
          : "demos.notReady");
  }
}

const hasInteractiveControls = (asset) => interactionKind(asset) !== null;
const isSearchMode = () => {
  const params = new URL(location.href).searchParams;
  return params.get("page") === "models" || (!params.has("page") && ["q", "theme", "category", "collection", "feature"].some((key) => params.has(key)));
};

const categoryLabel = value => t(categoryKey(value));
const demoCategoryKey = value => `demos.category.${value.toLowerCase()}`;
const demoTitleKey = demo => `demo.${demo.id}.title`;

function createCard(asset, searchMode) {
  const card = element("article", "asset-card");
  const link = element("a", "asset-image");
  link.href = modelUrl(asset);
  link.dataset.assetId = asset.id;
  link.setAttribute("aria-label", t("library.preview", { name: asset.name }));
  link.append(
    poster(asset.thumbnail, asset.name),
    element("span", "asset-image-label", t("library.view")),
  );
  const body = element("div", "asset-body");
  const heading = element(searchMode ? "h3" : "h4", "asset-title");
  const name = element("a", "", asset.name);
  name.href = modelUrl(asset);
  name.dataset.assetId = asset.id;
  heading.append(name);
  const download = element("a", "asset-download", t("library.download"));
  download.href = asset.file;
  download.download = `${asset.id}.glb`;
  download.setAttribute("aria-label", t("library.downloadAsset", { name: asset.name }));
  body.append(
    element("p", "asset-category", categoryLabel(asset.category)),
    heading,
    element(
      "p",
      "asset-metrics",
      t("library.metrics", { triangles: number(asset.triangles), size: formatBytes(asset.bytes) }),
    ),
  );
  const tags = element("div", "asset-tags");
  if (asset.animations > 0) tags.append(element("span", "", t("library.animatedGlb")));
  if (hasInteractiveControls(asset)) tags.append(element("span", "", t("library.interactive")));
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
      $("#model-collection").value, $("#model-theme").value,
      [categoryLabel(a.category), categoryLabel(a.browseCategory)]) &&
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
  $("#filter-count").textContent = number(activeFilters.length);
  $("#clear-model-filters").hidden = !filtering;
  $("#model-count").textContent = filtering
    ? plural("library.filteredCount", assets.length, { count: number(filtered.length), total: number(assets.length) })
    : plural("library.modelCount", assets.length);

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
    section.setAttribute("aria-label", categoryLabel(category));
    const heading = element("div", "collection-title");
    heading.append(
      element(searchMode ? "h2" : "h3", "group-title", categoryLabel(category)),
      element("p", "", plural("library.modelCount", items.length)),
    );
    const grid = element("div", "asset-grid");
    for (const asset of items) grid.append(createCard(asset, searchMode));
    section.append(heading, grid);
    fragment.append(section);
  }
  if (!filtered.length)
    fragment.append(emptyState("library.empty", "common.clearHint"));
  $("#catalog").replaceChildren(fragment);
}
const categoryLinks = [
  ["library.allCategories", "", ""], ["library.products", "theme", "Product Packaging"],
  ["category.vehicles", "category", "Vehicles"], ["library.buildings", "theme", "Buildings & Architecture"],
  ["category.characters", "theme", "People & Characters"], ["library.retailMall", "theme", "Shopping Mall"],
  ["category.nature", "theme", "Nature"],
];
for (const [label, key, value] of categoryLinks) {
  const link = localize(element("a", "category-link"), label);
  link.dataset.key = key;
  link.dataset.value = value;
  $("#category-navigation").append(link);
}
const heroAsset = assetById.get("proton-saga-1985");
if (heroAsset) {
  const feature = $("#featured-model");
  feature.href = `?model=${encodeURIComponent(heroAsset.slug ?? heroAsset.id)}`;
  feature.dataset.assetId = heroAsset.id;
  localize(feature, "gallery.featuredView", { name: heroAsset.name }, "aria-label");
  feature.querySelector(".hero-frame").append(poster(heroAsset.thumbnail, heroAsset.name, true));
  feature.querySelector("strong").textContent = heroAsset.name;
  feature.hidden = false;
}
function renderDemos() {
  const filtered = demos.filter(demo =>
    matches(demo, $("#demo-search").value, $("#demo-category").value, "", "", [
      t(demoTitleKey(demo)), t(`demo.${demo.id}.description`), t(demoCategoryKey(demo.category)),
      ...demo.tags.map(tag => t(`demos.tag.${tag.toLowerCase()}`)),
    ]),
  );
  $("#demo-count").textContent = filtered.length === demos.length
    ? plural("demos.count", demos.length)
    : plural("demos.filteredCount", demos.length, { count: number(filtered.length), total: number(demos.length) });
  const cards = filtered.map((demo) => {
    const title = t(demoTitleKey(demo));
    const card = element("article", "demo-card");
    card.dataset.demoId = demo.id;
    const image = element("a", "asset-image demo-image");
    image.href = demo.route;
    image.dataset.page = new URL(demo.route, location.href).searchParams.get(
      "page",
    );
    image.setAttribute("aria-label", t("demos.launch", { title }));
    image.append(poster(demo.thumbnail, title));
    const body = element("div", "demo-body");
    const heading = element("h2");
    const link = element("a", "", title);
    link.href = demo.route;
    link.dataset.page = image.dataset.page;
    heading.append(link);
    body.append(
      element("p", "asset-category", t(demoCategoryKey(demo.category))),
      heading,
      element("p", "demo-description", t(`demo.${demo.id}.description`)),
      element(
        "p",
        "demo-technology",
        (demo.technologies ?? demo.technology ?? []).join(" · "),
      ),
      element(
        "p",
        "demo-availability",
        demo.status === "available"
          ? t("demos.available")
          : t("demos.unavailable"),
      ),
    );
    const offlineStatus = element("p", "demo-offline-status");
    offlineStatus.dataset.demoId = demo.id;
    body.append(offlineStatus);
    if (demo.status === "available") {
      const launch = element("a", "outline-button", t("demos.launchLink", { title }));
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
            "demos.empty",
            "common.clearHint",
          ),
        ]),
  );
  refreshDemoOfflineStatus();
}
options(
  $("#model-theme"),
  assets.map((a) => a.browseCategory), categoryKey,
);
options(
  $("#model-category"),
  assets.map((a) => a.category), categoryKey,
);
// Keep previously shared category URLs usable without offering outdated labels for new searches.
for (const value of [...new Set(assets.map((a) => a.previousCategory).filter(Boolean))]) {
  const option = element("option");
  option.dataset.previousCategory = value;
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
  demos.map((d) => d.category), demoCategoryKey,
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
    ["library.collection", asset.collectionName],
    ["library.category", categoryLabel(asset.category)],
    ["viewer.format", asset.format ?? "GLB"],
    ["viewer.size", formatBytes(asset.bytes)],
    ["viewer.triangles", asset.triangles == null ? null : number(asset.triangles)],
    ["viewer.vertices", asset.vertices == null ? null : number(asset.vertices)],
    ["viewer.materials", asset.materials],
    ["viewer.animations", asset.animations === 0 ? t("viewer.noAnimation") : asset.animations],
    [
      "viewer.license",
      asset.license ??
        asset.details?.rights ??
        t("viewer.rightsPending"),
    ],
  ];
  for (const [label, value] of rows)
    if (value !== undefined && value !== null && value !== "") {
      const group = element("div");
      group.append(element("dt", "", t(label)), element("dd", "", String(value)));
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
  const title = localize($("#viewer-title"));
  title.textContent = asset.name;
  refreshViewerMetadata(asset);
  const notes = [
    asset.description,
    asset.details?.accuracy_notes,
    ...(asset.details?.attribution ?? []).map((a) => a.credit),
  ].filter(Boolean);
  $("#viewer-description").textContent = [...new Set(notes)].join(" ");
  for (const attribution of asset.details?.attribution ?? []) {
    for (const [label, value] of [["viewer.source", attribution.url], ["viewer.license", attribution.license_url]]) {
      if (typeof value !== "string" || !value.startsWith("https://")) continue;
      const link = localize(element("a"), label);
      link.href = value;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      $("#viewer-description").append(" ", link);
    }
  }
  $("#viewer-download").href = asset.file;
  $("#viewer-download").download = `${asset.id}.glb`;
  $("#viewer-download").hidden = asset.downloadable === false;
  const preview = $("#viewer-poster");
  preview.hidden = false;
  preview.src = asset.thumbnail;
  localize(preview, "viewer.poster", { name: asset.name }, "alt");
  preview.onerror = () => {
    preview.hidden = true;
  };
  $("#reset-view").disabled = true;
  $("#retry-view").hidden = true;
  $("#fullscreen-view").hidden = !viewport.requestFullscreen;
  const related = $("#viewer-related");
  related.replaceChildren(localize(element("h3"), "viewer.related"));
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
  localize(status, "viewer.loading");
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
    localize(status, "viewer.unavailable");
    $("#retry-view").hidden = false;
    void pwaRuntime.checkForUpdate(true);
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
    localize(status, "viewer.noFullscreen");
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
      localize(noticeText, "viewer.missingModel");
    }
  }
}

const pwaRuntime = setupPwa(() => gamePage);
pwaState = pwaRuntime.getState?.() ?? null;
refreshDemoOfflineStatus();

function refreshVersion() {
  const versionText = pwaCopy.version(__APP_VERSION__);
  for (const chip of document.querySelectorAll("[data-app-version]")) {
    chip.textContent = versionText;
    chip.title = pwaCopy.appVersion(versionText);
  }
  $(".topbar-update-short").textContent = pwaCopy.update;
}

function refreshUpdateActions() {
  const { update, updateReady, updateVersion } = pwaState;
  const target = updateLabelVersion(updateVersion, __APP_VERSION__);
  const label = target ? pwaCopy.updateTo(target) : pwaCopy.update;
  for (const button of document.querySelectorAll("[data-pwa-update]")) {
    button.hidden = !updateReady;
    const busy = update !== "available" && update !== "error";
    if (busy) button.setAttribute("aria-disabled", "true");
    else button.removeAttribute("aria-disabled");
    button.setAttribute("aria-label", label);
    const text = button.querySelector(".topbar-update-full") ?? button;
    if (text.textContent !== label) text.textContent = label;
  }
}

function offerUpdate(container) {
  const button = element("button", "outline-button pwa-inline-update");
  button.type = "button";
  button.dataset.pwaUpdate = "";
  container.append(button);
  refreshUpdateActions();
  void pwaRuntime.checkForUpdate(true);
}

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-pwa-update]");
  if (button && button.getAttribute("aria-disabled") !== "true")
    void pwaRuntime.beginUpdate();
});
refreshUpdateActions();
window.addEventListener("pwa-state-change", (event) => {
  pwaState = event.detail;
  refreshDemoOfflineStatus();
  refreshScrollToTop();
  refreshUpdateActions();
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
  const tunnel = page === "sg-world" && new URLSearchParams(location.search).get("tunnel") === "fort-canning";
  const worldDriveChanged = mountedTunnel !== tunnel;
  const isDemo = demoPages.includes(page);
  const motion = motionDemos[page];
  const dressup = page === "chibi-dressup";
  const drive = page === "drive-jb";
  const city = page === "sg-heartland";
  const world = page === "sg-world";
  const mrt = page === "sg-mrt";
  const commerce = page === "commerce-hub";
  const previousSearchMode = $("#gallery-page").classList.contains("search-mode");
  refreshScrollToTop();
  if (page !== "game" && gamePage && !gamePage.beforeLeave()) {
    history.replaceState({}, "", lastRouteUrl);
    return;
  }
  lastRouteUrl = location.href;
  setSmartTopbar(!isDemo);
  notice.hidden = true;
  notice.querySelector(".pwa-inline-update")?.remove();
  const raw = new URL(location.href).searchParams.get("page");
  if (
    raw &&
    ![...demoPages, "demos", "about", "gallery", "models"].includes(raw)
  ) {
    notice.hidden = false;
    localize(noticeText, "shell.missingRoute");
    offerUpdate(notice);
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
  refreshTitle(page, tunnel);
  if (page === mountedRoute && !worldDriveChanged && (gamePage || solarPage || productStudioPage || shelfInspectorPage || motionPage || dressupPage || drivePage || cityPage || worldPage || mrtPage || commercePage || pageController))
    return;
  const run = ++routeRun;
  pageController?.abort();
  pageController = null;
  gamePage?.dispose();
  solarPage?.dispose();
  productStudioPage?.dispose();
  motionPage?.dispose();
  dressupPage?.dispose();
  drivePage?.dispose();
  cityPage?.dispose();
  worldPage?.dispose();
  mrtPage?.dispose();
  commercePage?.dispose();
  commercePage = null;
  motionPage = dressupPage = drivePage = cityPage = worldPage = mrtPage = null;
  shelfInspectorPage?.dispose();
  gamePage = solarPage = productStudioPage = shelfInspectorPage = null;
  mountedRoute = page;
  mountedTunnel = tunnel;
  if (isDemo) {
    if (dialog.open) closeViewer(false);
    const cleanUrl = new URL(location.href);
    cleanUrl.searchParams.delete("model");
    history.replaceState({}, "", cleanUrl);
    const controller = new AbortController();
    pageController = controller;
    const root = $(`#${page}-page`);
    root.replaceChildren(
      localize(element("p", "route-loading"), "shell.loadingExperience"),
    );
    try {
      const module = await demoLoaders[demoRoutes[page]]();
      if (run !== routeRun || controller.signal.aborted) return;
      const demo = demosByRoute.get(`?page=${page}`);
      const result =
        page === "game"
          ? await module.mountGame(root, assets, controller.signal, () =>
              navigate("gallery", true),
            )
          : motion
            ? await module.mountMotion(root, assetById.get(motion.assetId), controller.signal, { ...motion, titleKey: demoTitleKey(demo) })
          : page === "shelf-inspector"
            ? await module.mountShelfInspector(root, controller.signal)
          : page === "product-studio"
            ? await module.mountProductStudio(root, assetById.get("demo-food-tin"), controller.signal, [assetById.get("demo-beverage-can")].filter(Boolean))
          : dressup
            ? await module.mountDressup(root, demo.thumbnail, controller.signal)
          : drive
            ? await module.mountDrive(root, demo.thumbnail, controller.signal)
          : city
            ? await module.mountCity(root, demo.thumbnail, controller.signal)
          : world
            ? await module.mountWorld(root, demo.thumbnail, controller.signal, { tunnel })
          : mrt
            ? await module.mountMrt(root, demo.thumbnail, controller.signal)
          : commerce
            ? await module.mountCommerceHub(root, assets, controller.signal)
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
      else if (dressup) dressupPage = result;
      else if (drive) drivePage = result;
      else if (city) cityPage = result;
      else if (world) worldPage = result;
      else if (mrt) mrtPage = result;
      else if (commerce) commercePage = result;
      else if (page === "shelf-inspector") shelfInspectorPage = result;
      else productStudioPage = result;
      window.dispatchEvent(new CustomEvent(`${page}-mounted`));
    } catch (error) {
      if (controller.signal.aborted) return;
      console.error(`Experience ${page} failed to start`, error);
      controller.abort();
      pageController = null;
      root.replaceChildren(
        emptyState(
          "shell.experienceFailed",
          "shell.experienceRecovery",
        ),
      );
      const retry = localize(element("button", "outline-button"), "common.retryExperience");
      retry.addEventListener("click", () => void syncRoute());
      root.append(retry);
      offerUpdate(root);
    }
  } else {
    if (dialog.open && page !== "gallery") closeViewer(false);
    if (page === "gallery") syncModelUrl();
  }
  const libraryViewChanged = page === "gallery" && previousSearchMode !== isSearchMode();
  if (previous && (previous !== page || worldDriveChanged || libraryViewChanged)) {
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
  url.searchParams.delete("tunnel");
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
function refreshTitle(page, tunnel = mountedTunnel) {
  const demo = demosByRoute.get(`?page=${page}`);
  const key = page === "sg-world" && tunnel ? "world.tunnel.title"
    : demo ? demoTitleKey(demo) : page === "gallery" ? "nav.models" : `nav.${page}`;
  document.title = t("shell.pageTitle", { title: t(key) });
}

function refreshViewerMetadata(asset) {
  localize($("#viewer-category"), "viewer.category", () => ({
    category: categoryLabel(asset.category).toLocaleUpperCase(getLanguage()),
  }));
  metadata(asset);
}

function refreshLanguage() {
  for (const option of document.querySelectorAll("[data-previous-category]")) {
    option.textContent = t("library.previous", { category: categoryLabel(option.dataset.previousCategory) });
  }
  const page = route();
  if (mountedRoute === "gallery") renderModels();
  if (mountedRoute === "demos") renderDemos();
  if (activeAsset) refreshViewerMetadata(activeAsset);
  refreshTitle(page);
  refreshVersion();
  refreshUpdateActions();
  refreshScrollToTop();
}

onLanguageChange(refreshLanguage);
refreshLanguage();
void syncRoute();
document.documentElement.removeAttribute("data-i18n-pending");
