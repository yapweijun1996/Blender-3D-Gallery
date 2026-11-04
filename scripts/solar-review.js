import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
const renderer = new THREE.WebGLRenderer({
  antialias: true,
  preserveDrawingBuffer: true,
});
renderer.setSize(640, 640);
renderer.setPixelRatio(1);
renderer.setClearColor(0x313840);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
document.body.append(renderer.domElement);
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 100);
scene.add(new THREE.HemisphereLight(0xffffff, 0x667080, 2));
const light = new THREE.DirectionalLight(0xffffff, 2.1);
light.position.set(4, 5, 6);
scene.add(light);
let model;
const loader = new GLTFLoader();
const dispose = () =>
  model?.traverse((o) => {
    o.geometry?.dispose();
    for (const m of o.material ? [].concat(o.material) : []) {
      for (const v of Object.values(m)) if (v?.isTexture) v.dispose();
      m.dispose();
    }
  });
window.reviewAsset = async (id, angle = 0) => {
  dispose();
  if (model) scene.remove(model);
  const gltf = await loader.loadAsync(`/models/solar-system/exports/${id}.glb`);
  model = gltf.scene;
  model.rotation.y = { jupiter: -2.05, pluto: -1.1 }[id] ?? 0;
  scene.add(model);
  model.updateMatrixWorld(true);
  let triangles = 0,
    vertices = 0,
    degenerate = 0,
    invalid = 0,
    normalErrors = 0,
    inward = 0;
  const textures = new Map();
  const materials = [];
  model.traverse((o) => {
    if (!o.matrixWorld.elements.every(Number.isFinite)) invalid++;
    if (!o.isMesh) return;
    const g = o.geometry,
      p = g.attributes.position,
      n = g.attributes.normal,
      idx = g.index;
    vertices += p.count;
    triangles += (idx?.count ?? p.count) / 3;
    for (let i = 0; i < p.count; i++) {
      if (![p.getX(i), p.getY(i), p.getZ(i)].every(Number.isFinite)) invalid++;
      if (
        n &&
        (![n.getX(i), n.getY(i), n.getZ(i)].every(Number.isFinite) ||
          Math.abs(Math.hypot(n.getX(i), n.getY(i), n.getZ(i)) - 1) > 0.01)
      )
        normalErrors++;
    }
    const a = new THREE.Vector3(),
      b = new THREE.Vector3(),
      c = new THREE.Vector3(),
      cross = new THREE.Vector3(),
      avg = new THREE.Vector3();
    for (let i = 0; i < (idx?.count ?? p.count); i += 3) {
      const ia = idx ? idx.getX(i) : i,
        ib = idx ? idx.getX(i + 1) : i + 1,
        ic = idx ? idx.getX(i + 2) : i + 2;
      a.fromBufferAttribute(p, ia);
      b.fromBufferAttribute(p, ib);
      c.fromBufferAttribute(p, ic);
      cross.crossVectors(b.sub(a), c.sub(a));
      if (cross.lengthSq() < 1e-18) degenerate++;
      if (n) {
        avg.fromBufferAttribute(n, ia);
        if (cross.dot(avg) < -1e-9) inward++;
      }
    }
    for (const m of [].concat(o.material)) {
      materials.push({
        name: m.name,
        roughness: m.roughness,
        metalness: m.metalness,
        transparent: m.transparent,
        opacity: m.opacity,
        side: m.side,
      });
      for (const key of [
        "map",
        "emissiveMap",
        "normalMap",
        "roughnessMap",
        "metalnessMap",
        "alphaMap",
      ]) {
        const t = m[key];
        if (t) {
          const im = t.image;
          if (!im?.width || !im?.height) invalid++;
          if (
            ["map", "emissiveMap"].includes(key)
              ? t.colorSpace !== THREE.SRGBColorSpace
              : t.colorSpace !== THREE.NoColorSpace
          )
            invalid++;
          textures.set(t.uuid, {
            width: im?.width,
            height: im?.height,
            colorSpace: t.colorSpace,
            role: key,
          });
        }
      }
    }
  });
  const box = new THREE.Box3().setFromObject(model),
    size = box.getSize(new THREE.Vector3()),
    center = box.getCenter(new THREE.Vector3());
  const radius = size.length() / 2;
  camera.near = radius / 100;
  camera.far = radius * 100;
  camera.updateProjectionMatrix();
  camera.position
    .copy(center)
    .add(
      new THREE.Vector3(Math.sin(angle) * 0.9 + 0.55, 0.42, Math.cos(angle))
        .normalize()
        .multiplyScalar(
          (radius / Math.sin(THREE.MathUtils.degToRad(17.5))) * 1.03,
        ),
    );
  camera.lookAt(center);
  document.querySelector("#name").textContent = id;
  renderer.render(scene, camera);
  const tex = [...textures.values()];
  return {
    id,
    triangles,
    vertices,
    degenerate,
    invalid,
    normalErrors,
    inward,
    bounds: { min: box.min.toArray(), max: box.max.toArray() },
    textures: tex,
    textureMemoryBytes: tex.reduce(
      (s, t) => s + (t.width * t.height * 4 * 4) / 3,
      0,
    ),
    materials,
    renderer: renderer.info.render,
    allPass:
      triangles > 0 &&
      !degenerate &&
      !invalid &&
      !normalErrors &&
      !inward &&
      !box.isEmpty() &&
      box.min.toArray().every(Number.isFinite) &&
      box.max.toArray().every(Number.isFinite),
  };
};
window.solarReviewReady = true;
