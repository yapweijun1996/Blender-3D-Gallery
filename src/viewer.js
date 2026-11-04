import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export default async function createViewer(container, url, status, signal, asset) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x657078);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  if (asset.family === 'solar-system') {
    renderer.setClearColor(0x313840); renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1;
  }
  renderer.domElement.setAttribute('aria-label', `Interactive 3D ${asset.name}. Use the mouse or touch to rotate and zoom.`);
  renderer.domElement.setAttribute('role', 'img');
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.00001, 1000);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x535b53, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2.1);
  light.position.set(4, 7, 5);
  scene.add(light);
  let frame = 0;
  let model;
  let disposed = false;
  const resize = () => {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  const disposeModel = object => {
    object?.traverse(child => {
      child.geometry?.dispose();
      for (const material of (Array.isArray(child.material) ? child.material : [child.material])) {
        if (!material) continue;
        for (const value of Object.values(material)) if (value?.isTexture) value.dispose();
        material.dispose();
      }
    });
  };
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.dispose();
    disposeModel(model);
    renderer.dispose();
    renderer.domElement.remove();
    signal.removeEventListener('abort', dispose);
  };
  signal.addEventListener('abort', dispose, { once: true });
  renderer.domElement.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    if (!disposed) status.textContent = 'The 3D view was interrupted. Close and reopen it to retry.';
  });
  try {
    const gltf = await new GLTFLoader().loadAsync(url);
    if (disposed || signal.aborted) {
      disposeModel(gltf.scene);
      throw new DOMException('Viewer closed', 'AbortError');
    }
    model = gltf.scene;
    if (asset.details) model.rotation.y = asset.details.display.previewRotationY;
    scene.add(model);
    const bounds = new THREE.Box3().setFromObject(model);
    if (bounds.isEmpty()) throw new Error('Model has no visible bounds');
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const radius = Math.max(size.length() / 2, 0.001);
    camera.near = radius / 50;
    camera.far = radius * 50;
    controls.minDistance = radius * 1.05;
    controls.maxDistance = radius * 20;
    const direction = (asset.family === 'solar-system'
      ? new THREE.Vector3(.55, .42, 1)
      : asset.category === 'Balls'
      ? new THREE.Vector3(1, .3, .25)
      : new THREE.Vector3(1, .9, 1)).normalize();
    const reset = () => {
      resize();
      const vertical = THREE.MathUtils.degToRad(camera.fov / 2);
      const horizontal = Math.atan(Math.tan(vertical) * camera.aspect);
      const distance = radius / Math.sin(Math.min(vertical, horizontal)) * 1.08;
      camera.position.copy(center).addScaledVector(direction, distance);
      controls.target.copy(center);
      controls.update();
    };
    reset();
    status.textContent = '';
    const render = () => { controls.update(); renderer.render(scene, camera); frame = requestAnimationFrame(render); };
    render();
    return { reset, dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
