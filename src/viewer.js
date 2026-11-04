import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

export default async function createViewer(container, url, status) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0x657078);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-label', 'Interactive 3D billiards table. Use the mouse or touch to rotate and zoom.');
  renderer.domElement.setAttribute('role', 'img');
  container.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  scene.add(new THREE.HemisphereLight(0xffffff, 0x535b53, 2));
  const light = new THREE.DirectionalLight(0xffffff, 2.1);
  light.position.set(4, 7, 5);
  scene.add(light);
  let frame = 0;
  let model;
  const resize = () => {
    const { clientWidth: width, clientHeight: height } = container;
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(container);
  const dispose = () => {
    cancelAnimationFrame(frame);
    observer.disconnect();
    controls.dispose();
    if (model) model.traverse(object => {
      if (object.geometry) object.geometry.dispose();
      for (const material of (Array.isArray(object.material) ? object.material : [object.material])) {
        if (!material) continue;
        for (const value of Object.values(material)) if (value?.isTexture) value.dispose();
        material.dispose();
      }
    });
    renderer.dispose();
    renderer.domElement.remove();
  };
  renderer.domElement.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    status.textContent = 'The 3D view was interrupted. Close and reopen it to retry.';
  });
  try {
    const gltf = await new GLTFLoader().loadAsync(url);
    model = gltf.scene;
    scene.add(model);
    const bounds = new THREE.Box3().setFromObject(model);
    if (bounds.isEmpty()) throw new Error('Model has no visible bounds');
    const center = bounds.getCenter(new THREE.Vector3());
    const size = bounds.getSize(new THREE.Vector3());
    const distance = Math.max(size.x, size.y, size.z) * 1.4;
    const initial = center.clone().add(new THREE.Vector3(distance, distance * .9, distance));
    const reset = () => { camera.position.copy(initial); controls.target.copy(center); controls.update(); };
    reset();
    resize();
    status.textContent = '';
    const render = () => { controls.update(); renderer.render(scene, camera); frame = requestAnimationFrame(render); };
    render();
    return { reset, dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
