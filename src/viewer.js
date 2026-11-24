import { localize, t } from "./i18n/index.js";
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import { interactionKind } from "./model-interaction.js";
import { acquireModelViewerRenderer } from "./model-viewer-renderer.js";
import { fitViewerBounds, fitViewerObject, syncViewerSize } from "./viewer-framing.js";

export default async function createViewer(
  container,
  url,
  status,
  signal,
  asset,
) {
  const isVehicle = asset.id === "proton-saga-1985";
  // Optional metadata is validated during catalog loading/build. Omitting each
  // override retains the original viewer defaults, including special families.
  const display = asset.details?.display;
  const lighting = display?.previewLighting;
  let vehicleToolbar;
  let fishMotion;
  let cartDemo;
  let pickupDemo;
  let lohHeiDemo;
  let railReloadDemo;
  let carparkHelpDemo;
  let airBalangDemo;
  let coconutScraperDemo;
  let parcelHatchDemo;
  let beverageReturnDemo;
  let awningDemo;
  let dacingDemo;
  let visitorDemo;
  let animationPreview;
  let buildingLoop;
  let chibiRig;
  let lastDraw = 0;
  let studio;
  let model;
  let frameForResize;
  const rendererLease = acquireModelViewerRenderer();
  const { renderer } = rendererLease;
  renderer.toneMapping = THREE.NoToneMapping;
  renderer.toneMappingExposure = 1;
  renderer.shadowMap.enabled = false;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x657078);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  if (asset.id === "marina-bay-sands-loop") {
    renderer.setClearColor(0xd5d0c9);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.90;
  }
  if (isVehicle) {
    renderer.setClearColor(0x202326);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  }
  if (asset.family === "solar-system") {
    renderer.setClearColor(0x313840);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1;
  }
  localize(renderer.domElement, "viewer.canvas", { name: asset.name }, "aria-label");
  renderer.domElement.setAttribute("role", "group");
  renderer.domElement.tabIndex = 0;
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.00001, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  const clearPreset = () => {
    vehicleToolbar?.querySelectorAll("[data-vehicle-view]").forEach(button => button.setAttribute("aria-pressed", "false"));
  };
  controls.addEventListener("start", clearPreset);
  const onKeyDown = (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const orbit = new THREE.Spherical().setFromVector3(camera.position.clone().sub(controls.target));
    const step = Math.PI / 18;
    if (event.key === "ArrowLeft") orbit.theta -= step;
    else if (event.key === "ArrowRight") orbit.theta += step;
    else if (event.key === "ArrowUp") orbit.phi -= step;
    else if (event.key === "ArrowDown") orbit.phi += step;
    else if (["+", "=", "PageUp"].includes(event.key)) orbit.radius /= 1.15;
    else if (["-", "_", "PageDown"].includes(event.key)) orbit.radius *= 1.15;
    else return;
    event.preventDefault();
    clearPreset();
    orbit.makeSafe();
    orbit.radius = THREE.MathUtils.clamp(orbit.radius, controls.minDistance, controls.maxDistance);
    camera.position.copy(controls.target).add(new THREE.Vector3().setFromSpherical(orbit));
    controls.update();
    invalidate();
  };
  renderer.domElement.addEventListener("keydown", onKeyDown);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x535b53, lighting?.hemisphereIntensity ?? 2));
  const light = new THREE.DirectionalLight(0xffffff, lighting?.directionalIntensity ?? 2.1);
  light.position.fromArray(lighting?.directionalPosition ?? [4, 7, 5]);
  scene.add(light);
  let frame = 0;
  let disposed = false;
  let draw = () => {};
  const invalidate = () => {
    if (!disposed && !document.hidden && !frame)
      frame = requestAnimationFrame(() => {
        frame = 0;
        draw();
      });
  };
  controls.addEventListener("change", invalidate);
  const visibility = () => {
    if (document.hidden) {
      fishMotion?.suspend();
      cancelAnimationFrame(frame);
      frame = 0;
    } else invalidate();
  };
  document.addEventListener("visibilitychange", visibility);
  const resize = () => {
    const { sizeChanged, aspectChanged, pixelRatioChanged } = syncViewerSize(
      container,
      renderer,
      camera,
      Math.min(window.devicePixelRatio, 2),
    );
    if (sizeChanged || aspectChanged) {
      if (model && frameForResize) frameForResize();
      else invalidate();
    } else if (pixelRatioChanged) {
      invalidate();
    }
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  window.addEventListener("resize", resize);
  const disposeModel = (object) => {
    object?.traverse((child) => {
      child.geometry?.dispose();
      for (const material of Array.isArray(child.material)
        ? child.material
        : [child.material]) {
        if (!material) continue;
        for (const value of Object.values(material))
          if (value?.isTexture) value.dispose();
        material.dispose();
      }
    });
  };
  const onContextLost = (event) => {
    event.preventDefault();
    if (!disposed)
      localize(status, "viewer.interrupted");
  };
  renderer.domElement.addEventListener("webglcontextlost", onContextLost);
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    window.removeEventListener("resize", resize);
    controls.removeEventListener("change", invalidate);
    document.removeEventListener("visibilitychange", visibility);
    controls.dispose();
    renderer.domElement.removeEventListener("keydown", onKeyDown);
    renderer.domElement.removeEventListener("webglcontextlost", onContextLost);
    fishMotion?.dispose();
    cartDemo?.dispose();
    pickupDemo?.dispose();
    lohHeiDemo?.dispose();
    railReloadDemo?.dispose();
    carparkHelpDemo?.dispose();
    airBalangDemo?.dispose();
    coconutScraperDemo?.dispose();
    parcelHatchDemo?.dispose();
    beverageReturnDemo?.dispose();
    awningDemo?.dispose();
    dacingDemo?.dispose();
    visitorDemo?.dispose();
    animationPreview?.dispose();
    buildingLoop?.dispose();
    chibiRig?.dispose();
    disposeModel(model);
    disposeModel(studio);
    scene.environment = null;
    light.shadow.dispose();
    vehicleToolbar?.remove();
    rendererLease.release();
    signal.removeEventListener("abort", dispose);
  };
  signal.addEventListener("abort", dispose, { once: true });
  try {
    // Read the native response before parsing. The pinned FileLoader's stream
    // reader path reports ERR_ABORTED after a complete transfer in Chromium;
    // see docs/gallery-loading.md. Keep the viewer signal on the real request.
    const response = await fetch(url, { signal });
    // Consume error bodies too: retry must not abort a leftover HTTP response.
    const buffer = await response.arrayBuffer();
    if (!response.ok) throw new Error(`Model request failed: ${response.status}`);
    if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    const base = THREE.LoaderUtils.extractUrlBase(new URL(url, document.baseURI).href);
    const gltf = await new GLTFLoader().parseAsync(buffer, base);
    if (disposed || signal.aborted) {
      disposeModel(gltf.scene);
      throw new DOMException("Viewer closed", "AbortError");
    }
    model = gltf.scene;
    const doorCodes = ["FL", "FR", "RL", "RR"];
    const candidates = isVehicle ? doorCodes.map(code => model.getObjectByName(`Door_${code}_Hinge`)) : [];
    // Door controls only operate when the real model has all four independent pivots.
    const doorRig = candidates.length === 4 && candidates.every(node => node && node.children.length)
      ? Object.fromEntries(doorCodes.map((code, index) => [code, { node: candidates[index], closed: candidates[index].rotation.y }]))
      : null;
    const doorButtons = new Map();
    if (isVehicle || display?.studioEnvironment === true) {
      // Local studio reflections give metallic paint, steel rims and tin lids their form.
      scene.environment = rendererLease.getStudioEnvironment();
      scene.environmentIntensity = display?.environmentIntensity ?? 0.6;
    }
    if (display)
      model.rotation.y = display.previewRotationY ?? 0;
    if (display?.textureAnisotropy > 1) {
      // Anisotropic filtering keeps small printed text readable at oblique angles on curved surfaces (opt-in per asset).
      const level = Math.min(display.textureAnisotropy, renderer.capabilities.getMaxAnisotropy());
      model.traverse((node) => {
        if (!node.isMesh) return;
        for (const material of [].concat(node.material))
          for (const texture of [material.map, material.normalMap, material.roughnessMap, material.metalnessMap])
            if (texture) texture.anisotropy = Math.max(texture.anisotropy, level);
      });
    }
    scene.add(model);
    const interaction = interactionKind(asset);
    if (interaction === "fish") {
      const { default: createFishMotion } = await import("./fish-motion.js");
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
      fishMotion = createFishMotion({ model, clips: gltf.animations, container, invalidate });
    } else if (interaction === "cart") {
      const { default: createCartDemo } = await import('./shopping-cart/demo.js');
      cartDemo = await createCartDemo({ model, scene, container, signal, invalidate });
      if (disposed || signal.aborted) {
        cartDemo.dispose();
        throw new DOMException('Viewer closed', 'AbortError');
      }
    } else if (interaction === "pickup-bay") {
      // A missing optional control must not make the ordinary viewer fail.
      try {
        const { default: createPickupDemo } = await import("./pickup-bay/demo.js");
        if (!disposed && !signal.aborted) pickupDemo = createPickupDemo({ model, container, signal, invalidate });
      } catch {
        // The model remains available for viewing even if the demo module fails.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    } else if (interaction === "visitor-v2") {
      const { default: createVisitorDemo } = await import('./visitor-v2/demo.js');
      if (disposed || signal.aborted) throw new DOMException('Viewer closed', 'AbortError');
      visitorDemo = createVisitorDemo({ model, clips: gltf.animations, container, invalidate });
    } else if (interaction === "visitor-v3") {
      const { default: createVisitorDemo } = await import('./visitor-v3/demo.js');
      if (disposed || signal.aborted) throw new DOMException('Viewer closed', 'AbortError');
      visitorDemo = createVisitorDemo({ model, clips: gltf.animations, container, invalidate });
    }
    if (asset.id === "tripo-chibi-rig") {
      const { createChibiRigControls } = await import("./chibi-rig-controls.js");
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
      chibiRig = createChibiRigControls({ model, scene, container, invalidate });
    }
    const bounds = new THREE.Box3().setFromObject(cartDemo?.group ?? model);
    if (bounds.isEmpty()) throw new Error("Model has no visible bounds");
    const radius = Math.max(bounds.getSize(new THREE.Vector3()).length() / 2, 0.001);
    const direction = (
      display?.previewCameraDirection ? new THREE.Vector3().fromArray(display.previewCameraDirection) :
      isVehicle ? new THREE.Vector3(1, 0.35, -0.75) :
      asset.family === "solar-system"
        ? new THREE.Vector3(0.55, 0.42, 1)
        : asset.category === "Balls"
          ? new THREE.Vector3(1, 0.3, 0.25)
          : new THREE.Vector3(1, 0.9, 1)
    ).normalize();
    const frameObject = (visibleObject, viewDirection, animationBounds) => {
      syncViewerSize(container, renderer, camera, Math.min(window.devicePixelRatio, 2));
      const frame = animationBounds
        ? fitViewerBounds(animationBounds, camera, viewDirection)
        : fitViewerObject(visibleObject, camera, viewDirection);
      camera.near = Math.max(frame.radius * 0.001, Number.EPSILON);
      camera.far = Math.max(frame.radius * 50, frame.distance * 12 + frame.radius);
      camera.updateProjectionMatrix();
      controls.minDistance = frame.minDistance;
      controls.maxDistance = frame.maxDistance;
      const damping = controls.enableDamping;
      controls.enableDamping = false;
      try {
        // Clear any orbit inertia before applying this exact reset or preset.
        controls.update();
        controls.target.copy(frame.target);
        camera.position.copy(frame.target).addScaledVector(frame.direction, frame.distance);
        controls.update();
      } finally {
        controls.enableDamping = damping;
      }
      invalidate();
    };
    const animationPreviews = asset.id === "tripo-convert-1c818c0d"
      ? [["run", "clip.run"], ["sit", "clip.sit"]]
      : asset.id === "tripo-convert-405dc0a0"
        ? [["walk", "clip.walk"]]
        : undefined;
    if (animationPreviews) {
      const { default: createAnimationPreview } = await import("./tripo-animation-preview.js");
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
      animationPreview = createAnimationPreview({
        model,
        clips: gltf.animations,
        previews: animationPreviews,
        container,
        onPlay(bounds) {
          lastDraw = 0;
          const viewDirection = camera.position.clone().sub(controls.target).normalize();
          frameObject(model, viewDirection, bounds);
        },
      });
    }
    if (interaction === "loh-hei") {
      try {
        const { default: createLohHeiDemo } = await import("./loh-hei/demo.js");
        if (!disposed && !signal.aborted) {
          lohHeiDemo = createLohHeiDemo({
            model, clips: gltf.animations, container, invalidate,
            onPlay(bounds) {
              lastDraw = 0;
              const viewDirection = camera.position.clone().sub(controls.target).normalize();
              frameObject(model, viewDirection, bounds);
            },
          });
        }
      } catch {
        // Optional animation must not take down the ordinary model viewer.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "rail-reload") {
      try {
        const { default: createRailReloadDemo } = await import("./rail-reload/demo.js");
        if (!disposed && !signal.aborted) {
          railReloadDemo = createRailReloadDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The booth remains available as an ordinary model if the add-on fails.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "carpark-help") {
      try {
        const { default: createCarparkHelpDemo } = await import("./carpark-help/demo.js");
        if (!disposed && !signal.aborted) {
          carparkHelpDemo = createCarparkHelpDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The help point remains available as an ordinary model if the add-on fails.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "air-balang") {
      try {
        const { default: createAirBalangDemo } = await import("./air-balang/demo.js");
        if (!disposed && !signal.aborted) {
          airBalangDemo = createAirBalangDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The stall remains available as an ordinary model if the add-on fails.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "coconut-scraper") {
      try {
        const { default: createCoconutScraperDemo } = await import("./coconut-scraper/demo.js");
        if (!disposed && !signal.aborted) {
          coconutScraperDemo = createCoconutScraperDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The scraper remains available as an ordinary model if the add-on fails.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "parcel-hatch") {
      try {
        const { default: createParcelHatchDemo } = await import("./parcel-hatch/demo.js");
        if (!disposed && !signal.aborted) {
          parcelHatchDemo = createParcelHatchDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The hatch remains inspectable even if the optional demo cannot load.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "beverage-return") {
      try {
        const { default: createBeverageReturnDemo } = await import("./beverage-return/demo.js");
        if (!disposed && !signal.aborted) {
          beverageReturnDemo = createBeverageReturnDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The kiosk remains inspectable even if the optional demo cannot load.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "awning") {
      try {
        const { default: createAwningDemo } = await import("./awning/demo.js");
        if (!disposed && !signal.aborted) {
          awningDemo = createAwningDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The awning remains inspectable even if the optional demo cannot load.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    if (interaction === "dacing") {
      try {
        const { default: createDacingDemo } = await import("./dacing/demo.js");
        if (!disposed && !signal.aborted) {
          dacingDemo = createDacingDemo({
            model, clips: gltf.animations, container,
            invalidate() {
              lastDraw = 0;
              invalidate();
            },
          });
        }
      } catch {
        // The scale remains inspectable even if the optional demo cannot load.
      }
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
    }
    frameForResize = () => {
      if (!model) return;
      const viewDirection = camera.position.clone().sub(controls.target);
      if (viewDirection.lengthSq() === 0) viewDirection.copy(direction);
      else viewDirection.normalize();
      frameObject(cartDemo?.group ?? model, viewDirection, animationPreview?.bounds ?? lohHeiDemo?.bounds ?? (buildingLoop && bounds));
    };
    const frameVehicle = (viewDirection, target = model) => {
      // Include open doors in the bounds so a preset never cuts them off.
      frameObject(target, viewDirection);
    };
    const reset = () => {
      clearPreset();
      cartDemo?.reset();
      pickupDemo?.reset();
      lohHeiDemo?.reset();
      railReloadDemo?.reset();
      carparkHelpDemo?.reset();
      airBalangDemo?.reset();
      coconutScraperDemo?.reset();
      parcelHatchDemo?.reset();
      beverageReturnDemo?.reset();
      awningDemo?.reset();
      dacingDemo?.reset();
      visitorDemo?.reset();
      animationPreview?.reset();
      chibiRig?.reset();
      if (doorRig) for (const [code, door] of Object.entries(doorRig)) {
        door.node.rotation.y = door.closed;
        doorButtons.get(code)?.setAttribute("aria-pressed", "false");
      }
      if (isVehicle || cartDemo) { frameVehicle(direction, cartDemo?.group ?? model); return; }
      frameObject(model, direction, buildingLoop && bounds);
    };
    const setView = (name) => {
      const directions = { front: [-1, 0, 0], rear: [1, 0, 0], left: [0, 0, 1], right: [0, 0, -1] };
      if (!isVehicle || !directions[name]) return;
      const axis = new THREE.Vector3(...directions[name]).applyEuler(model.rotation).normalize();
      frameVehicle(axis);
      vehicleToolbar?.querySelectorAll("[data-vehicle-view]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.vehicleView === name)));
    };
    if (isVehicle) {
      scene.fog = new THREE.Fog(0x202326, radius * 6, radius * 14);
      studio = new THREE.Group();
      scene.add(studio);
      const floor = new THREE.Mesh(new THREE.PlaneGeometry(200, 200), new THREE.MeshStandardMaterial({ color: 0x25282b, roughness: 0.85 }));
      floor.rotation.x = -Math.PI / 2;
      floor.position.y = bounds.min.y - 0.005;
      floor.receiveShadow = true;
      studio.add(floor);
      model.traverse(object => { if (object.isMesh) { object.castShadow = true; object.receiveShadow = false; } });
      light.castShadow = true;
      light.shadow.mapSize.set(1024, 1024);
      light.shadow.camera.left = light.shadow.camera.bottom = -5;
      light.shadow.camera.right = light.shadow.camera.top = 5;
      light.shadow.camera.near = 0.1;
      light.shadow.camera.far = 30;
      light.shadow.normalBias = 0.003;
      light.shadow.bias = -0.00002;
      const fill = new THREE.DirectionalLight(0xdde8ff, 2);
      fill.position.set(-4, 3, -3);
      studio.add(fill);
      controls.maxPolarAngle = Math.PI / 2;
      vehicleToolbar = document.createElement("div");
      vehicleToolbar.className = "vehicle-views";
      vehicleToolbar.setAttribute("role", "group");
      localize(vehicleToolbar, "vehicle.controls", undefined, "aria-label");
      const title = document.createElement("span");
      title.className = "vehicle-views-label";
      localize(title, "vehicle.showcase");
      vehicleToolbar.append(title);
      const buttons = document.createElement("div");
      buttons.className = "vehicle-view-buttons";
      for (const name of ["front", "rear", "left", "right"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.vehicleView = name;
        localize(button, `direction.${name}`);
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => setView(name));
        buttons.append(button);
      }
      vehicleToolbar.append(buttons);
      const doorControls = document.createElement("div");
      doorControls.className = "vehicle-door-controls";
      if (doorRig) {
        const label = document.createElement("span");
        label.className = "vehicle-views-label";
        localize(label, "vehicle.doors");
        const group = document.createElement("div");
        group.className = "vehicle-door-buttons";
        group.setAttribute("role", "group");
        localize(group, "vehicle.doors", undefined, "aria-label");
        for (const code of doorCodes) {
          const button = document.createElement("button");
          button.type = "button";
          button.dataset.vehicleDoor = code;
          localize(button, `vehicle.door.${code}`);
          localize(button, "vehicle.doorLabel", () => ({ position: t(`vehicle.door.${code}`) }), "aria-label");
          button.setAttribute("aria-pressed", "false");
          button.addEventListener("click", () => {
            const opening = button.getAttribute("aria-pressed") !== "true";
            const door = doorRig[code];
            door.node.rotation.y = door.closed + (opening ? (code.endsWith("L") ? -1 : 1) * Math.PI / 3 : 0);
            button.setAttribute("aria-pressed", String(opening));
            const currentDirection = camera.position.clone().sub(controls.target).normalize();
            frameVehicle(currentDirection);
          });
          doorButtons.set(code, button);
          group.append(button);
        }
        doorControls.append(label, group);
      } else {
        doorControls.classList.add("vehicle-door-unavailable");
        localize(doorControls, "vehicle.noDoors");
      }
      vehicleToolbar.append(doorControls);
      container.insertAdjacentElement("afterend", vehicleToolbar);
    }
    if (asset.id === "marina-bay-sands-loop") {
      const { default: createBuildingLoop } = await import("./building-loop.js");
      if (disposed || signal.aborted) throw new DOMException("Viewer closed", "AbortError");
      buildingLoop = createBuildingLoop({ model, clip: gltf.animations[0], container, invalidate });
    }
    reset();
    localize(status);
    draw = () => {
      frame = 0;
      if (disposed || document.hidden) return;
      const now = performance.now();
      const active = cartDemo?.update(lastDraw ? (now - lastDraw) / 1000 : 0);
      const elapsed = lastDraw ? (now - lastDraw) / 1000 : 0;
      const pickupActive = pickupDemo?.update(elapsed);
      const lohHeiActive = lohHeiDemo?.update(elapsed);
      const railReloadActive = railReloadDemo?.update(elapsed);
      const carparkHelpActive = carparkHelpDemo?.update(elapsed);
      const airBalangActive = airBalangDemo?.update(elapsed);
      const coconutScraperActive = coconutScraperDemo?.update(elapsed);
      const parcelHatchActive = parcelHatchDemo?.update(elapsed);
      const beverageReturnActive = beverageReturnDemo?.update(elapsed);
      const awningActive = awningDemo?.update(elapsed);
      const dacingActive = dacingDemo?.update(elapsed);
      const visitorActive = visitorDemo?.update(elapsed);
      const animationActive = animationPreview?.update(elapsed);
      const buildingActive = buildingLoop?.update(elapsed);
      lastDraw = now;
      const fishActive = fishMotion?.update();
      const changed = controls.update();
      renderer.render(scene, camera);
      if (changed || active || pickupActive || lohHeiActive || railReloadActive || carparkHelpActive || airBalangActive || coconutScraperActive || parcelHatchActive || beverageReturnActive || awningActive || dacingActive || visitorActive || animationActive || buildingActive || fishActive) invalidate();
    };
    invalidate();
    return { reset, dispose, setView };
  } catch (error) {
    dispose();
    throw error;
  }
}
