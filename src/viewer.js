import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

export default async function createViewer(
  container,
  url,
  status,
  signal,
  asset,
) {
  const isVehicle = asset.id === "proton-saga-1985";
  let vehicleToolbar;
  let studio;
  let environmentTarget;
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x657078);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
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
  renderer.domElement.setAttribute(
    "aria-label",
    `Interactive 3D ${asset.name}. Drag or use arrow keys to rotate. Use plus and minus keys to zoom.`,
  );
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
  renderer.domElement.addEventListener("keydown", (event) => {
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
  });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x535b53, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2.1);
  light.position.set(4, 7, 5);
  scene.add(light);
  let frame = 0;
  let model;
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
      cancelAnimationFrame(frame);
      frame = 0;
    } else invalidate();
  };
  document.addEventListener("visibilitychange", visibility);
  const resize = () => {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    invalidate();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
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
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.removeEventListener("change", invalidate);
    document.removeEventListener("visibilitychange", visibility);
    controls.dispose();
    disposeModel(model);
    disposeModel(studio);
    scene.environment = null;
    environmentTarget?.dispose();
    light.shadow.dispose();
    vehicleToolbar?.remove();
    renderer.dispose();
    renderer.domElement.remove();
    signal.removeEventListener("abort", dispose);
  };
  signal.addEventListener("abort", dispose, { once: true });
  renderer.domElement.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    if (!disposed)
      status.textContent =
        "The 3D view was interrupted. Close and reopen it to retry.";
  });
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
    if (isVehicle) {
      // Local studio reflections give metallic paint and steel rims their form.
      const room = new RoomEnvironment();
      const pmrem = new THREE.PMREMGenerator(renderer);
      try {
        environmentTarget = pmrem.fromScene(room, 0.04);
        scene.environment = environmentTarget.texture;
        scene.environmentIntensity = 0.6;
      } finally {
        room.dispose();
        pmrem.dispose();
      }
    }
    if (asset.details?.display)
      model.rotation.y = asset.details.display.previewRotationY ?? 0;
    scene.add(model);
    const bounds = new THREE.Box3().setFromObject(model);
    if (bounds.isEmpty()) throw new Error("Model has no visible bounds");
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 0.001);
    camera.near = radius / 50;
    camera.far = radius * 50;
    controls.minDistance = radius * 1.05;
    controls.maxDistance = radius * 20;
    const direction = (
      isVehicle ? new THREE.Vector3(1, 0.35, -0.75) :
      asset.family === "solar-system"
        ? new THREE.Vector3(0.55, 0.42, 1)
        : asset.category === "Balls"
          ? new THREE.Vector3(1, 0.3, 0.25)
          : new THREE.Vector3(1, 0.9, 1)
    ).normalize();
    const frameVehicle = (viewDirection) => {
      resize();
      // Include open doors in the bounds so a preset never cuts them off.
      const visibleBounds = new THREE.Box3().setFromObject(model);
      const visibleCenter = visibleBounds.getCenter(new THREE.Vector3());
      const vertical = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
      const horizontal = vertical * camera.aspect;
      const right = new THREE.Vector3().crossVectors(camera.up, viewDirection).normalize();
      const up = new THREE.Vector3().crossVectors(viewDirection, right).normalize();
      let distance = 0;
      for (const x of [visibleBounds.min.x, visibleBounds.max.x]) for (const y of [visibleBounds.min.y, visibleBounds.max.y]) for (const z of [visibleBounds.min.z, visibleBounds.max.z]) {
        const offset = new THREE.Vector3(x, y, z).sub(visibleCenter);
        const depth = offset.dot(viewDirection);
        distance = Math.max(distance, depth + Math.abs(offset.dot(right)) / horizontal, depth + Math.abs(offset.dot(up)) / vertical);
      }
      controls.target.copy(visibleCenter);
      camera.position.copy(visibleCenter).addScaledVector(viewDirection, Math.max(distance * 1.08, controls.minDistance));
      controls.update();
      invalidate();
    };
    const reset = () => {
      clearPreset();
      if (doorRig) for (const [code, door] of Object.entries(doorRig)) {
        door.node.rotation.y = door.closed;
        doorButtons.get(code)?.setAttribute("aria-pressed", "false");
      }
      if (isVehicle) { frameVehicle(direction); return; }
      resize();
      const vertical = THREE.MathUtils.degToRad(camera.fov / 2);
      const horizontal = Math.atan(Math.tan(vertical) * camera.aspect);
      const distance =
        (radius / Math.sin(Math.min(vertical, horizontal))) * 1.08;
      camera.position.copy(center).addScaledVector(direction, distance);
      controls.target.copy(center);
      controls.update();
      invalidate();
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
      vehicleToolbar.setAttribute("aria-label", "Vehicle showcase controls");
      const title = document.createElement("span");
      title.className = "vehicle-views-label";
      title.textContent = "360° Vehicle Showcase";
      vehicleToolbar.append(title);
      const buttons = document.createElement("div");
      buttons.className = "vehicle-view-buttons";
      for (const name of ["front", "rear", "left", "right"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.vehicleView = name;
        button.textContent = name[0].toUpperCase() + name.slice(1);
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
        label.textContent = "Open or close doors";
        const group = document.createElement("div");
        group.className = "vehicle-door-buttons";
        group.setAttribute("role", "group");
        group.setAttribute("aria-label", "Open or close doors");
        for (const [code, labelText] of [["FL", "Front left"], ["FR", "Front right"], ["RL", "Rear left"], ["RR", "Rear right"]]) {
          const button = document.createElement("button");
          button.type = "button";
          button.dataset.vehicleDoor = code;
          button.textContent = labelText;
          button.setAttribute("aria-label", `${labelText} door`);
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
        doorControls.textContent = "Door controls are unavailable for this model.";
      }
      vehicleToolbar.append(doorControls);
      container.insertAdjacentElement("afterend", vehicleToolbar);
    }
    reset();
    status.textContent = "";
    draw = () => {
      frame = 0;
      if (disposed || document.hidden) return;
      const changed = controls.update();
      renderer.render(scene, camera);
      if (changed) invalidate();
    };
    invalidate();
    return { reset, dispose, setView };
  } catch (error) {
    dispose();
    throw error;
  }
}
