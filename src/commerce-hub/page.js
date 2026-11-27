import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { localize, mountMarkup, t } from "../i18n/index.js";
import { FRAME, HEADROOM, placements, VIEW_ELEVATION, VIEW_YAW } from "./layout.js";
import { animateParts, composeModules, createLinks, disposeTree, pickModule } from "./scene.js";
import "./style.css";

const icon = paths => `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
const MIN_ZOOM = 0.6, MAX_ZOOM = 5;
// Shortest gap between a label and the point it names, in CSS pixels.
const LEADER = 20;
// Labels sit centred above their module. The centre module has no drawn label: it is clicked directly,
// and its button appears only for keyboard focus.
const LABELS = Object.freeze({
  bags: { icon: icon('<path d="M5 8h14l1 12H4zM9 8V6a3 3 0 0 1 6 0v2"/>') },
  shop: { icon: icon('<path d="M4 9h16l-1-5H5zM5 9v11h14V9M9 20v-6h6v6"/>') },
  warehouse: { icon: icon('<path d="M12 3l9 5v8l-9 5-9-5V8zM3 8l9 5 9-5M12 13v8"/>') },
  delivery: { icon: icon('<path d="M3 6h11v11H3zM14 10h4l3 3v4h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17" cy="18" r="2"/>') },
  payment: { icon: icon('<path d="M3 6h18v12H3zM3 10h18M7 15h4"/>') },
  analytics: { icon: icon('<path d="M5 20v-6M12 20V9M19 20V4"/>') },
  automation: { icon: icon('<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9L7 7M17 17l2.1 2.1M19.1 4.9L17 7M7 17l-2.1 2.1"/><circle cx="12" cy="12" r="7"/>') },
});
export async function mountCommerceHub(root, assets, signal) {
  if (signal.aborted) throw new DOMException("Navigation cancelled", "AbortError");
  mountMarkup(root, `<section class="commerce-hub"><header class="ch-heading"><h1 data-i18n="commerce.title"></h1><p data-i18n="commerce.intro"></p></header><div class="ch-stage" aria-busy="true"><div class="ch-labels"></div><p class="ch-loading" role="status"></p><div class="ch-zoom"><button type="button" data-zoom="in" data-i18n-aria-label="commerce.zoomIn" disabled>+</button><button type="button" data-zoom="out" data-i18n-aria-label="commerce.zoomOut" disabled>−</button><button type="button" data-zoom="reset" data-i18n-aria-label="commerce.reset" disabled>⟲</button></div></div><div class="ch-panel" aria-live="polite"><div><h2></h2><p class="ch-text"></p></div><button type="button" class="ch-reset" data-i18n="commerce.reset" disabled></button></div><p class="ch-hint" data-i18n="commerce.hint"></p></section>`);
  const $ = selector => root.querySelector(selector);
  const stage = $(".ch-stage"), layer = $(".ch-labels"), loading = $(".ch-loading"), reset = $(".ch-reset");
  const zoomButtons = root.querySelectorAll("[data-zoom]");
  const local = new AbortController(), reduced = matchMedia("(prefers-reduced-motion: reduce)");
  const places = placements(), models = new Map(), buttons = new Map();
  let pointerStart = null, renderer, controls, resizeObserver, viewObserver, environment, composed, links, light;
  let disposed = false, onScreen = true, drawn = 0, frame = 0, selected = null, tween = null, halfHeight = 8, started = 0;

  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 200);
  const yaw = VIEW_YAW * Math.PI / 180, elevation = VIEW_ELEVATION * Math.PI / 180;
  const direction = new THREE.Vector3(Math.sin(yaw) * Math.cos(elevation), Math.sin(elevation), Math.cos(yaw) * Math.cos(elevation));
  const overview = new THREE.Vector3();
  const screenRight = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  const screenUp = new THREE.Vector3().crossVectors(direction, screenRight);
  const showInfo = () => {
    localize($(".ch-panel h2"), selected ? `commerce.${selected}.label` : "commerce.overview.title");
    localize($(".ch-text"), selected ? `commerce.${selected}.text` : "commerce.overview.text");
    for (const [id, button] of buttons) button.setAttribute("aria-pressed", String(id === selected));
    stage.dataset.selected = selected ?? "";
  };

  const narrow = matchMedia("(max-width: 700px)");
  const placeLabels = () => {
    const width = stage.clientWidth, height = stage.clientHeight;
    const toScreen = point => {
      const projected = point.clone().project(camera);
      return { x: (projected.x + 1) / 2 * width, y: (1 - projected.y) / 2 * height, inside: Math.abs(projected.x) <= 1 && Math.abs(projected.y) <= 1.1 };
    };
    for (const [id, button] of buttons) {
      const anchor = composed?.anchors.get(id);
      if (!anchor) continue;
      const pin = toScreen(anchor.pin), top = toScreen(anchor.top), half = button.offsetWidth / 2, tall = button.offsetHeight;
      // Labels of modules that were moved off screen are hidden instead of piling up at the edges.
      // The centre button is the only keyboard path to the bags, so it never leaves the tab order.
      button.hidden = id !== "bags" && !pin.inside;
      // Centred above the module, with the leader reaching down to its highest point.
      const x = Math.min(width - half - 2, Math.max(half + 2, pin.x));
      // On phones the icon sits on its own module, so it cannot cover a neighbour.
      const above = Math.min(pin.y - LEADER, top.y - 4) - tall;
      const y = Math.min(height - tall - 2, Math.max(2, narrow.matches ? pin.y - tall / 4 : above));
      button.style.transform = `translate(${Math.round(x - half)}px, ${Math.round(y)}px)`;
      button.style.setProperty("--leader", `${Math.max(8, Math.round(pin.y - y - tall + 4))}px`);
      button.style.setProperty("--leader-shift", `${Math.round(pin.x - x)}px`);
    }
  };

  const draw = now => {
    if (disposed || !composed) return;
    const time = reduced.matches ? 0 : (now - started) / 1000;
    animateParts(composed.parts, time);
    if (tween) {
      const k = Math.min(1, (now - tween.start) / 600), e = k * k * (3 - 2 * k);
      const target = tween.from.clone().lerp(tween.to, e);
      camera.position.add(target.clone().sub(controls.target));
      controls.target.copy(target);
      camera.zoom = tween.zoomFrom + (tween.zoomTo - tween.zoomFrom) * e;
      camera.updateProjectionMatrix();
      if (k === 1) tween = null;
    }
    controls.update();
    camera.updateMatrixWorld();
    // Moving parts cast shadows: refresh the single shadow pass a few times a second, not every frame.
    if (!reduced.matches && ++drawn % 6 === 0) renderer.shadowMap.needsUpdate = true;
    renderer.render(scene, camera);
    const calls = String(renderer.info.render.calls);
    if (stage.dataset.frameCalls !== calls) stage.dataset.frameCalls = calls;
    placeLabels();
  };
  const animating = () => !reduced.matches && onScreen && !document.hidden;
  const invalidate = () => {
    if (disposed || !composed || frame || animating()) return;
    frame = requestAnimationFrame(now => { frame = 0; draw(now); });
  };
  const syncLoop = () => {
    if (disposed || !composed) return;
    renderer.setAnimationLoop(animating() ? () => draw(performance.now()) : null);
    invalidate();
  };

  const focus = id => {
    if (!composed) return;
    selected = id;
    showInfo();
    const place = places.find(item => item.id === id);
    const to = place ? new THREE.Vector3(place.x, 1.2 * place.scale, place.z) : overview.clone();
    const zoom = place ? Math.min(MAX_ZOOM, Math.max(1.4, halfHeight / (place.radius * 1.5) * Math.min(1, camera.right / camera.top))) : 1;
    if (!place) {
      camera.position.copy(controls.target).addScaledVector(direction, 60);
    }
    tween = { start: performance.now() - (reduced.matches ? 600 : 0), from: controls.target.clone(), to, zoomFrom: camera.zoom, zoomTo: zoom };
    if (animating()) return;
    draw(performance.now());
  };

  const fit = () => {
    const width = stage.clientWidth, height = stage.clientHeight;
    if (!width || !height || !composed) return;
    renderer.setSize(width, height, false);
    // Overview shows exactly the anchor frame; other aspect ratios only add margin around it.
    const aspect = width / height;
    halfHeight = Math.max((FRAME.height + HEADROOM) / 2, FRAME.width / 2 / aspect) / FRAME.pixelsPerUnit;
    Object.assign(camera, { left: -halfHeight * aspect, right: halfHeight * aspect, top: halfHeight, bottom: -halfHeight });
    // Centre the view on the frame plus its headroom.
    const yawRight = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
    overview.crossVectors(direction, yawRight).multiplyScalar(HEADROOM / 2 / FRAME.pixelsPerUnit);
    controls.target.copy(overview);
    camera.position.copy(overview).addScaledVector(direction, 60);
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    tween = null;
    if (selected) focus(selected);
    else draw(performance.now());
  };

  const zoomBy = factor => {
    if (!composed) return;
    tween = null;
    camera.zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, camera.zoom * factor));
    camera.updateProjectionMatrix();
    controls.update();
    invalidate();
  };
  // A click or tap on a module itself selects it; a drag only looks around.
  const pick = event => {
    const bounds = renderer.domElement.getBoundingClientRect(), ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2((event.clientX - bounds.left) / bounds.width * 2 - 1,
      1 - (event.clientY - bounds.top) / bounds.height * 2), camera);
    return pickModule(composed, places, ray);
  };

  function dispose() {
    if (disposed) return;
    disposed = true;
    local.abort();
    signal.removeEventListener("abort", dispose);
    cancelAnimationFrame(frame);
    renderer?.setAnimationLoop(null);
    resizeObserver?.disconnect();
    viewObserver?.disconnect();
    controls?.dispose();
    disposeTree(scene);
    for (const model of models.values()) disposeTree(model);
    environment?.dispose();
    light?.shadow.dispose();
    renderer?.dispose();
    renderer?.forceContextLoss();
    renderer?.domElement.remove();
  }

  // The message has its own element: translating a container would delete the button beside it.
  const notice = (state, key, action, signal) => {
    stage.dataset.state = state;
    stage.setAttribute("aria-busy", "false");
    loading.hidden = false;
    const button = localize(document.createElement("button"), "common.retry");
    button.type = "button";
    button.addEventListener("click", action, signal ? { signal } : undefined);
    loading.replaceChildren(localize(document.createElement("span"), key), " ", button);
    return button;
  };

  async function load() {
    stage.dataset.state = "loading";
    stage.setAttribute("aria-busy", "true");
    let done = models.size;
    const message = document.createElement("span");
    loading.replaceChildren(message);
    const progress = () => localize(message, "commerce.loading", { done, total: places.length });
    progress();
    const loader = new GLTFLoader();
    try {
      // Settle every request before reporting, so late progress cannot overwrite the retry button.
      const results = await Promise.allSettled(places.filter(({ id }) => !models.has(id)).map(async ({ id }) => {
        const asset = assets.find(item => item.id === `commerce-${id}`);
        const response = await fetch(asset.file, { signal: local.signal });
        if (!response.ok) throw new Error(`Commerce module ${id}: ${response.status}`);
        const gltf = await loader.parseAsync(await response.arrayBuffer(), "");
        if (disposed) return disposeTree(gltf.scene);
        models.set(id, gltf.scene);
        done += 1;
        progress();
      }));
      if (disposed) return;
      const failed = results.find(result => result.status === "rejected");
      if (failed) throw failed.reason;
      composed = composeModules(places, models);
      models.clear();
      links = createLinks();
      scene.add(composed.root, links.group);
      renderer.shadowMap.needsUpdate = true;
      started = performance.now();
      loading.hidden = true;
      reset.disabled = false;
      for (const button of buttons.values()) button.disabled = false;
      for (const button of zoomButtons) button.disabled = false;
      layer.hidden = false;
      stage.dataset.state = "ready";
      stage.setAttribute("aria-busy", "false");
      fit();
      stage.dataset.calls = String(renderer.info.render.calls);
      stage.dataset.triangles = String(renderer.info.render.triangles);
      syncLoop();
    } catch (error) {
      if (disposed) return;
      console.error(error);
      // Composition moves nodes out of the parsed models, so a retry starts from fresh files.
      for (const model of models.values()) disposeTree(model);
      models.clear();
      notice("error", "commerce.failed", () => void load(), local.signal);
    }
  }

  try {
    mountMarkup(layer, Object.entries(LABELS).map(([id, { icon: svg }]) =>
      `<button type="button" class="ch-label" data-module="${id}" aria-pressed="false" disabled>${svg}<span></span></button>`).join(""));
    for (const button of layer.querySelectorAll("button")) {
      buttons.set(button.dataset.module, button);
      localize(button.querySelector("span"), `commerce.${button.dataset.module}.label`);
    }
    layer.hidden = true;
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setClearColor(0xf7f3ee);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.NoToneMapping;
    // Almost everything is static, so the shadow pass runs on demand instead of every frame.
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.shadowMap.autoUpdate = false;
    const canvas = renderer.domElement;
    canvas.tabIndex = 0;
    canvas.setAttribute("role", "img");
    localize(canvas, "commerce.stage", undefined, "aria-label");
    stage.prepend(canvas);
    canvas.addEventListener("touchstart", event => event.preventDefault(), { passive: false, signal: local.signal });

    const pmrem = new THREE.PMREMGenerator(renderer), room = new RoomEnvironment();
    environment = pmrem.fromScene(room, 0.04);
    scene.environment = environment.texture;
    scene.environmentIntensity = 0.35;
    room.dispose();
    pmrem.dispose();
    scene.add(new THREE.HemisphereLight(0xfff6ea, 0xc9b8a0, 0.75));
    light = new THREE.DirectionalLight(0xfff2e0, 2.0);
    light.position.set(-1, 14, 10.5);
    light.castShadow = true;
    light.shadow.mapSize.setScalar(2048);
    Object.assign(light.shadow.camera, { left: -13, right: 13, top: 13, bottom: -13, near: 1, far: 45 });
    Object.assign(light.shadow, { radius: 8, intensity: 0.42, bias: -0.0004, normalBias: 0.02 });
    scene.add(light);

    controls = new OrbitControls(camera, canvas);
    Object.assign(controls, {
      enablePan: true, screenSpacePanning: true, zoomToCursor: true, enableDamping: false, minZoom: MIN_ZOOM, maxZoom: MAX_ZOOM,
      minAzimuthAngle: yaw - 0.45, maxAzimuthAngle: yaw + 0.45,
      minPolarAngle: Math.PI / 2 - elevation - 0.22, maxPolarAngle: Math.PI / 2 - elevation + 0.17,
    });
    camera.position.copy(direction).multiplyScalar(60);
    controls.addEventListener("change", invalidate);
    controls.addEventListener("start", () => { tween = null; });

    layer.addEventListener("click", event => {
      const button = event.target.closest("button[data-module]");
      if (button) focus(button.dataset.module);
    }, { signal: local.signal });
    reset.addEventListener("click", () => focus(null), { signal: local.signal });
    $(".ch-zoom").addEventListener("click", event => {
      const action = event.target.closest("button[data-zoom]")?.dataset.zoom;
      if (action === "reset") focus(null);
      else if (action) zoomBy(action === "in" ? 1.3 : 1 / 1.3);
    }, { signal: local.signal });
    canvas.addEventListener("pointerdown", event => {
      pointerStart = event.isPrimary ? [event.clientX, event.clientY] : null;
    }, { signal: local.signal });
    // Dragging away and back is still a drag.
    canvas.addEventListener("pointermove", event => {
      if (pointerStart && Math.hypot(event.clientX - pointerStart[0], event.clientY - pointerStart[1]) > 6) pointerStart = null;
    }, { signal: local.signal });
    canvas.addEventListener("pointercancel", () => { pointerStart = null; }, { signal: local.signal });
    canvas.addEventListener("pointerup", event => {
      const start = pointerStart;
      pointerStart = null;
      if (!composed || !start || event.button !== 0 || Math.hypot(event.clientX - start[0], event.clientY - start[1]) > 6) return;
      const id = pick(event);
      if (id) focus(id);
    }, { signal: local.signal });
    root.addEventListener("keydown", event => {
      if (event.key === "Escape" && selected) focus(null);
    }, { signal: local.signal });
    canvas.addEventListener("keydown", event => {
      const turn = { ArrowLeft: -0.1, ArrowRight: 0.1 }[event.key];
      const zoom = { "+": 1.15, "=": 1.15, "-": 1 / 1.15 }[event.key];
      if (!turn && !zoom && event.key !== "Home") return;
      event.preventDefault();
      if (event.key === "Home") return focus(null);
      if (zoom) return zoomBy(zoom);
      else {
        const offset = camera.position.clone().sub(controls.target);
        const spherical = new THREE.Spherical().setFromVector3(offset);
        spherical.theta = Math.min(yaw + 0.45, Math.max(yaw - 0.45, spherical.theta + turn));
        camera.position.copy(controls.target).add(offset.setFromSpherical(spherical));
      }
      controls.update();
      invalidate();
    }, { signal: local.signal });
    canvas.addEventListener("webglcontextlost", event => {
      event.preventDefault();
      dispose();
      layer.hidden = true;
      reset.disabled = true;
      for (const button of zoomButtons) button.disabled = true;
      // dispose() aborted the page listeners, so this recovery button gets none of its signals.
      notice("interrupted", "commerce.interrupted", () => location.reload()).focus();
    }, { signal: local.signal });
    document.addEventListener("visibilitychange", syncLoop, { signal: local.signal });
    reduced.addEventListener("change", syncLoop, { signal: local.signal });
    viewObserver = new IntersectionObserver(([entry]) => { onScreen = entry.isIntersecting; syncLoop(); });
    viewObserver.observe(stage);
    resizeObserver = new ResizeObserver(fit);
    resizeObserver.observe(stage);
    signal.addEventListener("abort", dispose, { once: true });
    showInfo();
    void load();
    return { dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
