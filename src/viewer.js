import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export default async function createViewer(
  container,
  url,
  status,
  signal,
  asset,
) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x657078);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
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
    const gltf = await new GLTFLoader().loadAsync(url, (event) => {
      if (!disposed)
        status.textContent = event.total
          ? `Loading the 3D model… ${Math.round((event.loaded / event.total) * 100)}%`
          : "Loading the 3D model…";
    });
    if (disposed || signal.aborted) {
      disposeModel(gltf.scene);
      throw new DOMException("Viewer closed", "AbortError");
    }
    model = gltf.scene;
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
      asset.family === "solar-system"
        ? new THREE.Vector3(0.55, 0.42, 1)
        : asset.category === "Balls"
          ? new THREE.Vector3(1, 0.3, 0.25)
          : new THREE.Vector3(1, 0.9, 1)
    ).normalize();
    const reset = () => {
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
    return { reset, dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
