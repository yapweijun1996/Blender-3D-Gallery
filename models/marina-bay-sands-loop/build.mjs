import { writeFile } from 'node:fs/promises';
import * as THREE from 'three';
import { GLTFExporter } from 'three/addons/exporters/GLTFExporter.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

// GLTFExporter uses FileReader for the final binary Blob in Node.
globalThis.FileReader ??= class {
  readAsArrayBuffer(blob) {
    blob.arrayBuffer().then(result => {
      this.result = result;
      this.onloadend?.();
    });
  }
};

const scene = new THREE.Scene();
scene.name = 'Marina Bay Sands';
const root = new THREE.Group();
root.name = 'ASSET_MarinaBaySands';
scene.add(root);

function material(name, color, roughness = 0.77, metalness = 0) {
  return new THREE.MeshStandardMaterial({ name, color, roughness, metalness });
}
const palette = {
  earth: material('Cut waterfront base', 0x948a7b),
  land: material('Reclaimed land', 0xc7c1a9),
  water: material('Bay water', 0x2a777c, 0.29, 0.14),
  silver: material('Champagne aluminium', 0xdbdfdb, 0.47, 0.17),
  pale: material('Pale limestone', 0xe1ddca),
  trim: material('Blue grey shadowlines', 0x466365),
  glass: material('Jade curtain wall', 0x3d8290, 0.41, 0.12),
  glazing: material('Variegated glazing panels', 0xffffff, 0.25, 0.22),
  blue: material('Blue grey curtain wall', 0x316673, 0.4, 0.13),
  atrium: material('Dark atrium glass', 0x2e5057, 0.41, 0.1),
  wood: material('Teak observation deck', 0xcfa370),
  pool: material('Infinity pool', 0x39c8c3, 0.33),
  lawn: material('Roof garden', 0x698647),
  leaves: material('Tropical foliage', 0x4b744f),
  lightLeaves: material('Sunlit foliage', 0x85a04e),
  bark: material('Palm trunks', 0x947852),
  canvas: material('Sunshade canvas', 0xf6ecda),
  rail: material('Brushed stainless steel railing', 0xb1bab7, 0.38, 0.35),
  grout: material('Limestone paving joints', 0xaaa598),
};
palette.glazing = new THREE.MeshPhysicalMaterial({
  name: 'Coated jade architectural glass', color: 0xffffff, vertexColors: true,
  roughness: 0.12, metalness: 0.22, ior: 1.52, clearcoat: 1, clearcoatRoughness: 0.07,
});
for (const [key, color] of [['water', 0x337e81], ['pool', 0x49aaa8]]) {
  palette[key] = new THREE.MeshPhysicalMaterial({
    name: key === 'pool' ? 'Infinity pool water' : 'Bay water', color,
    roughness: 0.17, ior: 1.333, clearcoat: 1, clearcoatRoughness: 0.10,
  });
}
palette.leaves.side = THREE.DoubleSide;
palette.lightLeaves.side = THREE.DoubleSide;

const cube = new THREE.BoxGeometry();
const stem = new THREE.CylinderGeometry(0.58, 0.85, 1, 9);
const pane = new THREE.PlaneGeometry();
function mesh(parent, name, geometry, color, position = [0, 0, 0], scale = [1, 1, 1]) {
  const object = new THREE.Mesh(geometry, palette[color]);
  object.name = name;
  object.position.fromArray(position);
  object.scale.fromArray(scale);
  parent.add(object);
  return object;
}

function box(parent, name, color, x, y, z, width, height, depth) {
  return mesh(parent, name, cube, color, [x, y, z], [width, height, depth]);
}

function batchedBoxes(parent, name, color, dimensions) {
  const blocks = dimensions.map(([x, y, z, width, height, depth]) =>
    cube.clone().scale(width, height, depth).translate(x, y, z));
  return mesh(parent, name, mergeGeometries(blocks), color);
}

const duration = 20;
const tracks = [];
function stage(name, position, start, span, { lift = 0, vertical = false } = {}) {
  const group = new THREE.Group();
  group.name = name;
  group.position.fromArray(position);
  root.add(group);
  const times = [];
  const positions = [];
  const scales = [];
  function sample(time, fraction) {
    const progress = fraction * fraction * (3 - 2 * fraction);
    times.push(time);
    positions.push(position[0], position[1] + lift * (1 - progress), position[2]);
    scales.push(vertical ? 1 : progress, progress, vertical ? 1 : progress);
  }
  const steps = 16;
  sample(0, 0);
  for (let i = 0; i <= steps; i++) sample(start + span * i / steps, i / steps);
  for (let i = steps; i >= 0; i--) sample(duration - start - span * i / steps, i / steps);
  sample(duration, 0);
  tracks.push(new THREE.VectorKeyframeTrack(name + '.position', times, positions));
  tracks.push(new THREE.VectorKeyframeTrack(name + '.scale', times, scales));
  return group;
}

box(root, 'Waterfront terrain section', 'earth', 0, -0.113, 0, 14.4, 0.185, 7.3);
function waterSurface(parent, name, color, position, width, depth, columns, rows, amplitude) {
  const sheet = new THREE.PlaneGeometry(width, depth, columns, rows);
  const points = sheet.attributes.position;
  for (let i = 0; i < points.count; i++) {
    const x = points.getX(i), y = points.getY(i);
    const wave = Math.sin(y * 20 + x * 3 + Math.sin(x * 2.7)) +
      0.45 * Math.sin(y * 31 - x * 5.3) + 0.24 * Math.sin(x * 13 + y * 9);
    points.setZ(i, amplitude * wave);
  }
  sheet.computeVertexNormals();
  mesh(parent, name, sheet, color, position).rotation.x = -Math.PI / 2;
}
box(root, 'Bay edge', 'water', 0, -0.062, 0, 14.4, 0.08, 7.3);
waterSurface(root, 'Bay_Surface', 'water', [0, 0, 2.68], 14.4, 1.94, 170, 52, 0.004);
box(root, 'Bare waterfront land', 'land', 0, -0.011, -0.95, 14.4, 0.06, 5.40);

const base = stage('Waterfront_Promenade', [0, 0.02, -0.75], 0.54, 1.04, {lift: -0.08});
box(base, 'Waterfront promenade', 'pale', 0, 0.06, 2.15, 14.02, 0.12, 0.99);
for (let step = 0; step < 3; step++) {
  box(base, 'Promenade step ' + (step + 1), 'pale',
    -0.35, 0.030 - step * 0.018, 2.72 + step * 0.105, 11.7, 0.095, 0.15);
}
box(base, 'Hotel entry podium', 'pale', -0.05, 0.155, 0.15, 10.42, 0.31, 3.51);
box(base, 'Glazed lobby', 'atrium', -0.05, 0.32, 1.31, 9.9, 0.37, 0.48);
box(base, 'Lobby canopy', 'silver', -0.05, 0.53, 1.44, 10.02, 0.09, 0.73);
const lobbyColumns = [];
const plazaJoints = [];
for (let i = 0; i < 50; i++) {
  const x = -6.87 + i * 0.28;
  plazaJoints.push([x, 0.1207, 2.15, 0.005, 0.002, 0.98]);
  if (Math.abs(x) < 4.88) lobbyColumns.push([x, 0.33, 1.566, 0.025, 0.35, 0.034]);
}
for (let row = 1; row < 4; row++) {
  plazaJoints.push([0, 0.1207, 1.66 + row * 0.25, 14.0, 0.002, 0.005]);
}
batchedBoxes(base, 'Cut limestone paving joints', 'grout', plazaJoints);
batchedBoxes(base, 'Lobby glazing mullions', 'silver', lobbyColumns);
for (const x of [-3.53, -0.19, 3.15]) {
  box(base, 'Entrance portal', 'trim', x, 0.30, 1.597, 0.46, 0.30, 0.025);
  box(base, 'Portal lintel', 'pale', x, 0.459, 1.61, 0.53, 0.035, 0.072);
  box(base, 'Glass entrance doors', 'glass', x, 0.29, 1.616, 0.39, 0.264, 0.013);
  for (const offset of [-0.214, 0, 0.214]) {
    box(base, 'Door frame', 'silver', x + offset, 0.30, 1.628, 0.012, 0.31, 0.018);
  }
}

function loft(rings) {
  const points = [];
  const triangles = [];
  for (const ring of rings) points.push(...ring.flat());
  const n = rings[0].length;
  for (let row = 0; row < rings.length - 1; row++) {
    for (let i = 0; i < n; i++) {
      const a = row * n + i;
      const b = row * n + (i + 1) % n;
      triangles.push(a, b, b + n, a, b + n, a + n);
    }
  }
  for (let i = 1; i < n - 1; i++) {
    triangles.push(0, i + 1, i);
    const last = (rings.length - 1) * n;
    triangles.push(last, last + i, last + i + 1);
  }
  const indexed = new THREE.BufferGeometry();
  indexed.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  indexed.setIndex(triangles);
  const flat = indexed.toNonIndexed();
  flat.computeVertexNormals();
  return flat;
}

// Rings are clockwise seen from above so the top and the facade face out.
function rectangle(x, y, z, width, depth) {
  return [
    [x - width / 2, y, z + depth / 2], [x + width / 2, y, z + depth / 2],
    [x + width / 2, y, z - depth / 2], [x - width / 2, y, z - depth / 2],
  ];
}

const height = 6.38;
const floors = 55;
function plan(t, rear, lean) {
  const width = 1.96 - 0.15 * t;
  const depth = rear ? 0.63 + 0.18 * (1 - t) : 0.76;
  const z = rear ? -0.14 - lean * Math.pow(1 - t, 1.65) : 0.57 - 0.12 * t;
  return { width, depth, z };
}

function curtainWall(tower, towerIndex, rear, lean) {
  const panels = [];
  const bays = 13;
  for (let floor = 0; floor < floors; floor++) {
    const t = (floor + 0.5) / floors;
    const { width, depth, z } = plan(t, rear, lean);
    const bay = width / bays;
    const face = rear ? -1 : 1;
    const lower = plan(floor / floors, rear, lean);
    const upper = plan((floor + 1) / floors, rear, lean);
    const dz = upper.z - lower.z + face * (upper.depth - lower.depth) / 2;
    for (let column = 0; column < bays; column++) {
      const x = -width / 2 + (column + 0.5) * bay;
      const tone = ((floor * 17 + column * 23 + towerIndex * 11) % 37) / 36;
      const reflection = 0.25 + Math.sin(column * 0.43 + floor * 0.035 + towerIndex) * 0.15;
      const color = new THREE.Color(rear ? 0x315763 : 0x316e76).lerp(
        new THREE.Color(rear ? 0x56757a : 0x6d9d9d), reflection + tone * 0.10);
      const panel = pane.clone().scale(bay - 0.008, Math.hypot(height / floors, dz) - 0.009, 1);
      // Small pane-to-pane differences in the reflected sky are visible while orbiting.
      const normals = panel.attributes.normal;
      for (let corner = 0; corner < normals.count; corner++) {
        const normal = new THREE.Vector3((tone - 0.5) * 0.083 + (corner % 2 - 0.5) * 0.027,
          Math.sin(column * 1.8 + floor * 0.51) * 0.028, 1).normalize();
        normals.setXYZ(corner, normal.x, normal.y, normal.z);
      }
      if (rear) panel.rotateY(Math.PI);
      panel.rotateX(Math.atan2(dz, height / floors));
      panel.translate(x, height * t, z + face * (depth / 2 + 0.018));
      panel.setAttribute('color', new THREE.Float32BufferAttribute(
        Array.from({ length: 4 }, () => [color.r, color.g, color.b]).flat(), 3));
      panels.push(panel);
    }
  }
  mesh(tower, rear ? 'Individual east guestroom glazing' : 'Individual bay-facing guestroom glazing',
    mergeGeometries(panels), 'glazing');
}

function wingEndWalls(rings) {
  const positions = [];
  for (let floor = 0; floor < rings.length - 1; floor++) {
    for (const [a, b, side] of [[1, 2, 1], [3, 0, -1]]) {
      const offset = ([x, y, z]) => [x + side * 0.005, y, z];
      const lowerA = offset(rings[floor][a]);
      const lowerB = offset(rings[floor][b]);
      const upperA = offset(rings[floor + 1][a]);
      const upperB = offset(rings[floor + 1][b]);
      positions.push(...lowerA, ...lowerB, ...upperB, ...lowerA, ...upperB, ...upperA);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.computeVertexNormals();
  return geometry;
}

for (const [index, x] of [-3.53, -0.19, 3.15].entries()) {
  const skeleton = stage('Structural_Frame_' + (index + 1), [x, 0.24, -0.66],
    1.65 + index * 0.20, 1.68, { lift: -0.30, vertical: true });
  box(skeleton, 'Lift core', 'pale', 0, height / 2, 0.42, 0.48, height, 0.34);
  const slabs = [];
  for (let floor = 1; floor <= floors; floor++) {
    const t = floor / floors;
    const section = plan(t, false, 0);
    slabs.push([0, t * height, section.z, section.width - 0.045, 0.016, section.depth - 0.035]);
  }
  batchedBoxes(skeleton, 'Concrete floor plates', 'pale', slabs);
  const tower = stage('Hotel_Tower_' + (index + 1), [x, 0.24, -0.66],
    3.95 + index * 0.22, 1.0, { lift: -0.28, vertical: true });
  const lean = 1.83 - index * 0.15;
  for (const rear of [false, true]) {
    const rings = [];
    const bands = [];
    for (let i = 0; i <= floors; i++) {
      const t = i / floors;
      const { width, depth, z } = plan(t, rear, lean);
      rings.push(rectangle(0, height * t, z, width, depth));
      if (i === 0 || i === floors) continue;
      bands.push([0, height * t, z, width + 0.022, 0.010, depth + 0.045]);
    }
    mesh(tower, rear ? 'Curving east hotel wing' : 'Upright bay-facing hotel wing',
      loft(rings), rear ? 'blue' : 'glass');
    mesh(tower, 'Continuous aluminium end walls', wingEndWalls(rings), 'silver');
    batchedBoxes(tower, 'Horizontal window bands', 'silver', bands);
    curtainWall(tower, index, rear, lean);
  }
  box(tower, 'Crown connection', 'silver', 0, 6.29, 0.16, 1.74, 0.20, 1.38);
  for (const offset of [-0.55, 0, 0.55]) {
    box(tower, 'Crown support', 'trim', offset, 6.34, 0.61, 0.072, 0.14, 0.15);
  }
}

const park = stage('Sands_SkyPark', [-0.78, 6.56, -0.38], 5.52, 1.08, {lift: 1.25});
const hull = [
  [-6.1, 0.06], [-5.77, 0.54], [-4.75, 0.95], [-2.25, 1.06],
  [2.70, 1.02], [4.77, 0.78], [5.27, 0.38], [5.37, -0.03],
  [5.20, -0.43], [4.65, -0.72], [2.22, -0.91],
  [-2.75, -0.94], [-4.81, -0.75], [-5.62, -0.42],
];
const hullRing = (y, xScale, zScale) => hull.map(([x, z]) => [x * xScale, y, z * zScale]);
mesh(park, 'Cantilevered ship hull', loft([
  hullRing(0, 0.88, 0.60), hullRing(0.17, 0.98, 0.90),
  hullRing(0.31, 1, 1), hullRing(0.36, 1, 1),
]), 'silver');
mesh(park, 'Continuous SkyPark fascia reveal', loft([
  hullRing(0.304, 1.001, 1.005), hullRing(0.313, 1.001, 1.005),
]), 'trim');
mesh(park, 'Teak SkyPark deck', loft([hullRing(0.359, 0.984, 0.93), hullRing(0.39, 0.984, 0.93)]), 'wood');
box(park, 'Infinity pool coping', 'pale', 0.36, 0.414, 0.53, 5.36, 0.074, 0.54);
waterSurface(park, 'Infinity_pool_surface', 'pool', [0.36, 0.468, 0.55], 5.23, 0.44, 108, 16, 0.0016);
box(park, 'Rooftop garden beds', 'lawn', 0.42, 0.427, -0.42, 5.64, 0.08, 0.52);
box(park, 'Roof pavilion', 'atrium', 3.96, 0.55, -0.04, 0.98, 0.31, 0.68);
box(park, 'Pavilion roof', 'pale', 3.96, 0.725, -0.04, 1.12, 0.075, 0.81);

function guardrail(parent, outline) {
  const posts = [];
  const rails = [];
  for (let i = 0; i < outline.length; i++) {
    const [x1, z1] = outline[i];
    const [x2, z2] = outline[(i + 1) % outline.length];
    const dx = x2 - x1;
    const dz = z2 - z1;
    const length = Math.hypot(dx, dz);
    const spaces = Math.ceil(length / 0.24);
    for (let j = 0; j < spaces; j++) {
      posts.push([x1 + dx * j / spaces, 0.442, z1 + dz * j / spaces, 0.011, 0.105, 0.011]);
    }
    for (const y of [0.453, 0.493]) {
      rails.push(cube.clone().scale(length, 0.009, 0.011)
        .rotateY(-Math.atan2(dz, dx)).translate((x1 + x2) / 2, y, (z1 + z2) / 2));
    }
  }
  mesh(parent, 'Twin handrails', mergeGeometries(rails), 'rail');
  batchedBoxes(parent, 'SkyPark balusters', 'rail', posts);
}
guardrail(park, hull.map(([x, z]) => [x * 0.969, z * 0.90]));

const chairs = [];
const umbrellas = new THREE.ConeGeometry(1, 0.28, 10);
for (let i = 0; i < 18; i++) {
  const x = -2.17 + i * 0.285;
  chairs.push([x, 0.417, 0.17, 0.083, 0.022, 0.17]);
  chairs.push([x, 0.442, 0.098, 0.083, 0.049, 0.025]);
}
batchedBoxes(park, 'Poolside chaise lounges', 'canvas', chairs);
for (const x of [-4.24, -3.63, -2.98, 3.30]) {
  box(park, 'Umbrella stand', 'rail', x, 0.486, 0.02, 0.011, 0.19, 0.011);
  mesh(park, 'Pool terrace umbrella', umbrellas, 'canvas', [x, 0.585, 0.02], [0.145, 0.145, 0.145]);
}

function palmFrond() {
  const points = [];
  for (let step = 0; step <= 24; step++) {
    const t = step / 24;
    const x = t;
    const lift = Math.sin(t * Math.PI) * 0.26 - 0.28 * t * t;
    const serration = step % 2 ? 0.38 : 1;
    const edge = Math.sin(t * Math.PI) * 0.13 * serration;
    points.push(x, lift - edge * 0.6, -edge, x, lift, 0, x, lift - edge * 0.6, edge);
  }
  const faces = [];
  for (let row = 0; row < 24; row++) {
    const a = row * 3;
    for (let side = 0; side < 2; side++) {
      const i = a + side;
      if (row > 0) faces.push(i, i + 1, i + 3);
      if (row < 23) faces.push(i + 1, i + 4, i + 3);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  geometry.setIndex(faces);
  const surface = geometry.toNonIndexed();
  surface.computeVertexNormals();
  return surface;
}
const frond = palmFrond();
function tree(parent, x, y, z, size, index) {
  const trunk = mesh(parent, 'Palm trunk', stem, 'bark',
    [x, y + size * 0.34, z], [size * 0.038, size * 0.70, size * 0.038]);
  trunk.rotation.z = (index % 3 - 1) * 0.085;
  const crownX = x - Math.sin(trunk.rotation.z) * size * 0.35;
  for (let blade = 0; blade < 11; blade++) {
    const spread = size * (0.37 + (blade % 4) * 0.049);
    const leaf = mesh(parent, 'Palm frond', frond, blade % 3 ? 'leaves' : 'lightLeaves',
      [crownX, y + size * 0.68, z], [spread, spread, spread]);
    leaf.rotation.set(0, blade * 2.39996 + index * 1.33, 0.09 + (blade % 3) * 0.22, 'YXZ');
  }
}
for (let i = 0; i < 12; i++) {
  const x = -3.72 + i * 0.609;
  box(park, 'SkyPark raised planter', 'pale', x, 0.421, -0.45, 0.39, 0.062, 0.36);
  box(park, 'Planter foliage bed', 'lawn', x, 0.452, -0.45, 0.35, 0.025, 0.32);
  tree(park, x, 0.46, -0.45, 0.34 + i % 3 * 0.105, i);
}

const landscaping = stage('Ground_Gardens', [0, 0.025, 0], 8.42, 0.78, {lift: -0.12});
for (const [i, [x, z, size]] of [
  [-6.42, 0.38, 0.89], [-6.10, -0.55, 0.75], [5.68, 0.85, 0.89],
  [6.39, 0.16, 1.07], [5.92, -1.0, 0.92], [6.56, -1.57, 0.79],
].entries()) {
  box(landscaping, 'Waterfront planter curb', 'pale', x, 0.030, z, 0.69, 0.06, 0.67);
  box(landscaping, 'Waterfront planting bed', 'lawn', x, 0.061, z, 0.62, 0.02, 0.60);
  tree(landscaping, x, 0.073, z, size, i);
}

// The galleries radiate from an open rainwater oculus above the waterfront.
const museumOrigin = [-5.48, 0.04, 2.04];
const substructure = stage('Museum_Podium', museumOrigin, 0.83, 0.83);
mesh(substructure, 'Museum landing', new THREE.CylinderGeometry(1.34, 1.42, 0.14, 64), 'pale', [0, 0.075, 0]);
mesh(substructure, 'Entrance rotunda', new THREE.CylinderGeometry(0.69, 0.53, 0.43, 48), 'atrium', [0, 0.35, 0]);
const shell = stage('ArtScience_Museum', museumOrigin, 6.84, 1.35, { lift: 0.42 });
palette.porcelain = material('Ivory composite cladding', 0xf3f0e8, 0.36);
const funnel = new THREE.LatheGeometry([[0.19,0.38],[0.27,0.53],[0.48,0.62],[0.71,0.67]]
  .map(([r,y]) => new THREE.Vector2(r,y)), 72);
palette.porcelain.side = THREE.DoubleSide;
mesh(shell, 'Rain oculus dish', funnel, 'porcelain');
for (let finger = 0; finger < 10; finger++) {
  const angle = finger * Math.PI / 5;
  const length = 1.36 + 0.23 * Math.sin(angle + 1.1);
  const rise = 0.79 + 0.43 * Math.cos(angle + 2);
  const rings = [];
  for (let row = 0; row <= 16; row++) {
    const u = row / 16;
    const radius = 0.36 + u * length;
    const width = 0.105 + 0.21 * Math.sin(Math.PI * u * 0.87) + 0.07 * u;
    const y = 0.54 + rise * u * u;
    const ring = [];
    for (let edge = 0; edge < 20; edge++) {
      const arc = edge * Math.PI / 10;
      const tangent = width * Math.cos(arc);
      const vertical = (0.10 + 0.14 * Math.sin(Math.PI * u) + 0.055 * u) * Math.sin(arc);
      ring.push([radius * Math.cos(angle) - tangent * Math.sin(angle), y + vertical,
        radius * Math.sin(angle) + tangent * Math.cos(angle)]);
    }
    rings.push(ring);
  }
  const skin = loft(rings);
  mesh(shell, 'Lotus gallery ' + (finger + 1), skin, 'porcelain');
  const rim = rings.at(-1).map(([x,y,z]) => new THREE.Vector3(x,y,z));
  const center = rim.reduce((sum,v) => sum.add(v), new THREE.Vector3()).multiplyScalar(1/rim.length);
  const vertices = [];
  const outward = new THREE.Vector3(Math.cos(angle),0,Math.sin(angle)).multiplyScalar(0.008);
  for (let j = 0; j < rim.length; j++) {
    for (const point of [center,rim[j],rim[(j+1)%rim.length]]) {
      vertices.push(...point.clone().lerp(center,0.13).add(outward).toArray());
    }
  }
  const window = new THREE.BufferGeometry();
  window.setAttribute('position', new THREE.Float32BufferAttribute(vertices,3));
  window.computeVertexNormals();
  palette.atrium.side = THREE.DoubleSide;
  mesh(shell,'Gallery tip skylight',window,'atrium');
  mesh(substructure, 'Radial support', stem, 'silver',
    [0.52*Math.cos(angle),0.34,0.52*Math.sin(angle)], [0.06,0.46,0.06]);
}
root.userData.constructionStages = [
  [0,'site'], [0.54,'base'], [1.65,'frame'], [3.95,'glass'], [5.52,'skypark'],
  [6.84,'museum'], [8.42,'landscape'], [9.20,'complete'],
];
const clip = new THREE.AnimationClip('Land to Marina Bay Sands to Land', duration, tracks);
const glb = await new GLTFExporter().parseAsync(scene, { binary: true, animations: [clip] });
await writeFile(new URL('marina-bay-sands.glb', import.meta.url), Buffer.from(glb));
