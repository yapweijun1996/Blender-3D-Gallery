import {
  Box3, DirectionalLight, HemisphereLight, PerspectiveCamera, Scene, Vector3, WebGLRenderer,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

export function loadModels(urls, signal, scenes) {
  const loader = new GLTFLoader();
  return Promise.allSettled(urls.map(async url => {
    const response = await fetch(url, { signal });
    if (!response.ok) throw new Error("Could not load a dress-up model");
    const data = await response.arrayBuffer();
    signal.throwIfAborted();
    const gltf = await loader.parseAsync(data, "");
    scenes.add(gltf.scene);
    return gltf;
  })).then(results => results.map(result => {
    if (result.status === "rejected") throw result.reason;
    return result.value;
  }));
}

export function disposeModels(scenes) {
  const resources = new Set();
  const bitmaps = new Set();
  for (const scene of scenes) scene.traverse(node => {
    if (node.geometry) resources.add(node.geometry);
    if (node.skeleton) resources.add(node.skeleton);
    for (const material of [node.material].flat().filter(Boolean)) {
      resources.add(material);
      for (const texture of Object.values(material).filter(value => value?.isTexture)) {
        resources.add(texture);
        if (texture.image?.close) bitmaps.add(texture.image);
      }
    }
  });
  for (const resource of resources) resource.dispose();
  for (const bitmap of bitmaps) bitmap.close();
}

export function createView(stage, model, bounds, advance) {
  const scene = new Scene();
  scene.add(model);
  const key = new DirectionalLight(0xffffff, 2.4);
  key.position.set(2, 3, 4);
  scene.add(key, new HemisphereLight(0xffffff, 0xa9a5b7, 2.1));

  // Reserve headroom for the vertical travel in Jump.
  const size = bounds.getSize(new Vector3());
  const target = bounds.getCenter(new Vector3());
  target.y += size.y * 0.12;
  const camera = new PerspectiveCamera(33, 1, 0.01, 30);
  const renderer = new WebGLRenderer({ alpha: true, antialias: true });
  const canvas = renderer.domElement;
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  canvas.setAttribute("aria-hidden", "true");
  stage.append(canvas);

  const controls = new OrbitControls(camera, canvas);
  controls.target.copy(target);
  controls.enablePan = false;
  controls.maxPolarAngle = Math.PI * 0.59;
  controls.minPolarAngle = Math.PI * 0.16;
  const angle = new Vector3(0.15, 0.07, 1).normalize();
  let dirty = true;
  let previousTime;
  let playing = false;
  const invalidate = () => { dirty = true; };
  controls.addEventListener("change", invalidate);

  function resize() {
    const { clientWidth, clientHeight } = stage;
    if (!clientWidth || !clientHeight) return;
    camera.aspect = clientWidth / clientHeight;
    const fit = Math.max(size.y * 1.42, size.x * 1.14 / camera.aspect);
    const distance = (fit / 2) / Math.tan(camera.fov * Math.PI / 360);
    if (previousTime === undefined) camera.position.copy(target).addScaledVector(angle, distance);
    else if (camera.position.distanceTo(target) < distance && camera.aspect < 1) {
      camera.position.sub(target).setLength(distance).add(target);
    }
    controls.minDistance = size.y * 0.85;
    controls.maxDistance = distance * 2.5;
    controls.update();
    camera.updateProjectionMatrix();
    renderer.setSize(clientWidth, clientHeight, false);
    invalidate();
  }

  const observer = new ResizeObserver(resize);
  resize();
  observer.observe(stage);
  renderer.setAnimationLoop(time => {
    const delta = previousTime === undefined ? 0 : Math.min((time - previousTime) / 1000, 0.05);
    previousTime = time;
    if (playing) advance(delta);
    if (playing || dirty) {
      renderer.render(scene, camera);
      dirty = false;
    }
  });
  return {
    canvas,
    setPlaying(value) { playing = value; },
    invalidate,
    get triangles() { return renderer.info.render.triangles; },
    dispose() {
      observer.disconnect();
      controls.dispose();
      renderer.setAnimationLoop(null);
      renderer.dispose();
      renderer.forceContextLoss();
      canvas.remove();
    },
  };
}

export const getBounds = model => new Box3().setFromObject(model, true);
