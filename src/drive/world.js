import {
  BoxGeometry, BufferAttribute, BufferGeometry, CanvasTexture, Color, ConeGeometry, CylinderGeometry, DirectionalLight, DoubleSide,
  Fog, Group, HemisphereLight, InstancedMesh, Matrix4, Mesh, MeshBasicMaterial, MeshLambertMaterial, PerspectiveCamera,
  PlaneGeometry, Quaternion, RepeatWrapping, Scene, SphereGeometry, Vector3, WebGLRenderer,
} from "three";
import { findRoad, project, sample } from "./route.js";
import { buildLandmarkModels, buildScenery } from "./scenery.js";

const ROAD_HALF_WIDTH = 5.5;
const rng = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;

const SKY = [
  { hour: 17.5, sky: 0xf2b27c, ground: 0x6f7a55, sun: 2.4, lamp: 0 },
  { hour: 18.6, sky: 0xb7737f, ground: 0x4b5545, sun: 1.2, lamp: 0.5 },
  { hour: 19.3, sky: 0x2e3566, ground: 0x2a3030, sun: 0.45, lamp: 1 },
  { hour: 19.75, sky: 0x0d1530, ground: 0x1a2124, sun: 0.2, lamp: 1 },
];
const mix = (a, b, t) => a + (b - a) * t;
function skyAt(hour) {
  let i = 0;
  while (i < SKY.length - 2 && hour > SKY[i + 1].hour) i++;
  const a = SKY[i], b = SKY[i + 1], t = Math.max(0, Math.min(1, (hour - a.hour) / (b.hour - a.hour)));
  return {
    sky: new Color(a.sky).lerp(new Color(b.sky), t), ground: new Color(a.ground).lerp(new Color(b.ground), t),
    sun: mix(a.sun, b.sun, t), lamp: mix(a.lamp, b.lamp, t),
  };
}

function roadTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 128; canvas.height = 256;
  const g = canvas.getContext("2d");
  g.fillStyle = "#3d4046"; g.fillRect(0, 0, 128, 256);
  // Fine asphalt grain and two faint tyre tracks per lane.
  for (let i = 0; i < 1400; i++) { g.fillStyle = `rgba(${i % 2 ? 255 : 0},${i % 2 ? 255 : 0},${i % 2 ? 255 : 0},.05)`; g.fillRect(Math.random() * 128, Math.random() * 256, 2, 2); }
  g.fillStyle = "rgba(0,0,0,.14)";
  for (const x of [24, 40, 88, 104]) g.fillRect(x, 0, 8, 256);
  // Solid white edge lines and a yellow dashed centre line.
  g.fillStyle = "#e9e6da"; g.fillRect(6, 0, 4, 256); g.fillRect(118, 0, 4, 256);
  g.fillStyle = "#f0cf5a"; g.fillRect(62, 20, 4, 96);
  const texture = new CanvasTexture(canvas);
  texture.wrapT = RepeatWrapping;
  texture.anisotropy = 8;
  return texture;
}

/** A strip between two lateral offsets (and heights) along the route, only where include(distance) holds. */
function stripBetween(route, step, offA, offB, yA, yB, include, material) {
  const positions = [], indices = [];
  const count = Math.ceil(route.length / step);
  for (let i = 0; i < count; i++) {
    const d0 = i * step, d1 = Math.min(route.length, (i + 1) * step);
    if (!include((d0 + d1) / 2)) continue;
    const a0 = sample(route, d0, offA), b0 = sample(route, d0, offB), a1 = sample(route, d1, offA), b1 = sample(route, d1, offB);
    const k = positions.length / 3;
    positions.push(a0.x, yA, a0.z, b0.x, yB, b0.z, a1.x, yA, a1.z, b1.x, yB, b1.z);
    indices.push(k, k + 1, k + 2, k + 1, k + 3, k + 2);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new Mesh(geometry, material);
}

function ribbon(route, step, half, y, texture, uvScale) {
  const positions = [], uvs = [], indices = [];
  const count = Math.ceil(route.length / step) + 1;
  for (let i = 0; i < count; i++) {
    const distance = Math.min(route.length, i * step);
    const a = sample(route, distance, half), b = sample(route, distance, -half);
    positions.push(a.x, y, a.z, b.x, y, b.z);
    uvs.push(0, distance / uvScale, 1, distance / uvScale);
    if (i) { const k = (i - 1) * 2; indices.push(k, k + 1, k + 2, k + 1, k + 3, k + 2); }
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  geometry.setAttribute("uv", new BufferAttribute(new Float32Array(uvs), 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new Mesh(geometry, new MeshLambertMaterial({ map: texture, side: DoubleSide }));
}

/** Zones along the route decide what stands beside the road. */
function zoneAt(route, distance) {
  const bukit = findRoad(route, "Pan-Island Expressway") ?? findRoad(route, "Bukit Timah Expressway") ?? 1e9;
  const woodlands = findRoad(route, "Woodlands Crossing") ?? 1e9;
  const causeway = findRoad(route, "Causeway") ?? 1e9;
  const ciq = findRoad(route, "JB CIQ") ?? 1e9;
  if (distance < 1500) return "bay";
  if (distance < bukit) return "city";
  if (distance < woodlands) return "expressway";
  if (distance < causeway) return "checkpoint";
  if (distance < ciq) return "water";
  return "johor";
}

function addInstances(scene, geometry, material, items) {
  const mesh = new InstancedMesh(geometry, material, items.length);
  const matrix = new Matrix4(), quaternion = new Quaternion(), up = new Vector3(0, 1, 0);
  items.forEach((item, index) => {
    quaternion.setFromAxisAngle(up, item.yaw ?? 0);
    matrix.compose(new Vector3(item.x, item.y ?? 0, item.z), quaternion, new Vector3(item.sx ?? 1, item.sy ?? 1, item.sz ?? 1));
    mesh.setMatrixAt(index, matrix);
    if (item.color && mesh.setColorAt) mesh.setColorAt(index, new Color(item.color));
  });
  mesh.instanceMatrix.needsUpdate = true;
  if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
  mesh.frustumCulled = false;
  scene.add(mesh);
  return mesh;
}

const PALETTE = [0xe8d8c0, 0xcfc3b0, 0xb8c8c4, 0xd8b8a0, 0xa9b7c9, 0xe3c9a6, 0xc5d0b5];

/** Nearest distance from a point to any route sample, with a grid so the check is cheap. */
function routeProximity(route) {
  const cell = 40, grid = new Map();
  for (const p of route.points) {
    const key = `${Math.floor(p.x / cell)},${Math.floor(p.z / cell)}`;
    (grid.get(key) ?? grid.set(key, []).get(key)).push(p);
  }
  return (x, z, limit) => {
    const cx = Math.floor(x / cell), cz = Math.floor(z / cell), reach = Math.ceil(limit / cell);
    let best = Infinity;
    for (let i = -reach; i <= reach; i++) for (let j = -reach; j <= reach; j++)
      for (const p of grid.get(`${cx + i},${cz + j}`) ?? []) best = Math.min(best, Math.hypot(p.x - x, p.z - z));
    return best;
  };
}

function buildSurroundings(scene, route) {
  const random = rng(20261120);
  const nearest = routeProximity(route);
  const blocks = [], trees = [], lamps = [];
  for (let distance = 30; distance < route.length - 20; distance += 22) {
    const zone = zoneAt(route, distance);
    for (const side of [-1, 1]) {
      const pose = sample(route, distance + random() * 10, side * (30 + random() * 50));
      const lampPose = sample(route, distance, side * (ROAD_HALF_WIDTH + 1.2));
      if (zone !== "water") lamps.push({ x: lampPose.x, z: lampPose.z, y: 4, sy: 1, yaw: lampPose.heading });
      if (zone === "water") continue;
      const height = zone === "city" ? 14 + random() * 52 : zone === "bay" ? 20 + random() * 60
        : zone === "johor" ? 8 + random() * 26 : zone === "checkpoint" ? 5 + random() * 10 : 3 + random() * 6;
      const wide = zone === "city" || zone === "bay" ? 14 + random() * 14 : 9 + random() * 10;
      if ((zone !== "expressway" || random() > 0.55) && nearest(pose.x, pose.z, 60) > wide * 0.9 + ROAD_HALF_WIDTH + 4)
        blocks.push({ x: pose.x, z: pose.z, y: height / 2, sx: wide, sy: height, sz: wide * (0.8 + random() * 0.6), yaw: pose.heading, color: PALETTE[Math.floor(random() * PALETTE.length)] });
      for (let k = 0; k < (zone === "expressway" ? 4 : 2); k++) {
        const near = sample(route, distance + random() * 22, side * (ROAD_HALF_WIDTH + 5 + random() * 16));
        if (nearest(near.x, near.z, 20) > ROAD_HALF_WIDTH + 2.5) trees.push({ x: near.x, z: near.z, y: 2.5, sx: 0.8 + random() * 0.5, sy: 0.8 + random() * 0.8, sz: 0.8 + random() * 0.5 });
      }
    }
  }
  const buildings = addInstances(scene, new BoxGeometry(1, 1, 1), new MeshLambertMaterial({ color: 0xffffff }), blocks);
  const trunk = addInstances(scene, new ConeGeometry(1.1, 5, 6), new MeshLambertMaterial({ color: 0x3f7a45 }), trees);
  const lampMaterial = new MeshBasicMaterial({ color: 0xffe3a0 });
  const poles = addInstances(scene, new BoxGeometry(0.25, 8, 0.25), new MeshLambertMaterial({ color: 0x59616a }), lamps);
  const heads = addInstances(scene, new BoxGeometry(0.9, 0.3, 0.5), lampMaterial, lamps.map(l => ({ ...l, y: 8 })));
  return { buildings, trunk, poles, heads, lampMaterial };
}

function tower(x, z, w, h, d, color, yaw = 0) {
  const mesh = new Mesh(new BoxGeometry(w, h, d), new MeshLambertMaterial({ color }));
  mesh.position.set(x, h / 2, z);
  mesh.rotation.y = yaw;
  return mesh;
}

function buildLandmarks(scene, route) {
  const group = new Group();
  // Marina Bay Sands: three leaning towers joined by a sky park, on the bay side of the start.
  const start = sample(route, 0, -90);
  const towers = new Group();
  for (const [i, shift] of [-38, 0, 38].entries()) {
    const t = tower(shift, 0, 26, 190, 34, 0xcdd5dc);
    t.position.y = 95; t.rotation.z = (i - 1) * 0.03;
    towers.add(t);
  }
  const park = tower(0, 0, 150, 8, 40, 0xe9edf0); park.position.y = 194;
  const boat = tower(0, 0, 60, 6, 22, 0xc7d4dc); boat.position.set(36, 202, 0);
  towers.add(park, boat);
  towers.position.set(start.x, 0, start.z);
  towers.rotation.y = start.heading + Math.PI / 2;
  group.add(towers);
  const gates = [];
  // Woodlands checkpoint: a canopy over the road, with booths and a barrier.
  const checkpoint = findRoad(route, "Woodlands border checkpoint (cars) - zone 4") ?? findRoad(route, "Woodlands border checkpoint");
  const stop = (checkpoint ?? route.length * 0.75) + 150;
  const at = sample(route, stop);
  const gate = new Group();
  gate.position.set(at.x, 0, at.z);
  gate.rotation.y = at.heading;
  const canopy = tower(0, 0, 26, 1.2, 14, 0x2f5d8a); canopy.position.y = 6.4;
  gate.add(canopy);
  for (const x of [-7, 0, 7]) {
    const booth = tower(x * 1.2 + (x === 0 ? 0 : x > 0 ? 2 : -2), 0, 2.2, 3.4, 3, 0xe7edf2);
    booth.position.z = 0;
    gate.add(booth);
  }
  const barrier = new Mesh(new BoxGeometry(9, 0.25, 0.25), new MeshLambertMaterial({ color: 0xd13b2f }));
  barrier.position.set(-1.5, 1.1, 5);
  const pivot = new Group();
  pivot.position.set(-5.7, 1.1, 5);
  barrier.position.set(4.5, 0, 0);
  pivot.add(barrier);
  gate.add(pivot);
  group.add(gate);
  gates.push({ stop, barrier: pivot });
  // Johor Bahru: tall towers near the end of the route.
  const endPose = sample(route, route.length, 70);
  const southkey = new Group();
  for (const [x, z, h, c] of [[0, 0, 150, 0xa5b4c4], [34, 18, 120, 0xb9c4cf], [-30, 24, 100, 0x9eaebf], [10, -36, 130, 0xc7ccd6]]) southkey.add(tower(x, z, 24, h, 24, c));
  southkey.position.set(endPose.x, 0, endPose.z);
  group.add(southkey);
  scene.add(group);
  return { gates, stop };
}

/** Curbs, sidewalks and zebra crossings; the kerb and sidewalk only appear in built-up stretches. */
function buildRoadKit(scene, route) {
  const built = distance => { const z = zoneAt(route, distance); return z === "bay" || z === "city" || z === "johor"; };
  const curbMaterial = new MeshLambertMaterial({ color: 0xb9b2a2, side: DoubleSide });
  const walkMaterial = new MeshLambertMaterial({ color: 0xcfc6b2, side: DoubleSide });
  for (const side of [-1, 1]) {
    const edge = side * (ROAD_HALF_WIDTH + 0.2);
    scene.add(stripBetween(route, 10, edge, side * (ROAD_HALF_WIDTH + 3.6), 0.3, 0.3, built, walkMaterial));
    scene.add(stripBetween(route, 10, edge, edge, 0.12, 0.3, built, curbMaterial));
    scene.add(stripBetween(route, 10, edge, side * (ROAD_HALF_WIDTH + 0.2), 0.14, 0.14, built, curbMaterial));
  }
  // Zebra crossings every 300 m in built-up stretches.
  const stripes = [];
  for (let d = 150; d < route.length - 100; d += 300) {
    if (!built(d)) continue;
    const pose = sample(route, d);
    for (let k = -4; k <= 4; k++) {
      const spot = sample(route, d, k * 1.15);
      stripes.push({ x: spot.x, z: spot.z, y: 0.16, sx: 0.6, sy: 0.02, sz: 3.2, yaw: pose.heading });
    }
  }
  if (stripes.length) addInstances(scene, new BoxGeometry(1, 1, 1), new MeshLambertMaterial({ color: 0xf2f0e6 }), stripes);
}

function buildWater(scene, route) {
  const group = new Group();
  const material = new MeshLambertMaterial({ color: 0x2f5f7f });
  const bay = new Mesh(new PlaneGeometry(2400, 2200), material);
  bay.rotation.x = -Math.PI / 2;
  const first = sample(route, 0, -1300);
  bay.position.set(first.x, 0.05, first.z);
  group.add(bay);
  const causeway = findRoad(route, "Johor–Singapore Causeway") ?? route.length * 0.78;
  const ciq = findRoad(route, "JB CIQ") ?? route.length * 0.85;
  const strait = new Mesh(new PlaneGeometry(12000, Math.max(300, ciq - causeway) * 0.9), material);
  strait.rotation.x = -Math.PI / 2;
  const mid = sample(route, (causeway + ciq) / 2);
  strait.position.set(mid.x, 0.06, mid.z);
  group.add(strait);
  scene.add(group);
  return group;
}

export function buildWorld(canvasHost, route, kit = new Map()) {
  const useKit = ["building_hdb", "tree_street", "street_lamp", "landmark_checkpoint"].every(name => kit.has(name));
  const scene = new Scene();
  const hemi = new HemisphereLight(0xffffff, 0x445544, 1.1);
  const sun = new DirectionalLight(0xffe0b0, 2.2);
  sun.position.set(-300, 220, 160);
  scene.add(hemi, sun);
  scene.fog = new Fog(0xf2b27c, useKit ? 90 : 120, useKit ? 600 : 720);
  const ground = new Mesh(new PlaneGeometry(60000, 60000), new MeshLambertMaterial({ color: 0x6f7a55 }));
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(-5000, 0, -15000);
  scene.add(ground);
  const road = ribbon(route, 6, ROAD_HALF_WIDTH, 0.12, roadTexture(), 24);
  scene.add(road);
  const sides = ribbon(route, 12, ROAD_HALF_WIDTH + 1.6, 0.1, roadTexture(), 1e9);
  sides.material = new MeshLambertMaterial({ color: 0x8e8a7c });
  scene.add(sides);
  buildRoadKit(scene, route);
  const water = buildWater(scene, route);
  const procedural = useKit ? null : buildSurroundings(scene, route);
  const landmarks = useKit ? { gates: [], stop: (findRoad(route, "Woodlands border checkpoint (cars) - zone 4") ?? findRoad(route, "Woodlands border checkpoint") ?? route.length * 0.75) + 150 } : buildLandmarks(scene, route);
  const scenery = useKit ? buildScenery(scene, route, kit) : null;
  const models = useKit ? buildLandmarkModels(scene, route, kit, landmarks.stop) : null;
  if (models) landmarks.gates.push({ stop: landmarks.stop, barriers: models.barriers });
  const lightMaterials = new Set();
  for (const model of kit.values()) for (const part of model.parts) for (const material of [part.material].flat()) if (material.name === "light") lightMaterials.add(material);
  const surroundings = procedural ?? { lampMaterial: new MeshBasicMaterial(), heads: { visible: true } };

  const camera = new PerspectiveCamera(58, 1, 0.5, 2200);
  const renderer = new WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, matchMedia("(pointer: coarse)").matches ? 1.5 : 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  canvasHost.append(renderer.domElement);

  function setHour(hour) {
    const state = skyAt(hour);
    scene.background = state.sky;
    scene.fog.color.copy(state.sky);
    ground.material.color.copy(state.ground);
    sun.intensity = state.sun;
    hemi.intensity = 0.5 + state.sun * 0.35;
    surroundings.lampMaterial.color.setRGB(1, 0.89 * (0.55 + state.lamp * 0.45), 0.63 * (0.4 + state.lamp * 0.6));
    surroundings.heads.visible = state.lamp > 0.05;
    for (const material of lightMaterials) { material.emissive?.copy(material.color); material.emissiveIntensity = state.lamp * 1.6; }
  }

  return {
    scene, camera, renderer, landmarks, setHour, scenery, kitMode: useKit,
    resize(width, height) {
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    },
    dispose() {
      scene.traverse(node => {
        node.geometry?.dispose();
        for (const material of [node.material].flat().filter(Boolean)) { material.map?.dispose(); material.dispose(); }
      });
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
      water.clear();
    },
  };
}

export { ROAD_HALF_WIDTH, project };

export function buildCar(color = 0xd9453a) {
  const car = new Group();
  const body = new Mesh(new BoxGeometry(1.8, 0.7, 4.0), new MeshLambertMaterial({ color }));
  body.position.y = 0.65;
  const cabin = new Mesh(new BoxGeometry(1.5, 0.6, 2.0), new MeshLambertMaterial({ color: 0x2c3a45, transparent: true, opacity: 0.38 }));
  cabin.position.set(0, 1.2, -0.2);
  car.add(body, cabin);
  const wheelGeometry = new CylinderGeometry(0.36, 0.36, 0.3, 12);
  const wheelMaterial = new MeshLambertMaterial({ color: 0x15181b });
  for (const x of [-0.95, 0.95]) for (const z of [-1.3, 1.3]) {
    const wheel = new Mesh(wheelGeometry, wheelMaterial);
    wheel.rotation.z = Math.PI / 2;
    wheel.position.set(x, 0.36, z);
    car.add(wheel);
  }
  const lights = new Mesh(new BoxGeometry(1.5, 0.15, 0.1), new MeshBasicMaterial({ color: 0xfff1b8 }));
  lights.position.set(0, 0.7, 2.02);
  car.add(lights);
  const driver = new Mesh(new SphereGeometry(0.28, 10, 8), new MeshLambertMaterial({ color: 0xf0c9a0 }));
  driver.position.set(-0.35, 1.65, -0.3);
  driver.name = "driver-placeholder";
  car.add(driver);
  return car;
}
