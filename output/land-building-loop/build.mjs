import { writeFile } from 'node:fs/promises';
import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';

// GLTFExporter uses FileReader for its binary Blob even when there are no textures.
globalThis.FileReader ??= class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then(result => {
      this.result = result;
      this.onloadend?.();
    }, error => this.onerror?.(error));
  }
};

const scene = new THREE.Scene();
scene.name = 'Land to Building to Land';
const world = new THREE.Group();
world.name = 'Architectural Diorama';
scene.add(world);

const material = (name, color, roughness = 0.76, metalness = 0) =>
  new THREE.MeshStandardMaterial({ name, color, roughness, metalness });
const colors = {
  earth: material('Clay soil', 0x9c6751),
  grass: material('Olive lawn', 0x91a56d),
  site: material('Bare compacted earth', 0xc8aa7a),
  concrete: material('Warm concrete', 0xf1e4cb),
  paving: material('Sandstone paving', 0xdbccae),
  wall: material('Terracotta cladding', 0xba5636),
  trim: material('Dark bronze trim', 0x283936, 0.49),
  glass: material('Blue-green glass', 0x36717a, 0.28, 0.18),
  panes: material('Light blue-green glass', 0x5897a1, 0.33, 0.12),
  roof: material('Charcoal roofing', 0x374b49),
  solar: material('Photovoltaic cells', 0x274663, 0.38),
  bark: material('Tree bark', 0x785139),
  leaf: material('Sage foliage', 0x577a4d),
  lightLeaf: material('Golden foliage', 0xa6ae58),
};

const cube = new THREE.BoxGeometry();
const treeCanopy = new THREE.IcosahedronGeometry(1, 0);
const trunk = new THREE.CylinderGeometry(0.34, 0.55, 1, 6);

function mesh(parent, name, geometry, tint, x, y, z, sx, sy, sz) {
  const part = new THREE.Mesh(geometry, colors[tint]);
  part.name = name;
  part.position.set(x, y, z);
  part.scale.set(sx, sy, sz);
  parent.add(part);
  return part;
}

function box(parent, name, tint, x, y, z, width, height, depth) {
  return mesh(parent, name, cube, tint, x, y, z, width, height, depth);
}

const tracks = [];
const duration = 10;
function stage(name, x, y, z, start, span, rise) {
  const group = new THREE.Group();
  group.name = name;
  group.position.set(x, y, z);
  world.add(group);

  // Mirror each stage's samples so both directions share the same gentle easing.
  const times = [0];
  const positions = [x, y - rise, z];
  const scales = [0, 0, 0];
  const steps = 12;
  function sample(time, step) {
    const fraction = step / steps;
    const progress = fraction * fraction * (3 - 2 * fraction);
    times.push(time);
    positions.push(x, y - rise * (1 - progress), z);
    scales.push(progress, progress, progress);
  }
  for (let step = 0; step <= steps; step++) sample(start + span * step / steps, step);
  for (let step = steps; step >= 0; step--) sample(duration - start - span * step / steps, step);
  times.push(duration);
  positions.push(x, y - rise, z);
  scales.push(0, 0, 0);
  tracks.push(new THREE.VectorKeyframeTrack(name + '.position', times, positions));
  tracks.push(new THREE.VectorKeyframeTrack(name + '.scale', times, scales));
  return group;
}

box(world, 'Cut earth block', 'earth', 0, -0.31, 0, 8.9, 0.54, 7.5);
box(world, 'Lawn', 'grass', 0, -0.045, 0, 8.9, 0.095, 7.5);
box(world, 'Empty building plot', 'site', -0.25, 0.009, 0.1, 6.38, 0.022, 4.87);

const foundation = stage('Foundation', -0.25, 0.02, 0.1, 0.55, 0.76, 0.38);
box(foundation, 'Foundation slab', 'concrete', 0, 0.12, 0, 5.25, 0.24, 3.78);
box(foundation, 'Entry apron', 'paving', 0.7, 0.036, 2.14, 2.42, 0.07, 0.69);
box(foundation, 'Entry steps', 'concrete', 0.7, 0.065, 1.94, 1.49, 0.13, 0.42);

function story(number, height, time) {
  const unit = stage('Level ' + number, -0.25, height, 0.1, time, 0.95, 0.78);
  box(unit, 'Floor slab', 'concrete', 0, 0.057, 0, 4.8, 0.114, 3.43);
  box(unit, 'Rear wall', 'wall', 0, 0.62, -1.53, 4.56, 1.09, 0.22);
  box(unit, 'West wall', 'wall', -2.17, 0.62, -0.05, 0.22, 1.09, 3.02);
  box(unit, 'Front glass', 'glass', 0.04, 0.62, 1.52, 4.30, 1.01, 0.068);
  box(unit, 'East glass', 'panes', 2.19, 0.62, -0.02, 0.068, 1.01, 3.04);
  box(unit, 'West façade pier', 'wall', -1.99, 0.61, 1.55, 0.40, 1.10, 0.25);
  box(unit, 'Corner column', 'trim', 2.19, 0.62, 1.53, 0.087, 1.05, 0.085);
  for (let bay = 0; bay < 5; bay++) {
    box(unit, 'Front mullion ' + (bay + 1), 'trim',
      -1.76 + bay * 0.79, 0.62, 1.56, 0.052, 1.02, 0.08);
  }
  for (let bay = 0; bay < 3; bay++) {
    box(unit, 'East mullion ' + (bay + 1), 'trim',
      2.23, 0.62, -0.82 + bay * 0.78, 0.08, 1.02, 0.053);
  }
  box(unit, 'Front transom', 'trim', 0.12, 0.88, 1.573, 4.04, 0.04, 0.07);
  box(unit, 'East transom', 'trim', 2.226, 0.88, -0.02, 0.065, 0.04, 3.06);
  if (number === 1) {
    box(unit, 'Entrance canopy', 'concrete', 0.72, 0.97, 1.81, 1.53, 0.105, 0.64);
    box(unit, 'Entrance frame', 'trim', 0.72, 0.44, 1.577, 0.87, 0.70, 0.08);
    box(unit, 'Entrance door glass', 'panes', 0.72, 0.452, 1.628, 0.77, 0.64, 0.025);
    box(unit, 'Door handle', 'concrete', 0.93, 0.43, 1.65, 0.022, 0.16, 0.027);
  } else {
    for (let fin = 0; fin < 5; fin++) {
      box(unit, 'Terracotta sun fin ' + (fin + 1), 'wall',
        0.49 + fin * 0.31, 0.62, 1.65, 0.059, 0.91, 0.22);
    }
  }
}

story(1, 0.22, 1.10);
story(2, 1.38, 1.78);
story(3, 2.54, 2.46);

const roof = stage('Roof and solar array', -0.25, 3.70, 0.1, 3.11, 0.90, 0.72);
box(roof, 'Roof slab', 'concrete', 0, 0.092, 0, 4.96, 0.184, 3.58);
box(roof, 'Roof membrane', 'roof', 0, 0.195, 0, 4.65, 0.045, 3.30);
for (const z of [-1.70, 1.70]) box(roof, 'Long parapet', 'concrete', 0, 0.26, z, 4.96, 0.176, 0.16);
for (const x of [-2.40, 2.40]) box(roof, 'Short parapet', 'concrete', x, 0.26, 0, 0.16, 0.176, 3.26);
box(roof, 'Rooftop service core', 'wall', -1.47, 0.42, -0.56, 0.96, 0.42, 1.22);
box(roof, 'Service core cap', 'concrete', -1.47, 0.665, -0.56, 1.08, 0.1, 1.32);
for (let row = 0; row < 2; row++) {
  for (let column = 0; column < 3; column++) {
    const x = 0.14 + column * 0.64;
    const z = -0.51 + row * 0.98;
    const panel = box(roof, 'Solar panel', 'trim', x, 0.34, z, 0.59, 0.055, 0.80);
    panel.rotation.x = -0.24;
    const cells = box(roof, 'Solar panel cells', 'solar', x, 0.374, z, 0.53, 0.022, 0.73);
    cells.rotation.x = -0.24;
  }
}

const grounds = stage('Walkway', 0.45, 0.025, 2.67, 3.41, 0.78, 0.27);
for (let tile = 0; tile < 3; tile++) {
  box(grounds, 'Walkway stone ' + (tile + 1), 'paving', 0, 0.023, tile * 0.34, 1.05, 0.046, 0.29);
}

function tree(name, x, z, size, tint, time) {
  const group = stage(name, x, 0.012, z, time, 0.67, 0.36);
  mesh(group, 'Trunk', trunk, 'bark', 0, 0.37 * size, 0, 0.10 * size, 0.74 * size, 0.10 * size);
  const crown = mesh(group, 'Faceted crown', treeCanopy, tint, 0, 0.99 * size, 0, 0.43 * size, 0.53 * size, 0.43 * size);
  crown.rotation.y = 0.48;
}

tree('West tree', -3.45, 1.55, 1.10, 'leaf', 3.57);
tree('East rear tree', 3.31, -1.37, 1.32, 'leaf', 3.67);
tree('East front tree', 3.08, 1.57, 0.89, 'lightLeaf', 3.79);

const clip = new THREE.AnimationClip('Land → Building → Land', duration, tracks);
const glb = await new GLTFExporter().parseAsync(scene, { binary: true, animations: [clip] });
await writeFile(new URL('land-building-loop.glb', import.meta.url), Buffer.from(glb));
