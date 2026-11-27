import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { linkSegments } from "./layout.js";

// Parts that move keep their own node; everything else is merged to cut draw calls.
const MOVING = /^(Bag_|Truck_|Conveyor_Box_|Card_(Bottom|Middle|Top)$|Bar_|Output_Card$|Indicator$)/;
const bucket = value => Math.round(value * 4) / 4;

function plain(geometry, color) {
  const result = new THREE.BufferGeometry();
  const source = geometry.index ? geometry : geometry.clone().setIndex([...Array(geometry.attributes.position.count).keys()]);
  result.setIndex(source.index.clone());
  result.setAttribute("position", source.attributes.position.clone());
  if (source.attributes.normal) result.setAttribute("normal", source.attributes.normal.clone());
  else result.computeVertexNormals();
  const colors = new Float32Array(source.attributes.position.count * 3);
  for (let i = 0; i < colors.length; i += 3) color.toArray(colors, i);
  result.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return result;
}

// Physical materials carry specular settings that must survive the merge.
const finish = material => material.isMeshPhysicalMaterial
  ? { roughness: bucket(material.roughness), metalness: bucket(material.metalness), side: material.side,
      specularIntensity: bucket(material.specularIntensity), ior: material.ior }
  : { roughness: bucket(material.roughness), metalness: bucket(material.metalness), side: material.side };

/** Opaque, non-emissive surfaces share a material per finish; their colour moves into the vertices. */
function mergeable(material) {
  return material.isMeshStandardMaterial && !material.transparent && !material.vertexColors &&
    material.emissive.getHex() === 0;
}

export function composeModules(places, models) {
  const root = new THREE.Group(), groups = new Map(), parts = new Map(), boxes = new Map();
  const buckets = new Map(), owned = [];
  for (const place of places) {
    const group = new THREE.Group();
    group.position.set(place.x, 0, place.z);
    group.rotation.y = place.rotation;
    group.scale.setScalar(place.scale);
    root.add(group);
    groups.set(place.id, group);
    const model = models.get(place.id);
    for (const node of [...model.children]) group.add(node);
    group.updateMatrixWorld(true);
    boxes.set(place.id, new THREE.Box3().setFromCenterAndSize(
      new THREE.Vector3(place.x, 1.2 * place.scale, place.z),
      new THREE.Vector3(place.radius * 2, 2.4 * place.scale, place.radius * 2)));
    for (const node of [...group.children]) {
      if (MOVING.test(node.name)) {
        parts.set(`${place.id}:${node.name}`, { node, home: node.position.clone() });
        node.traverse(mesh => { if (mesh.isMesh && !mesh.material.transparent) mesh.castShadow = mesh.receiveShadow = true; });
        continue;
      }
      const meshes = [];
      node.traverse(object => { if (object.isMesh) meshes.push(object); });
      for (const mesh of meshes) {
        const material = mesh.material;
        if (!mergeable(material)) {
          if (!material.transparent) mesh.castShadow = mesh.receiveShadow = true;
          continue;
        }
        const settings = finish(material), key = JSON.stringify(settings);
        if (!buckets.has(key)) buckets.set(key, { geometries: [], settings });
        const geometry = plain(mesh.geometry, material.color).applyMatrix4(mesh.matrixWorld);
        buckets.get(key).geometries.push(geometry);
        mesh.removeFromParent();
        mesh.geometry.dispose();
        material.dispose();
      }
    }
  }
  for (const { geometries, settings } of buckets.values()) {
    const geometry = mergeGeometries(geometries);
    for (const source of geometries) source.dispose();
    if (!geometry) throw new Error("Commerce hub parts could not be merged");
    const Material = "ior" in settings ? THREE.MeshPhysicalMaterial : THREE.MeshStandardMaterial;
    const mesh = new THREE.Mesh(geometry, new Material({ vertexColors: true, ...settings }));
    mesh.castShadow = mesh.receiveShadow = true;
    root.add(mesh);
    owned.push(mesh);
  }
  return { root, groups, parts, boxes };
}

/** Flat glowing ribbons on the floor, with one travelling pulse per link. */
export function createLinks(places) {
  const group = new THREE.Group(), segments = linkSegments(places);
  const ribbon = (width, height, color, opacity) => {
    const positions = [], indices = [];
    segments.forEach(({ a, b }, i) => {
      const dx = b[0] - a[0], dz = b[1] - a[1], length = Math.hypot(dx, dz);
      const ox = -dz / length * width / 2, oz = dx / length * width / 2;
      positions.push(a[0] + ox, height, a[1] + oz, a[0] - ox, height, a[1] - oz,
        b[0] - ox, height, b[1] - oz, b[0] + ox, height, b[1] + oz);
      const n = i * 4;
      indices.push(n, n + 2, n + 1, n, n + 3, n + 2);
    });
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color, opacity, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
    mesh.renderOrder = 2;
    group.add(mesh);
  };
  ribbon(0.56, 0.03, 0xffcf5c, 0.34);
  ribbon(0.26, 0.035, 0xffd970, 0.6);
  ribbon(0.11, 0.04, 0xfff6d2, 1);
  // A glowing node marks where each link meets its plinth.
  const ends = segments.flatMap(({ a, b }) => [a, b]);
  for (const [radius, color, opacity, height] of [[0.34, 0xffcf5c, 0.4, 0.045], [0.16, 0xfff6d2, 1, 0.05]]) {
    const nodes = new THREE.InstancedMesh(new THREE.CircleGeometry(radius, 14).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color, opacity, transparent: true, depthWrite: false }), ends.length);
    const at = new THREE.Matrix4();
    ends.forEach(([x, z], i) => nodes.setMatrixAt(i, at.makeTranslation(x, height, z)));
    nodes.renderOrder = 2;
    nodes.frustumCulled = false;
    group.add(nodes);
  }
  const pulses = new THREE.InstancedMesh(new THREE.CircleGeometry(0.17, 12).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: 0xfff3cf, transparent: true, depthWrite: false }), segments.length);
  pulses.renderOrder = 3;
  pulses.frustumCulled = false;
  group.add(pulses);
  const matrix = new THREE.Matrix4();
  const update = time => {
    segments.forEach(({ a, b }, i) => {
      const t = (time * 0.32 + i * 0.137) % 1;
      pulses.setMatrixAt(i, matrix.makeTranslation(a[0] + (b[0] - a[0]) * t, 0.06, a[1] + (b[1] - a[1]) * t));
    });
    pulses.instanceMatrix.needsUpdate = true;
  };
  update(0);
  return { group, update };
}

/** Idle motion for the named parts. Time zero is the authored pose. */
export function animateParts(parts, time) {
  const wave = (speed, offset = 0) => Math.sin(time * speed + offset) - Math.sin(offset);
  const move = (key, x, y, z) => {
    const part = parts.get(key);
    if (part) part.node.position.set(part.home.x + x, part.home.y + y, part.home.z + z);
  };
  ["Large", "Medium", "Small"].forEach((size, i) => {
    const lift = Math.abs(wave(1.4, i * 1.9)) * 0.05;
    move(`bags:Bag_${size}`, 0, lift, 0);
    move(`bags:Bag_${size}_Handles`, 0, lift, 0);
  });
  const drive = wave(0.7) * 0.12;
  for (const name of ["Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"]) move(`delivery:Truck_${name}`, drive, 0, 0);
  move("warehouse:Conveyor_Box_1", 0, 0, wave(0.9) * 0.16);
  move("warehouse:Conveyor_Box_2", wave(0.9, 2.1) * 0.12, 0, 0);
  move("warehouse:Conveyor_Box_3", wave(0.9, 4.2) * 0.12, 0, 0);
  ["Bottom", "Middle", "Top"].forEach((level, i) => move(`payment:Card_${level}`, 0, wave(1.2, i * 1.3) * 0.045, 0));
  ["Low", "Mid", "High"].forEach((level, i) => {
    const bar = parts.get(`analytics:Bar_${level}`);
    if (bar) bar.node.scale.y = 1 + wave(0.8, i * 1.1) * 0.07;
  });
  move("automation:Output_Card", 0, 0, wave(1.1) * 0.14);
  const light = parts.get("automation:Indicator");
  if (light) light.node.scale.setScalar(1 + Math.abs(wave(3)) * 0.18);
}

export function disposeTree(object) {
  const materials = new Set();
  object.traverse(child => {
    child.geometry?.dispose();
    if (child.isInstancedMesh) child.dispose();
    if (child.material) for (const material of [].concat(child.material)) materials.add(material);
  });
  for (const material of materials) material.dispose();
}
