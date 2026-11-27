import * as THREE from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { LINK_HEIGHT, linkSegments, PLINTH_TOP, VIEW_ELEVATION, VIEW_YAW } from "./layout.js";

// Parts that move keep their own node; everything else is merged to cut draw calls.
const MOVING = /^(Truck_|Conveyor_Box_|Card_(Bottom|Middle|Top)$|Bar_|Output_Card$|Indicator$)/;
const bucket = value => Math.round(value * 4) / 4;

function plain(geometry, color, module) {
  const result = new THREE.BufferGeometry();
  const source = geometry.index ? geometry : geometry.clone().setIndex([...Array(geometry.attributes.position.count).keys()]);
  result.setIndex(source.index.clone());
  result.setAttribute("position", source.attributes.position.clone());
  if (source.attributes.normal) result.setAttribute("normal", source.attributes.normal.clone());
  else result.computeVertexNormals();
  const colors = new Float32Array(source.attributes.position.count * 3);
  for (let i = 0; i < colors.length; i += 3) color.toArray(colors, i);
  result.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  // Merging loses the object tree, so each vertex remembers its module for picking.
  result.setAttribute("module", new THREE.BufferAttribute(new Float32Array(source.attributes.position.count).fill(module), 1));
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

/** The module whose visible geometry the ray hits first; soft light and shadow layers are ignored. */
export function pickModule(composed, places, raycaster) {
  for (const hit of raycaster.intersectObject(composed.root, true)) {
    const merged = hit.object.geometry.getAttribute("module");
    if (merged) return places[merged.getX(hit.face.a)].id;
    let node = hit.object, effect = false;
    for (; node && !node.userData.module; node = node.parent) effect ||= node.name.startsWith("Fx_");
    if (!effect && node) return node.userData.module;
  }
  return null;
}

/** Where a module's label goes: above its highest point, with a pin touching it near the middle. */
function labelAnchor(group) {
  const yaw = VIEW_YAW * Math.PI / 180, elevation = VIEW_ELEVATION * Math.PI / 180;
  const right = new THREE.Vector3(Math.cos(yaw), 0, -Math.sin(yaw));
  const up = new THREE.Vector3(-Math.sin(yaw) * Math.sin(elevation), Math.cos(elevation), -Math.cos(yaw) * Math.sin(elevation));
  const points = [], solid = [];
  group.traverse(mesh => {
    if (!mesh.isMesh) return;
    for (let node = mesh; node && node !== group; node = node.parent) if (/^(Plinth_|Fx_)/.test(node.name)) return;
    // Thin lines, glass and handles count towards the height but make poor places for a pin.
    let thin = false;
    for (let node = mesh; node && node !== group; node = node.parent) thin ||= /Chart_|Glass|Handles/.test(node.name);
    const position = mesh.geometry.attributes.position;
    for (let i = 0; i < position.count; i++) {
      const point = new THREE.Vector3().fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld);
      points.push(point);
      if (!thin) solid.push(point);
    }
  });
  let low = Infinity, high = -Infinity, top = null;
  for (const point of points) {
    const side = point.dot(right);
    low = Math.min(low, side);
    high = Math.max(high, side);
    if (!top || point.dot(up) > top.dot(up)) top = point;
  }
  const middle = (low + high) / 2, band = (high - low) * 0.12;
  let best = null;
  for (const point of solid)
    if (Math.abs(point.dot(right) - middle) <= band && (!best || point.dot(up) > best.dot(up))) best = point;
  // The label clears the whole module; its leader reaches the point below its middle.
  return { pin: best, top };
}

export function composeModules(places, models) {
  const root = new THREE.Group(), groups = new Map(), parts = new Map(), anchors = new Map();
  const buckets = new Map(), owned = [];
  for (const place of places) {
    const group = new THREE.Group();
    group.position.set(place.x, 0, place.z);
    group.rotation.y = place.rotation;
    group.scale.setScalar(place.scale);
    group.userData.module = place.id;
    root.add(group);
    groups.set(place.id, group);
    const model = models.get(place.id);
    for (const node of [...model.children]) {
      // Resize what stands on the plinth around the centre of its top, leaving plinth and floor glow alone.
      if (!/^(Plinth_|Fx_ContactShadow$|Fx_FloorGlow$)/.test(node.name)) {
        const [width, height] = place.content, size = new THREE.Vector3(width, height, width);
        node.position.y -= PLINTH_TOP;
        node.position.multiply(size).y += PLINTH_TOP;
        node.scale.multiply(size);
      }
      group.add(node);
    }
    group.updateMatrixWorld(true);
    anchors.set(place.id, labelAnchor(group));
    for (const node of [...group.children]) {
      if (MOVING.test(node.name)) {
        parts.set(`${place.id}:${node.name}`, { node, home: node.position.clone(), size: node.scale.x, height: node.scale.y });
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
        const geometry = plain(mesh.geometry, material.color, places.indexOf(place)).applyMatrix4(mesh.matrixWorld);
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
  return { root, groups, parts, anchors };
}

/** Thin glowing lines with one node each, as drawn in the anchor. Nothing travels along them. */
export function createLinks() {
  const group = new THREE.Group(), paths = linkSegments();
  const ribbon = (width, height, color, opacity) => {
    const positions = [], indices = [];
    for (const { points } of paths) {
      const first = positions.length / 3;
      points.forEach(([x, z], i) => {
        const [ax, az] = points[Math.max(0, i - 1)], [bx, bz] = points[Math.min(points.length - 1, i + 1)];
        const length = Math.hypot(bx - ax, bz - az), ox = -(bz - az) / length * width / 2, oz = (bx - ax) / length * width / 2;
        positions.push(x + ox, height, z + oz, x - ox, height, z - oz);
        if (i) {
          const n = first + (i - 1) * 2;
          indices.push(n, n + 1, n + 2, n + 1, n + 3, n + 2);
        }
      });
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
    geometry.setIndex(indices);
    const mesh = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color, opacity, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
    mesh.renderOrder = 2;
    group.add(mesh);
  };
  ribbon(0.26, LINK_HEIGHT - 0.01, 0xffbe3d, 0.5);
  ribbon(0.085, LINK_HEIGHT, 0xffe9a0, 1);
  // The node sits on the plinth side face, so it is drawn over it.
  for (const [radius, color, opacity] of [[0.19, 0xffcf5c, 0.45], [0.085, 0xfffbe8, 1]]) {
    const nodes = new THREE.InstancedMesh(new THREE.CircleGeometry(radius, 16),
      new THREE.MeshBasicMaterial({ color, opacity, transparent: true, depthWrite: false, depthTest: false }), paths.length);
    const at = new THREE.Matrix4(), facing = new THREE.Quaternion().setFromEuler(
      new THREE.Euler(-VIEW_ELEVATION * Math.PI / 180, VIEW_YAW * Math.PI / 180, 0, "YXZ"));
    paths.forEach(({ node: [x, z] }, i) => nodes.setMatrixAt(i, at.compose(new THREE.Vector3(x, LINK_HEIGHT, z), facing, new THREE.Vector3(1, 1, 1))));
    nodes.renderOrder = 4;
    nodes.frustumCulled = false;
    group.add(nodes);
  }
  return { group };
}

/** Idle motion for the named parts. Time zero is the authored pose. */
export function animateParts(parts, time) {
  const wave = (speed, offset = 0) => Math.sin(time * speed + offset) - Math.sin(offset);
  const move = (key, x, y, z) => {
    const part = parts.get(key);
    if (part) part.node.position.set(part.home.x + x, part.home.y + y, part.home.z + z);
  };
  // The shopping bags stay on the floor: independent bobbing read as misplaced bags.
  const drive = wave(0.7) * 0.12;
  for (const name of ["Body", "Wheel_FL", "Wheel_FR", "Wheel_RL", "Wheel_RR"]) move(`delivery:Truck_${name}`, drive, 0, 0);
  move("warehouse:Conveyor_Box_1", 0, 0, wave(0.9) * 0.16);
  move("warehouse:Conveyor_Box_2", wave(0.9, 2.1) * 0.12, 0, 0);
  move("warehouse:Conveyor_Box_3", wave(0.9, 4.2) * 0.12, 0, 0);
  ["Bottom", "Middle", "Top"].forEach((level, i) => move(`payment:Card_${level}`, 0, wave(1.2, i * 1.3) * 0.045, 0));
  ["Low", "Mid", "High"].forEach((level, i) => {
    const bar = parts.get(`analytics:Bar_${level}`);
    if (bar) bar.node.scale.y = bar.height * (1 + wave(0.8, i * 1.1) * 0.07);
  });
  move("automation:Output_Card", 0, 0, wave(1.1) * 0.14);
  const light = parts.get("automation:Indicator");
  if (light) light.node.scale.setScalar(light.size * (1 + Math.abs(wave(3)) * 0.18));
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
