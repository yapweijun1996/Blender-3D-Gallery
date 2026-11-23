import {
  AdditiveBlending, AmbientLight, BoxGeometry, CylinderGeometry, CanvasTexture, Color, DirectionalLight, DoubleSide, Fog, Group, HemisphereLight, InstancedMesh, Matrix4, Mesh, MeshBasicMaterial, MeshLambertMaterial, PerspectiveCamera, PlaneGeometry, Quaternion, RepeatWrapping, Scene, SRGBColorSpace, Vector3, WebGLRenderer,
} from "three";
import { localize, mountMarkup, t } from "../i18n/index.js";
import { disposeModels } from "../chibi-dressup/view.js";
import { createDriveAudio } from "../drive/audio.js";
import { dayAt } from "../drive/daylight.js";
import { cloneModel, instanceModel, loadKitFrom } from "../drive/kit.js";
import { createQualityGovernor } from "../drive/quality.js";
import { createWorldFortCanning } from "./tunnel-integration/session.js";
import { createPhysicsWorld } from "./physics/world.js";
import { createSmoke, damageEffects } from "./damage.js";
import { STAMP_ZONE, createStamp } from "./stamp.js";
import { grovePlacements, groveRings } from "./groves.js";
import { LANDMARKS, hiddenOutline } from "./landmarks.js";
import { ROAD_DISTANCES } from "./mission-distances.js";
import { paintMinimap } from "./minimap.js";
import { MISSIONS, arrived, cleanRecord, distanceTo, missionScore, nextMission, recordScore, relativeBearing, roadDistance } from "./missions.js";
import { busStopPlacements, lampPlacements, nearestRoad } from "./furniture.js";
import { addWorldPedestrians, pedestrianPaths } from "./pedestrians.js";
import { createSignalLights, signalApproaches } from "./signals.js";
import { goToPage } from "../drive/nav.js";
import { VEHICLE_TYPES, buildTrafficGraph, createRandom, createTraffic } from "./traffic.js";
import { TILE_SIZE, buildTile, buildingMesh } from "./tile-mesh.js";
import "../drive/style.css";
import "./style.css";

// Open-world study: the real OpenStreetMap road network and buildings around Marina Bay, streamed in 250 m tiles,
// with a car driven by the Rapier vehicle physics (crashes, flips). Built from models/world/tiles (scripts/world/build-tiles.mjs).
const tileUrls = import.meta.glob("../../models/world/tiles/*.json", { eager: true, query: "?url", import: "default" });
const kitUrls = import.meta.glob([
  "../../models/drive/kit/car_saga.glb", "../../models/drive/kit/car_hatchback_hd.glb", "../../models/drive/kit/motorbike_hd.glb", "../../models/sg-{taxi,bus-double,lorry,police,ambulance,school-bus}-hd/*.glb", "../../models/sg-rain-tree/*.glb", "../../models/sg-angsana/*.glb", "../../models/sg-coconut-palm/*.glb",
  "../../models/sg-road-light/*.glb", "../../models/sg-bus-shelter-sbs/*.glb", "../../models/sg-bus-stop-flag/*.glb", "../../models/sg-station-sign/*.glb", "../../models/sg-bayfront-entrance/*.glb", "../../models/sg-supertree-{tall,mid,short}/*.glb",
], { eager: true, query: "?url", import: "default" });
const landmarkUrls = import.meta.glob("../../models/sg-{marina-bay-sands-towers,marina-bay-sands-podium,esplanade-domes,esplanade-base,merlion,merlion-park,artscience-museum,helix-bridge,flower-dome,cloud-forest,the-float,checkpoint-canopy,checkpoint-lane,checkpoint-building}/*.glb", { eager: true, query: "?url", import: "default" });
const KIT = { motorbike_hd: "drive/kit/motorbike_hd", car_saga: "drive/kit/car_saga", car_hatchback_hd: "drive/kit/car_hatchback_hd", "sg-taxi-hd": "sg-taxi-hd/sg-taxi-hd", "sg-bus-double-hd": "sg-bus-double-hd/sg-bus-double-hd", "sg-lorry-hd": "sg-lorry-hd/sg-lorry-hd", "sg-police-hd": "sg-police-hd/sg-police-hd", "sg-ambulance-hd": "sg-ambulance-hd/sg-ambulance-hd", "sg-school-bus-hd": "sg-school-bus-hd/sg-school-bus-hd", rain_tree: "sg-rain-tree/sg-rain-tree", angsana: "sg-angsana/sg-angsana", coconut_palm: "sg-coconut-palm/sg-coconut-palm", road_light: "sg-road-light/sg-road-light", bus_shelter: "sg-bus-shelter-sbs/sg-bus-shelter-sbs", bus_flag: "sg-bus-stop-flag/sg-bus-stop-flag", station_sign: "sg-station-sign/sg-station-sign", bayfront_entrance: "sg-bayfront-entrance/sg-bayfront-entrance", "sg-supertree-tall": "sg-supertree-tall/sg-supertree-tall", "sg-supertree-mid": "sg-supertree-mid/sg-supertree-mid", "sg-supertree-short": "sg-supertree-short/sg-supertree-short" };
const TREES = ["rain_tree", "angsana", "coconut_palm"];
// The cars the player can pick: the model, the physics type and how far the chase camera stays back.
const PLAYER_VEHICLES = [
  { id: "saga", model: "car_saga", type: "sedan", back: 8.5 }, { id: "hatchback", model: "car_hatchback_hd", type: "hatchback", back: 8 },
  { id: "taxi", model: "sg-taxi-hd", type: "sedan", back: 8.5 }, { id: "police", model: "sg-police-hd", type: "sedan", back: 8.5 },
  { id: "ambulance", model: "sg-ambulance-hd", type: "van", back: 9.5 }, { id: "school-bus", model: "sg-school-bus-hd", type: "bus", back: 13 },
  { id: "double-bus", model: "sg-bus-double-hd", type: "bus", back: 15 }, { id: "lorry", model: "sg-lorry-hd", type: "lorry", back: 12 },
  { id: "motorbike", model: "motorbike_hd", type: "motorbike", back: 6 },
];
const CHECKPOINT_BONUS = 300;
const PLAYER_TOP_SPEED = 28; // m/s, 100 km/h: the fastest limit on the mapped roads is 90 km/h
const SOLID_RADIUS = 1; // in tiles around the car; phones load a smaller ring of tiles
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const tileKey = (x, z) => `${x}_${z}`;

/**
 * One window bay and storey as a repeating texture: pale wall with a glazed window and a floor band. The bottom-left corner
 * stays plain wall (roofs sample it). The wall colour of each building multiplies it through the vertex colours.
 */
function facadeTexture() {
  const size = 128, canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const context = canvas.getContext("2d");
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, size, size);
  const glass = context.createLinearGradient(0, 30, 0, 100);
  glass.addColorStop(0, "#5d7585");
  glass.addColorStop(1, "#8fa8b6");
  context.fillStyle = glass;
  context.fillRect(30, 30, 82, 66);
  context.fillStyle = "#c9ced1";
  context.fillRect(30, 62, 82, 3); // transom
  context.fillStyle = "#dfe2e4";
  context.fillRect(0, size - 6, size, 6); // floor band
  const texture = new CanvasTexture(canvas);
  texture.wrapS = texture.wrapT = RepeatWrapping;
  texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;
  // The same windows on black: lit at night through the material's emissive map.
  const glowCanvas = document.createElement("canvas");
  glowCanvas.width = glowCanvas.height = size;
  const glowContext = glowCanvas.getContext("2d");
  glowContext.fillStyle = "#000000";
  glowContext.fillRect(0, 0, size, size);
  glowContext.fillStyle = "#ffffff";
  glowContext.fillRect(30, 30, 82, 28);
  glowContext.fillRect(30, 65, 82, 31);
  const glow = new CanvasTexture(glowCanvas);
  glow.wrapS = glow.wrapT = RepeatWrapping;
  glow.colorSpace = SRGBColorSpace;
  return { texture, glow };
}

/** Glass curtain wall for towers: a pane per bay and storey with thin mullions, and the same panes lit at night. */
function towerTexture() {
  const size = 128, make = fill => {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const context = canvas.getContext("2d");
    fill(context);
    return canvas;
  };
  const texture = new CanvasTexture(make(context => {
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, size, size);
    const glass = context.createLinearGradient(0, 0, 0, size);
    glass.addColorStop(0, "#9db4c2");
    glass.addColorStop(1, "#6f8a9b");
    context.fillStyle = glass;
    context.fillRect(8, 14, size - 16, size - 30);
    context.fillStyle = "#e6eaec";
    context.fillRect(0, size - 8, size, 8); // spandrel
  }));
  const glow = new CanvasTexture(make(context => {
    context.fillStyle = "#000000";
    context.fillRect(0, 0, size, size);
    context.fillStyle = "#ffffff";
    context.fillRect(8, 14, size - 16, size - 30);
  }));
  for (const map of [texture, glow]) { map.wrapS = map.wrapT = RepeatWrapping; map.colorSpace = SRGBColorSpace; map.anisotropy = 4; }
  return { texture, glow };
}

async function fetchTile(key, signal) {
  const url = tileUrls[`../../models/world/tiles/${key}.json`];
  if (!url) return null;
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`tile ${key}: HTTP ${response.status}`);
  return response.json();
}

export async function mountWorld(root, thumbnail, signal, { tunnel = false } = {}) {
  if (tunnel) {
    const { mountTunnelPrototype } = await import("./tunnel-prototype/page.js");
    signal.throwIfAborted();
    return mountTunnelPrototype(root, thumbnail, signal);
  }
  const LOAD_RADIUS = matchMedia("(pointer: coarse)").matches ? 1 : 2;
  mountMarkup(root, `<section class="drive">
    <header class="drive-heading">
      <h1 data-i18n="demo.sg-world.title"></h1>
      <p data-i18n="demo.sg-world.description"></p>
    </header>
    <div class="drive-stage world-stage" data-state="loading" data-mode="manual" aria-busy="true">
      <img class="drive-poster" alt="">
      <p class="drive-loading" role="status" data-i18n="world.loading"></p>
      <div class="drive-hud" hidden>
        <div class="drive-readout"><strong class="drive-speed">0</strong><span data-i18n="drive.kmh"></span></div>
        <p class="drive-road" aria-live="polite"></p>
        <p class="drive-trip"></p>
        <p class="drive-event" role="status" aria-live="polite"></p>
        <div class="world-mission" aria-live="off"><span class="world-arrow" aria-hidden="true">➤</span><span class="world-mission-text"></span></div>
        <canvas class="drive-minimap" width="160" height="200" aria-hidden="true"></canvas>
        <div class="drive-passport world-passport" role="dialog" hidden>
          <h2 data-i18n="drive.passport.title"></h2>
          <p class="drive-passport-text"></p>
          <div class="drive-stamp-bar" hidden><i class="drive-stamp-zone"></i><b class="drive-stamp-marker"></b></div>
          <button type="button" class="drive-passport-action"></button>
        </div>
        <button type="button" class="world-enter" hidden></button>
        <div class="drive-pad">
          <div class="drive-steer"><button type="button" data-key="left">◀</button><button type="button" data-key="right">▶</button></div>
          <div class="drive-pedals"><button type="button" data-key="brake">■</button><button type="button" data-key="gas">▲</button></div>
        </div>
      </div>
    </div>
    <div class="drive-controls" role="group">
      <button type="button" class="drive-pause" data-i18n="common.pause"></button>
      <button type="button" class="drive-horn" data-i18n="drive.horn"></button>
      <button type="button" class="drive-reset" data-i18n="world.reset"></button>
      <button type="button" class="world-vehicle"></button>
      <button type="button" class="world-time"></button>
      <button type="button" class="world-next" data-i18n="world.mission.next"></button>
      <button type="button" class="drive-sound" aria-pressed="true" data-i18n="drive.sound"></button>
    </div>
    <p class="drive-hint" data-i18n="world.hint"></p>
    <p class="drive-credit" data-i18n="world.credit"></p>
    <p class="drive-credit"><a href="?page=sg-world&amp;tunnel=fort-canning" data-i18n="world.tunnel.link"></a></p>
  </section>`);
  const stage = root.querySelector(".drive-stage");
  const enterButton = stage.querySelector(".world-enter");
  for (const [name, value] of Object.entries({
    "--drive-sky": "#9fcdea", "--drive-ink": "#ffffff", "--drive-gold": "#ffd36a", "--drive-on-gold": "#1c1c1c",
    "--drive-line": "rgba(255,255,255,.3)", "--drive-shadow": "rgba(0,0,0,.7)", "--drive-panel-soft": "rgba(8,14,28,.55)",
    "--drive-panel": "rgba(10,18,36,.92)", "--drive-good": "rgba(70,170,100,.85)",
  })) root.querySelector(".drive").style.setProperty(name, value);
  root.querySelector(".drive-poster").src = thumbnail;
  const hud = stage.querySelector(".drive-hud"), speedLabel = stage.querySelector(".drive-speed");
  const roadLabel = stage.querySelector(".drive-road"), tripLabel = stage.querySelector(".drive-trip"), eventLine = stage.querySelector(".drive-event");
  for (const button of root.querySelectorAll("[data-key]")) localize(button, `drive.key.${button.dataset.key}`, undefined, "aria-label");
  localize(root.querySelector(".drive-controls"), "drive.controls", undefined, "aria-label");

  const kitScenes = new Set();
  const kit = await loadKitFrom(Object.entries(KIT).map(([name, file]) => [name, kitUrls[`../../models/${file}.glb`]]), signal, kitScenes)
    .catch(error => { if (signal.aborted) throw error; console.error("World: model kit failed to load", error); return new Map(); });
  const landmarkKit = await loadKitFrom(LANDMARKS.flatMap(landmark => landmark.models).map(name => [name, landmarkUrls[`../../models/${name}/${name}.glb`]]), signal, kitScenes)
    .catch(error => { if (signal.aborted) throw error; console.error("World: landmarks failed to load", error); return new Map(); });
  const physics = await createPhysicsWorld();
  signal.throwIfAborted();

  const scene = new Scene();
  scene.background = new Color(0x9fcdea);
  scene.fog = new Fog(0x9fcdea, LOAD_RADIUS === 1 ? 160 : 260, LOAD_RADIUS === 1 ? 420 : 700);
  const hemisphere = new HemisphereLight(0xdff0ff, 0x7a8a68, 1.5);
  const ambient = new AmbientLight(0xffffff, 0.35);
  scene.add(hemisphere, ambient);
  const sun = new DirectionalLight(0xfff1d6, 2.2);
  sun.position.set(-120, 220, 90);
  scene.add(sun);
  const camera = new PerspectiveCamera(60, 1, 0.8, 1200);
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  const touchDevice = matchMedia("(pointer: coarse)").matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, touchDevice ? 1.5 : 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  stage.append(renderer.domElement);

  const groundMaterial = new MeshLambertMaterial({ vertexColors: true, side: DoubleSide });
  const facade = facadeTexture(), glass = towerTexture();
  const towerMaterial = new MeshLambertMaterial({ vertexColors: true, side: DoubleSide, map: glass.texture, emissiveMap: glass.glow, emissive: new Color(0xa9c0ee), emissiveIntensity: 0 });
  const buildingMaterial = new MeshLambertMaterial({ vertexColors: true, side: DoubleSide, map: facade.texture, emissiveMap: facade.glow, emissive: new Color(0xffd98a), emissiveIntensity: 0 });
  const flatGround = new Mesh(new PlaneGeometry(6000, 6000).rotateX(-Math.PI / 2), new MeshLambertMaterial({ color: 0x8aa06f }));
  flatGround.position.y = -0.3;
  scene.add(flatGround);

  const booms = [];
  for (const landmark of LANDMARKS) {
    for (const name of landmark.models) {
      const model = landmarkKit.get(name);
      if (!model) continue;
      const copy = cloneModel(model);
      copy.position.set(landmark.pose.x, 0, landmark.pose.z);
      copy.rotation.y = landmark.pose.yaw;
      scene.add(copy);
      // Checkpoint lanes: keep the boom arms to open when the passport is stamped.
      if (landmark.boom) copy.traverse(node => { if (node.name === "boom_arm") booms.push(node); });
    }
  }

  // Streaming: tiles near the car are fetched and built one per frame; colliders only exist for the nearest ring.
  const startTile = [0, 0];
  let carTile = [...startTile];
  let graphDirty = true;
  const tiles = new Map(); // key -> { x, z, group, solids, colliders, instances }
  const pending = new Set();
  const failed = new Set();
  function addInstances(entry, built) {
    const lists = new Map();
    built.trees.forEach(([x, z], index) => {
      const name = TREES[(Math.abs(Math.round(x * 7 + z * 13)) + index) % TREES.length];
      if (!kit.has(name)) return;
      (lists.get(name) ?? lists.set(name, []).get(name)).push({ x, z, yaw: ((x * 12.9898 + z * 78.233) % 6.283), scale: 1.2 });
    });
    for (const [name, placements] of lists) {
      if (!placements.length) continue;
      const set = instanceModel(kit.get(name), placements);
      for (const mesh of set.meshes) { entry.group.add(mesh); entry.instances.push(mesh); }
    }
  }
  function makeEntry(data, options) {
    const { x, z } = data;
    const built = buildTile(data, { hide: hiddenOutline, ...options });
    const group = new Group();
    const entry = { x, z, data, bridgeSolids: built.bridgeSolids, walkwaySolids: built.walkwaySolids, busStops: built.busStops, entrances: built.entrances, group, solids: built.solids, colliders: null, instances: [], geometries: [] };
    if (built.ground) { const mesh = new Mesh(built.ground, groundMaterial); mesh.matrixAutoUpdate = false; group.add(mesh); entry.geometries.push(built.ground); }
    if (built.towers) { const mesh = new Mesh(built.towers, towerMaterial); mesh.matrixAutoUpdate = false; group.add(mesh); entry.geometries.push(built.towers); }
    if (built.buildings) { const mesh = new Mesh(built.buildings, buildingMaterial); mesh.matrixAutoUpdate = false; group.add(mesh); entry.geometries.push(built.buildings); }
    addInstances(entry, built);
    return entry;
  }
  function buildEntry(x, z, data) {
    const entry = makeEntry(data);
    scene.add(entry.group);
    tiles.set(tileKey(x, z), entry);
    graphDirty = true;
    return entry;
  }
  function setColliders(entry, wanted) {
    if (wanted && !entry.colliders) {
      entry.colliders = [];
      try {
        for (const solid of entry.solids) {
          const { vertices, indices } = solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base);
          entry.colliders.push(physics.addStaticTrimesh({ vertices, indices }));
        }
        for (const panel of entry.walkwaySolids) {
          entry.colliders.push(physics.addStaticConvexHull({ vertices: panel.position, friction: 1 }));
        }
        for (const deck of entry.bridgeSolids) {
          entry.colliders.push(physics.addStaticTrimesh({ vertices: deck.vertices, indices: deck.indices, friction: 1 }));
        }
      } catch (error) {
        setColliders(entry, false);
        throw error;
      }
    } else if (!wanted && entry.colliders) {
      for (const collider of entry.colliders) physics.removeStatic(collider);
      entry.colliders = null;
    }
  }
  function disposeEntry(entry) {
    setColliders(entry, false);
    scene.remove(entry.group);
    for (const geometry of entry.geometries) geometry.dispose();
    for (const mesh of entry.instances) mesh.dispose?.();
    graphDirty = true;
  }
  function unload(key) {
    const entry = tiles.get(key);
    if (entry) disposeEntry(entry);
    tiles.delete(key);
  }
  const { activation, beforePhysics } = createWorldFortCanning({
    physics, signal, scene, flatGround, tiles, fetchTile, makeEntry, setColliders, disposeEntry,
  });
  let loadChain = Promise.resolve();
  const inLoadRadius = (x, z) => Math.max(Math.abs(x - carTile[0]), Math.abs(z - carTile[1])) <= LOAD_RADIUS;
  function request(x, z) {
    const key = tileKey(x, z);
    if (tiles.has(key) || pending.has(key) || failed.has(key) || !tileUrls[`../../models/world/tiles/${key}.json`]) return;
    pending.add(key);
    // A tile stays "pending" from the request until it is built or dropped, so it is never fetched twice while it waits in `ready`.
    loadChain = loadChain.then(() => {
      // Recheck at dispatch because earlier requests can outlast the player's visit.
      if (signal.aborted || !inLoadRadius(x, z)) return null;
      return fetchTile(key, signal);
    }).then(data => { if (data && !signal.aborted) ready.push({ x, z, data }); else pending.delete(key); })
      .catch(error => { pending.delete(key); if (!signal.aborted) { failed.add(key); console.error("World: tile failed", key, error); } });
  }
  const ready = [];
  function updateTiles(cx, cz) {
    for (let dz = -LOAD_RADIUS; dz <= LOAD_RADIUS; dz++) for (let dx = -LOAD_RADIUS; dx <= LOAD_RADIUS; dx++) request(cx + dx, cz + dz);
    // Build one waiting tile per frame, skipping tiles the car has already left behind.
    let next = ready.shift();
    while (next && !inLoadRadius(next.x, next.z)) { pending.delete(tileKey(next.x, next.z)); next = ready.shift(); }
    if (next) {
      pending.delete(tileKey(next.x, next.z));
      if (!tiles.has(tileKey(next.x, next.z))) buildEntry(next.x, next.z, next.data);
    }
    for (const [key, entry] of tiles) {
      const distance = Math.max(Math.abs(entry.x - cx), Math.abs(entry.z - cz));
      if (activation.available?.tiles.has(key)) {
        const visible = distance <= LOAD_RADIUS + 1;
        if (entry.group.visible !== visible) {
          entry.group.visible = visible;
          graphDirty = true;
        }
        setColliders(entry, distance <= SOLID_RADIUS);
        continue;
      }
      if (distance > LOAD_RADIUS + 1) unload(key);
      else setColliders(entry, distance <= SOLID_RADIUS);
    }
  }

  // Load the tiles around the start before the first frame, so the car does not spawn in the void.
  const startData = new Map();
  for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
    const x = startTile[0] + dx, z = startTile[1] + dz;
    const data = await fetchTile(tileKey(x, z), signal).catch(() => null);
    if (!data) continue;
    startData.set(tileKey(x, z), data);
    buildEntry(x, z, data);
  }
  signal.throwIfAborted();

  // Supertree Grove: the trees stand inside the mapped garden outline (approximate positions, see groves.js).
  const grove = grovePlacements(groveRings([...startData.values()]));
  for (const name of new Set(grove.map(tree => tree.model))) {
    if (!kit.has(name)) continue;
    for (const mesh of instanceModel(kit.get(name), grove.filter(tree => tree.model === name).map(tree => ({ x: tree.x, z: tree.z, yaw: tree.yaw, scale: 1 }))).meshes) scene.add(mesh);
  }

  // The player starts on Bayfront Avenue, in the left lane (Singapore drives on the left), facing along the road.
  let start = { x: 0, z: 0, heading: 0 };
  let bestDistance = Infinity;
  for (const data of startData.values()) {
    for (const road of data.roads) {
      if (!/Bayfront Avenue/.test(road.name ?? "") || road.geometry.length < 2) continue;
      const [a, b] = road.geometry.slice(0, 2).map(([x, z]) => [x + data.x * TILE_SIZE, z + data.z * TILE_SIZE]);
      const mx = (a[0] + b[0]) / 2, mz = (a[1] + b[1]) / 2, distance = Math.hypot(mx, mz);
      if (distance >= bestDistance) continue;
      bestDistance = distance;
      const heading = Math.atan2(b[0] - a[0], b[1] - a[1]);
      // The left of travel is (cos h, -sin h); on a two-way road the car sits 1.7 m left of the centreline.
      const offset = road.oneway ? 0 : 1.7;
      start = { x: mx + Math.cos(heading) * offset, z: mz - Math.sin(heading) * offset, heading };
    }
  }

  // The player's vehicle can be swapped (the Vehicle button): the body is rebuilt where the old one stood, the model replaced.
  let vehicle = null, restHeight = 0, playerChoice = 0, car = null;
  const carHolder = new Group();
  scene.add(carHolder);
  let playerHalfLength;
  function chooseVehicle(index, at = null) {
    const choice = PLAYER_VEHICLES[((index % PLAYER_VEHICLES.length) + PLAYER_VEHICLES.length) % PLAYER_VEHICLES.length];
    const place = at ?? { x: start.x, z: start.z, heading: start.heading };
    if (vehicle) physics.removeVehicle(vehicle);
    const supportY = place.supportY ?? 0;
    vehicle = physics.addVehicle({ type: choice.type, topSpeed: Math.min(PLAYER_TOP_SPEED, 47), position: { x: place.x, y: supportY + 1.4, z: place.z }, heading: place.heading });
    playerHalfLength = vehicle.collider.halfExtents().z;
    for (let i = 0; i < 90; i++) physics.step(1 / 60);
    const settled = vehicle.getState().position;
    restHeight = settled.y - (physics.supportHeight(settled) ?? supportY);
    if (car) carHolder.remove(car);
    car = kit.has(choice.model) ? cloneModel(kit.get(choice.model)) : new Group();
    carHolder.add(car);
    // The wheels of the model (named wheel_FL, wheel_RR and so on) turn with the speed, the front ones steer.
    wheelNodes = [];
    car.traverse(node => {
      if (!/^wheel_/.test(node.name)) return;
      node.rotation.order = "YXZ";
      wheelNodes.push({ node, radius: Math.max(0.2, node.position.y || 0.3), front: /^wheel_F/.test(node.name), angle: 0 });
    });
    playerChoice = PLAYER_VEHICLES.indexOf(choice);
    cameraBack = choice.back;
    vehicleButton.textContent = t("world.vehicle", { name: t(`world.vehicle.${choice.id}`) });
    try { localStorage.setItem("sg-world-vehicle", choice.id); } catch { /* Not saved. */ }
  }
  let cameraBack = 8.5, wheelNodes = [];
  const vehicleButton = root.querySelector(".world-vehicle");
  let savedVehicle = "saga";
  try { savedVehicle = localStorage.getItem("sg-world-vehicle") ?? "saga"; } catch { /* Use the default. */ }
  chooseVehicle(Math.max(0, PLAYER_VEHICLES.findIndex(item => item.id === savedVehicle)));
  vehicleButton.addEventListener("click", () => {
    const state = vehicle.getState();
    chooseVehicle(playerChoice + 1, { x: state.position.x, z: state.position.z, heading: state.heading, supportY: physics.supportHeight(state.position) ?? state.position.y - restHeight });
  });

  // Traffic: simulated on the road graph of the loaded tiles, drawn with one instanced set per vehicle model and
  // solid (a kinematic box) for the physics when it is near the player's car.
  const traffic = createTraffic({ graph: buildTrafficGraph([...tiles.values()].map(entry => entry.data)), random: createRandom(2025), maxVehicles: touchDevice ? 18 : 34 });
  const trafficSets = new Map();
  for (const type of VEHICLE_TYPES) {
    if (trafficSets.has(type.model) || !kit.has(type.model)) continue;
    // Room for every vehicle of the model: the instance buffers are sized by the first list given.
    const set = instanceModel(kit.get(type.model), Array.from({ length: traffic.maxVehicles }, () => ({ x: 0, z: 0 })), { dynamic: true });
    set.write([]);
    for (const mesh of set.meshes) scene.add(mesh);
    trafficSets.set(type.model, set);
  }
  // Street furniture follows the road graph: lamps along the main roads and shelters at the mapped bus stops.
  let furnitureMeshes = [], stationEntrances = [];
  const pillarGeometry = new BoxGeometry(0.9, 3.4, 0.9), pillarMaterial = new MeshLambertMaterial({ color: 0xc9252c });
  function placeFurniture(graph, localEntries) {
    for (const mesh of furnitureMeshes) { scene.remove(mesh); mesh.dispose?.(); }
    furnitureMeshes = [];
    const stops = localEntries.flatMap(entry => entry.busStops);
    const { shelters, flags } = busStopPlacements(graph, stops);
    // MRT entrances: a red pillar with the station sign on top, facing the nearest road.
    const entrances = localEntries.flatMap(entry => entry.entrances).map(entrance => {
      const road = nearestRoad(graph, entrance.x, entrance.z);
      return { ...entrance, yaw: road ? Math.atan2(road.x - entrance.x, road.z - entrance.z) : 0 };
    });
    stationEntrances = entrances;
    // Bayfront Exit B has its own modelled canopy; the other entrances are a red pillar with the station sign on top.
    const modelled = entrances.filter(entrance => kit.has("bayfront_entrance") && /Bayfront.*Exit B/i.test(entrance.name));
    const plain = entrances.filter(entrance => !modelled.includes(entrance));
    if (plain.length) {
      const pillars = new InstancedMesh(pillarGeometry, pillarMaterial, plain.length);
      plain.forEach((entrance, index) => pillars.setMatrixAt(index, new Matrix4().makeTranslation(entrance.x, 1.7, entrance.z)));
      pillars.frustumCulled = false;
      scene.add(pillars);
      furnitureMeshes.push(pillars);
      if (kit.has("station_sign")) for (const mesh of instanceModel(kit.get("station_sign"), plain.map(entrance => ({ x: entrance.x, y: 3.4, z: entrance.z, yaw: entrance.yaw, scale: 1.3 }))).meshes) { scene.add(mesh); furnitureMeshes.push(mesh); }
    }
    if (modelled.length) for (const mesh of instanceModel(kit.get("bayfront_entrance"), modelled.map(entrance => ({ x: entrance.x, y: 0, z: entrance.z, yaw: entrance.yaw, scale: 1 }))).meshes) { scene.add(mesh); furnitureMeshes.push(mesh); }
    for (const [name, placements] of [["road_light", lampPlacements(graph)], ["bus_shelter", shelters], ["bus_flag", flags]]) {
      if (!kit.has(name) || !placements.length) continue;
      for (const mesh of instanceModel(kit.get(name), placements.map(item => ({ ...item, scale: 1 }))).meshes) { scene.add(mesh); furnitureMeshes.push(mesh); }
    }
  }
  let pedestrians = null;
  addWorldPedestrians({ scene, signal, count: touchDevice ? { female: 2, male: 1 } : { female: 3, male: 3 } })
    .then(result => { if (signal.aborted) result.dispose(); else { pedestrians = result; graphDirty = true; } })
    .catch(error => { if (!signal.aborted) console.error("World: pedestrians failed to load", error); });
  const signalLights = createSignalLights(scene);
  let signalGraph = null, signalList = [];
  const solidVehicles = new Map(), solidWalkers = new Map();
  let headlightPoses = [];
  function updateTraffic(dt, state) {
    if (graphDirty) {
      const localEntries = [...tiles.values()].filter(entry => entry.group.visible);
      const localTiles = localEntries.map(entry => entry.data);
      const bundle = activation.available;
      const nearTunnel = bundle && localEntries.some(entry => bundle.tiles.has(tileKey(entry.x, entry.z)));
      signalGraph = buildTrafficGraph(localTiles, nearTunnel ? bundle.trafficOptions : undefined);
      traffic.setGraph(signalGraph);
      signalList = signalApproaches(signalGraph);
      placeFurniture(signalGraph, localEntries);
      pedestrians?.setPaths(pedestrianPaths(localTiles));
      signalLights.setApproaches(signalList, state.position);
      graphDirty = false;
    }
    signalLights.update(traffic.signalState);
    pedestrians?.update(dt, state.position);
    const walkers = pedestrians ? pedestrians.people.filter(person => person.root.visible).map(person => ({ id: person, x: person.root.position.x, y: person.root.position.y, z: person.root.position.z })) : [];
    const player = { x: state.position.x, y: state.position.y - restHeight, z: state.position.z, halfLength: playerHalfLength };
    traffic.update(dt, state.position, [player, ...walkers]);
    // Pedestrians near the player's car are solid too (a small box), so the car cannot drive through them.
    const aliveWalkers = new Set();
    for (const walker of walkers) {
      const near = Math.hypot(walker.x - state.position.x, walker.z - state.position.z) < 40;
      let solid = solidWalkers.get(walker.id);
      if (near && !solid) { solid = physics.addKinematicBox({ halfExtents: { x: 0.3, y: 0.9, z: 0.3 }, position: { x: walker.x, y: walker.y + 0.9, z: walker.z } }); solidWalkers.set(walker.id, solid); }
      else if (!near && solid) { solid.remove(); solidWalkers.delete(walker.id); solid = null; }
      if (solid) { aliveWalkers.add(walker.id); solid.setPose(walker.x, walker.y + 0.9, walker.z, 0); }
    }
    for (const [id, solid] of solidWalkers) if (!aliveWalkers.has(id)) { solid.remove(); solidWalkers.delete(id); }
    const lists = new Map([...trafficSets.keys()].map(name => [name, []]));
    const alive = new Set();
    for (const vehicle of traffic.vehicles) {
      const list = lists.get(vehicle.type.model);
      if (!list) continue;
      const pose = traffic.pose(vehicle);
      if (!pose) continue;
      list.push({ x: pose.x, y: pose.y, z: pose.z, yaw: pose.heading });
      alive.add(vehicle.id);
      const near = Math.hypot(pose.x - state.position.x, pose.z - state.position.z) < 55;
      let solid = solidVehicles.get(vehicle.id);
      if (near && !solid) {
        solid = physics.addKinematicBox({ halfExtents: { x: vehicle.type.width / 2, y: 0.8, z: vehicle.type.length / 2 }, position: { x: pose.x, y: pose.y + 0.8, z: pose.z }, yaw: pose.heading });
        solidVehicles.set(vehicle.id, solid);
      } else if (!near && solid) { solid.remove(); solidVehicles.delete(vehicle.id); solid = null; }
      solid?.setPose(pose.x, pose.y + 0.8, pose.z, pose.heading);
    }
    for (const [id, solid] of solidVehicles) if (!alive.has(id)) { solid.remove(); solidVehicles.delete(id); }
    for (const [name, set] of trafficSets) set.write(lists.get(name));
    headlightPoses = [{ x: state.position.x, y: state.position.y - restHeight, z: state.position.z, heading: state.heading }, ...traffic.vehicles.map(vehicle => traffic.pose(vehicle)).filter(Boolean).map(pose => ({ x: pose.x, y: pose.y, z: pose.z, heading: pose.heading }))];
  }

  const smoke = createSmoke(scene);
  let wasStalled = false;
  const keys = new Set(), pad = { left: false, right: false, brake: false, gas: false };
  const keyMap = { arrowup: "gas", w: "gas", arrowdown: "brake", s: "brake", arrowleft: "left", a: "left", arrowright: "right", d: "right", " ": "hand" };
  const held = name => keys.has(name) || pad[name];
  addEventListener("keydown", event => {
    if (event.target.closest?.("input, textarea, select")) return;
    const name = keyMap[event.key.toLowerCase()];
    if (name) { keys.add(name); event.preventDefault(); audio.start(); }
    if (event.key === "r" || event.key === "R") resetCar();
    if (event.key === "h" || event.key === "H") horn();
  }, { signal });
  addEventListener("keyup", event => { const name = keyMap[event.key.toLowerCase()]; if (name) keys.delete(name); }, { signal });
  addEventListener("blur", () => keys.clear(), { signal });
  for (const button of stage.querySelectorAll("[data-key]")) {
    const name = button.dataset.key;
    button.addEventListener("pointerdown", event => { event.preventDefault(); pad[name === "gas" ? "gas" : name] = true; audio.start(); });
    for (const type of ["pointerup", "pointerleave", "pointercancel"]) button.addEventListener(type, () => { pad[name === "gas" ? "gas" : name] = false; });
  }

  const audio = createDriveAudio();
  const horn = () => { audio.start(); audio.horn(); };
  root.querySelector(".drive-horn").addEventListener("click", horn);
  const soundButton = root.querySelector(".drive-sound");
  let soundOn = true;
  soundButton.addEventListener("click", () => { soundOn = !soundOn; audio.enabled = soundOn; audio.start(); soundButton.setAttribute("aria-pressed", String(soundOn)); });
  let paused = false;
  const pauseButton = root.querySelector(".drive-pause");
  pauseButton.addEventListener("click", () => { paused = !paused; localize(pauseButton, paused ? "common.play" : "common.pause"); });
  let eventTimer = 0, lastCrash = 0, lastFlip = false;
  const notify = (key, params) => { eventLine.textContent = t(key, params); eventTimer = 2.6; };
  function resetCar() {
    // Right the car where it stands (lifted a little); repairs it as well.
    vehicle.resetUpright({ repair: true });
    notify("world.righted");
  }
  root.querySelector(".drive-reset").addEventListener("click", resetCar);

  // At an MRT entrance the car stops being the point: a button (or E) goes down to the station platform page.
  let nearEntrance = null;
  const stationName = entrance => (entrance.name || "MRT").replace(/\s*\(.*$/, "").replace(/\s+Exit\s+\w+$/i, "");
  function updateEntrance(position) {
    let best = null, bestDistance = 30;
    for (const entrance of stationEntrances) {
      const distance = Math.hypot(entrance.x - position.x, entrance.z - position.z);
      if (distance < bestDistance) { best = entrance; bestDistance = distance; }
    }
    if (best === nearEntrance) return;
    nearEntrance = best;
    enterButton.hidden = !best;
    if (best) localize(enterButton, "world.enterMrt", { station: stationName(best) });
  }
  enterButton.addEventListener("click", () => { if (nearEntrance) goToPage("sg-mrt"); });
  addEventListener("keydown", event => { if ((event.key === "e" || event.key === "E") && nearEntrance) goToPage("sg-mrt"); }, { signal });

  function controlsNow() {
    const state = vehicle.getState();
    const forward = state.forwardSpeed;
    const wantsBrake = held("brake");
    const stalled = damageEffects(state.damage).stalled;
    return {
      throttle: held("gas") && !stalled ? 1 : 0,
      brake: wantsBrake && forward > 1 ? 1 : 0,
      reverse: wantsBrake && forward <= 1 ? 1 : 0,
      steer: (held("left") ? 1 : 0) - (held("right") ? 1 : 0),
      handbrake: keys.has("hand") ? 1 : 0,
    };
  }

  const camTarget = new Vector3(), camPosition = new Vector3(), quaternion = new Quaternion();
  let camHeading = start.heading, camReady = false;
  function placeCar(dt = 0) {
    const state = vehicle.getState();
    const steering = state.wheels[0]?.steering ?? 0;
    for (const wheel of wheelNodes) {
      wheel.angle += state.forwardSpeed * dt / wheel.radius;
      wheel.node.rotation.x = -wheel.angle;
      wheel.node.rotation.y = wheel.front ? steering : 0;
    }
    carHolder.position.set(state.position.x, state.position.y - restHeight, state.position.z);
    quaternion.set(state.quaternion.x, state.quaternion.y, state.quaternion.z, state.quaternion.w);
    carHolder.quaternion.copy(quaternion);
    return state;
  }
  function placeCamera(state, dt) {
    const target = Math.abs(state.forwardSpeed) > 2 ? state.heading + (state.forwardSpeed < 0 ? Math.PI : 0) : camHeading;
    let delta = target - camHeading;
    delta = Math.atan2(Math.sin(delta), Math.cos(delta));
    camHeading += delta * (camReady ? Math.min(1, dt * 2.5) : 1);
    camReady = true;
    const below = activation.available && state.position.y < -0.35;
    const back = below ? 5.3 : cameraBack + clamp(state.speed * 0.12, 0, 4), up = below ? 1.8 : 3.4 + clamp(state.speed * 0.04, 0, 1.4);
    camPosition.set(state.position.x - Math.sin(camHeading) * back, state.position.y + up, state.position.z - Math.cos(camHeading) * back);
    camTarget.set(state.position.x + Math.sin(camHeading) * 6, state.position.y + 1.2, state.position.z + Math.cos(camHeading) * 6);
    const cameraTile = tileKey(Math.floor(camPosition.x / TILE_SIZE), Math.floor(camPosition.z / TILE_SIZE));
    if (tiles.get(cameraTile)?.data.roadSurfaces) {
      const ceiling = physics.overheadHeight({ x: camPosition.x, y: state.position.y, z: camPosition.z });
      if (ceiling != null) camPosition.y = Math.min(camPosition.y, ceiling - .25);
    }
    camera.position.copy(camPosition);
    camera.lookAt(camTarget);
  }

  // Headlights at night: a soft pool of light on the road ahead of every vehicle (one instanced additive quad each).
  const poolCanvas = document.createElement("canvas");
  poolCanvas.width = 64; poolCanvas.height = 128;
  const poolContext = poolCanvas.getContext("2d");
  // An ellipse that fades to nothing inside the quad (stretch a circle by two along the length).
  poolContext.scale(1, 2);
  const gradient = poolContext.createRadialGradient(32, 32, 2, 32, 32, 31);
  gradient.addColorStop(0, "rgba(255,244,200,1)");
  gradient.addColorStop(1, "rgba(255,244,200,0)");
  poolContext.fillStyle = gradient;
  poolContext.fillRect(0, 0, 64, 64);
  const poolTexture = new CanvasTexture(poolCanvas);
  poolTexture.colorSpace = SRGBColorSpace;
  const POOL_CAPACITY = 64;
  const headlightPools = new InstancedMesh(new PlaneGeometry(4.2, 9).rotateX(-Math.PI / 2), new MeshBasicMaterial({ map: poolTexture, transparent: true, blending: AdditiveBlending, depthWrite: false, opacity: 0 }), POOL_CAPACITY);
  headlightPools.frustumCulled = false;
  headlightPools.count = 0;
  headlightPools.renderOrder = 2;
  scene.add(headlightPools);
  const poolMatrix = new Matrix4(), poolQuaternion = new Quaternion(), poolUp = new Vector3(0, 1, 0), poolPosition = new Vector3(), poolScale = new Vector3(1, 1, 1);
  function setHeadlights(poses) {
    const list = poses.slice(0, POOL_CAPACITY);
    list.forEach((pose, index) => {
      poolQuaternion.setFromAxisAngle(poolUp, pose.heading);
      poolPosition.set(pose.x + Math.sin(pose.heading) * 6.5, pose.y + 0.09, pose.z + Math.cos(pose.heading) * 6.5);
      poolMatrix.compose(poolPosition, poolQuaternion, poolScale);
      headlightPools.setMatrixAt(index, poolMatrix);
    });
    headlightPools.count = list.length;
    headlightPools.instanceMatrix.needsUpdate = true;
  }

  // Missions: drive to a place on the map. A gold beam marks the target, an arrow and the distance guide the way.
  // Best points per mission are kept in this browser only; storage can be blocked, so every access is guarded.
  const RECORD_KEY = "sg-world-best";
  let record = { best: {} };
  try { record = cleanRecord(JSON.parse(localStorage.getItem(RECORD_KEY))); } catch { /* No saved record. */ }
  let missionIndex = 0, missionsDone = 0, score = 0, missionStart = { time: 0, damage: 0, distance: 0 }, missionClock = 0;
  const missionText = stage.querySelector(".world-mission-text"), missionArrow = stage.querySelector(".world-arrow");
  const beam = new Mesh(new CylinderGeometry(3, 3, 140, 20, 1, true), new MeshBasicMaterial({ color: 0xffd36a, transparent: true, opacity: 0.28, side: DoubleSide, depthWrite: false }));
  scene.add(beam);
  function setMission(index, from = null) {
    missionIndex = index;
    // The par distance is the real road distance from the place the car left (the start, or the mission just done); from anywhere else a detour estimate.
    const origin = from?.position ?? start, straight = distanceTo(origin, MISSIONS[index]);
    missionStart = { time: missionClock, damage: from?.damage ?? 0, distance: roadDistance(ROAD_DISTANCES, from?.placeId ?? "start", MISSIONS[index].id, straight) };
    beam.position.set(MISSIONS[index].x, 70, MISSIONS[index].z);
  }
  setMission(0);
  root.querySelector(".world-next").addEventListener("click", () => { const state = vehicle.getState(); setMission(nextMission(missionIndex, state.position), state); });
  // Minimap: the road graph around the car, traffic as dots and the mission target.
  const minimap = stage.querySelector(".drive-minimap"), minimapContext = minimap.getContext("2d");
  const MINIMAP_COLORS = { background: "rgba(10,18,36,0.72)", road: "rgba(205,215,230,0.85)", traffic: "#ffd36a", target: "#ff5a4f", car: "#ffffff" };
  let minimapFrame = 0;
  function drawMinimap(state) {
    if (minimapFrame++ % 4) return;
    const edges = signalGraph ? [...signalGraph.edges.values()] : [];
    const target = MISSIONS[missionIndex];
    paintMinimap(minimapContext, {
      size: { width: minimap.width, height: minimap.height }, car: { x: state.position.x, z: state.position.z }, heading: state.heading, edges,
      vehicles: traffic.vehicles.map(vehicle => traffic.pose(vehicle)).filter(Boolean), target: { x: target.x, z: target.z }, colors: MINIMAP_COLORS,
    });
  }

  // The checkpoint: stop at the Woodlands barrier and play the passport stamp game before the mission counts.
  const passport = stage.querySelector(".world-passport"), passportText = stage.querySelector(".drive-passport-text");
  const stampBar = stage.querySelector(".drive-stamp-bar"), stampMarker = stage.querySelector(".drive-stamp-marker"), passportAction = stage.querySelector(".drive-passport-action");
  stage.querySelector(".drive-stamp-zone").style.left = `${STAMP_ZONE[0] * 100}%`;
  stage.querySelector(".drive-stamp-zone").style.width = `${(STAMP_ZONE[1] - STAMP_ZONE[0]) * 100}%`;
  let stamp = null, boomOpenUntil = -1, boomOpen = 0;
  function renderPassport() {
    passport.hidden = !stamp;
    if (!stamp) return;
    const showing = stamp.state.phase === "show";
    passportText.textContent = t(showing ? "drive.passport.show" : "drive.passport.stamp");
    stampBar.hidden = showing;
    localize(passportAction, showing ? "drive.passport.showButton" : "drive.passport.stampButton");
  }
  function pressPassport() {
    if (!stamp) return;
    const result = stamp.press();
    if (result === "hit") {
      audio.stamp();
      const state = vehicle.getState();
      stamp = null;
      renderPassport();
      completeMission(state, CHECKPOINT_BONUS);
    } else if (result === "miss") passportText.textContent = t("drive.passport.again");
    else renderPassport();
  }
  passportAction.addEventListener("click", pressPassport);
  addEventListener("keydown", event => { if (stamp && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); event.stopImmediatePropagation(); pressPassport(); } }, { signal, capture: true });

  function completeMission(state, bonus = 0) {
    const mission = MISSIONS[missionIndex];
    missionsDone++;
    const points = missionScore({ distance: missionStart.distance, seconds: missionClock - missionStart.time, damage: state.damage - missionStart.damage }) + bonus;
    score += points;
    const saved = recordScore(record, mission.id, points);
    record = saved.record;
    try { localStorage.setItem(RECORD_KEY, JSON.stringify(record)); } catch { /* Not saved. */ }
    if (mission.checkpoint) boomOpenUntil = missionClock + 9; // lift the barriers for a while
    notify("world.mission.done", { place: t(mission.name), points });
    setMission(nextMission(missionIndex, state.position), { ...state, placeId: mission.id });
  }

  function updateMission(state) {
    const mission = MISSIONS[missionIndex], distance = distanceTo(state.position, mission);
    if (arrived(state.position, mission)) {
      if (!mission.checkpoint) { completeMission(state); return; }
      // A checkpoint needs the car to be (nearly) stopped at the barrier.
      if (stamp) { missionText.textContent = t(mission.name); return; }
      if (state.speed < 2) { stamp = createStamp(); renderPassport(); audio.beep(); return; }
      missionText.textContent = t("world.checkpoint.stop");
      return;
    }
    const best = record.best[mission.id];
    missionText.textContent = `${t("world.mission.drive", { place: t(mission.name) })} · ${distance >= 1000 ? `${(distance / 1000).toFixed(1)} km` : `${Math.round(distance)} m`}${best ? ` · ${t("world.best", { points: best })}` : ""}`;
    missionArrow.style.transform = `rotate(${(-relativeBearing(state.position, state.heading, mission)).toFixed(3)}rad)`;
  }

  // Time of day: sky, fog, ground, sun, lit windows and street lamps follow the hour (one hour passes in 30 seconds).
  const lampMaterials = new Set();
  for (const name of ["road_light"]) for (const part of kit.get(name)?.parts ?? []) for (const material of [part.material].flat()) if (material.name === "lamp_emissive") lampMaterials.add(material);
  let hour = 15;
  const timeButton = root.querySelector(".world-time");
  const hourText = () => `${String(Math.floor(hour)).padStart(2, "0")}:${String(Math.floor((hour % 1) * 60)).padStart(2, "0")}`;
  function setHour(value) {
    hour = ((value % 24) + 24) % 24;
    const state = dayAt(hour);
    scene.background = state.sky;
    scene.fog.color.copy(state.sky);
    flatGround.material.color.copy(state.ground);
    sun.intensity = state.sun;
    hemisphere.intensity = 0.55 + state.sun * 0.38;
    buildingMaterial.emissiveIntensity = state.lamp * 1.1;
    towerMaterial.emissiveIntensity = state.lamp * 0.32;
    ambient.intensity = 0.12 + 0.23 * (1 - state.lamp);
    headlightPools.material.opacity = state.lamp * 0.55;
    headlightPools.visible = state.lamp > 0.02;
    for (const material of lampMaterials) { material.emissive?.copy(material.color); material.emissiveIntensity = state.lamp * 1.6; }
    timeButton.textContent = t("world.time", { time: hourText() });
  }
  const PRESETS = [8, 13, 18.5, 22];
  timeButton.addEventListener("click", () => setHour(PRESETS.find(value => value > hour + 0.01) ?? PRESETS[0]));
  setHour(hour);

  const resize = () => {
    const { width, height } = stage.getBoundingClientRect();
    if (!width || !height) return;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize);
  observer.observe(stage);
  resize();

  const governor = createQualityGovernor({
    initial: Math.min(devicePixelRatio, touchDevice ? 1.5 : 2),
    onChange: ratio => { renderer.setPixelRatio(ratio); resize(); },
  });
  let fixedView = null;
  let frame = 0, last = performance.now(), running = true, distanceDriven = 0, previousPosition = null;
  function affectedOccupants() {
    const result = [];
    for (const car of traffic.vehicles) {
      if (!solidVehicles.has(car.id)) continue;
      const position = traffic.pose(car);
      if (position) result.push({ position, speed: car.speed, radius: car.type.length / 2 });
    }
    for (const person of solidWalkers.keys()) result.push({ position: person.root.position, speed: 2, radius: .5 });
    return result;
  }
  function advance(dt, input) {
    const state = vehicle.getState();
    beforePhysics(state, dt, affectedOccupants);
    vehicle.setControls(input);
    updateTraffic(dt, state);
    const previous = activation.available;
    const active = activation.afterPhysics(physics.step(dt));
    if (active && !previous) {
      graphDirty = true;
      updateTraffic(0, vehicle.getState());
    }
  }
  function step(now) {
    if (!running) return;
    frame = requestAnimationFrame(step);
    governor.update(now);
    const dt = clamp((now - last) / 1000, 0, 0.1);
    last = now;
    if (!paused) advance(dt, controlsNow());
    const state = placeCar(paused ? 0 : dt);
    flatGround.position.x = state.position.x; flatGround.position.z = state.position.z; // the green plane under everything follows the car
    updateEntrance(state.position);
    const effects = damageEffects(state.damage);
    smoke.update(dt, { x: state.position.x + Math.sin(state.heading) * 1.6, y: state.position.y + 0.9, z: state.position.z + Math.cos(state.heading) * 1.6 }, effects.smoke);
    if (effects.stalled && !wasStalled) notify("world.stalled");
    wasStalled = effects.stalled;
    if (!paused) missionClock += dt;
    updateMission(state);
    // The checkpoint barriers swing up (about a second) while boomOpenUntil lies ahead, then down again.
    boomOpen += ((missionClock < boomOpenUntil ? 1 : 0) - boomOpen) * Math.min(1, dt * 3);
    for (const arm of booms) arm.rotation.z = -Math.PI / 2 * boomOpen;
    if (stamp) { if (!paused) stamp.update(dt); if (stamp.state.phase === "stamp") stampMarker.style.left = `${stamp.state.value * 100}%`; }
    drawMinimap(state);
    if (fixedView) { camera.position.set(...fixedView.position); camera.lookAt(...fixedView.target); } else placeCamera(state, dt);
    const tx = Math.floor(state.position.x / TILE_SIZE), tz = Math.floor(state.position.z / TILE_SIZE);
    carTile = [tx, tz];
    updateTiles(tx, tz);
    if (previousPosition) distanceDriven += Math.hypot(state.position.x - previousPosition.x, state.position.z - previousPosition.z);
    previousPosition = { x: state.position.x, z: state.position.z };
    speedLabel.textContent = String(Math.round(state.speed * 3.6));
    roadLabel.textContent = state.flipped ? t("world.flipped") : "";
    tripLabel.textContent = `${t("world.damage")} ${Math.round(state.damage * 100)}%  ·  ${(distanceDriven / 1000).toFixed(2)} km  ·  ${t("world.score")} ${score}`;
    if (state.damage - lastCrash > 0.02) { audio.bump(); notify("world.crash"); }
    lastCrash = state.damage;
    if (state.flipped && !lastFlip) notify("world.flippedHint");
    lastFlip = state.flipped;
    if (eventTimer > 0) { eventTimer -= dt; if (eventTimer <= 0) eventLine.textContent = ""; }
    if (!paused) setHour(hour + dt / 30);
    if (headlightPools.visible) setHeadlights(headlightPoses);
    audio.update(state.speed, 0.5);
    renderer.render(scene, camera);
  }
  hud.hidden = false;
  stage.dataset.state = "ready";
  stage.removeAttribute("aria-busy");
  stage.querySelector(".drive-loading").hidden = true;
  stage.querySelector(".drive-poster").hidden = true;
  frame = requestAnimationFrame(step);

  // Hooks for the browser test: stepping the physics without rendering, and a read-out of the state.
  stage.inspectTraffic = () => traffic.vehicles.flatMap(car => {
    const pose = traffic.pose(car);
    return pose ? [{ id: car.id, edgeId: car.edge, lane: car.lane, type: car.type.id, x: pose.x, y: pose.y, z: pose.z }] : [];
  });
  stage.inspectRoad = (x, z) => {
    const position = { x, y: 1, z };
    return { groundY: physics.supportHeight(position), overheadY: physics.overheadHeight(position),
      edgeId: signalGraph && nearestRoad(signalGraph, x, z)?.edge.id };
  };
  stage.inspectWorld = () => {
    const state = vehicle.getState();
    const nearbyTraffic = headlightPoses.slice(1).filter(pose => Math.hypot(pose.x - state.position.x, pose.z - state.position.z) <= 180).length;
    return { fortCanning: activation.status, nearbyTraffic, heading: state.heading, groundedWheels: state.wheels.filter(wheel => wheel.grounded).length, y: state.position.y, loading: { pending: pending.size, ready: ready.length, failed: failed.size }, tiles: tiles.size, calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, x: state.position.x, z: state.position.z, speed: state.speed, damage: state.damage, flipped: state.flipped, carTile, start, traffic: traffic.vehicles.length, signals: signalLights.count, mission: MISSIONS[missionIndex].id, vehicleId: PLAYER_VEHICLES[playerChoice].id, wheels: wheelNodes.length, wheelSpin: wheelNodes[0]?.angle ?? 0, checkpoint: stamp ? stamp.state.phase : null, booms: booms.length, boomOpen, missionsDone, score, bestRecord: record.best, smoking: smoke.points.visible, hour, supertrees: grove.length, entrances: stationEntrances.length, entranceList: stationEntrances.slice(0, 3).map(item => ({ x: item.x, z: item.z })), nearEntrance: nearEntrance ? stationName(nearEntrance) : null, people: pedestrians?.people.filter(person => person.root.visible).length ?? 0, trafficTypes: [...new Set(traffic.vehicles.map(item => item.type.id))] };
  };
  stage.simulate = (seconds, input) => { for (let i = 0; i < seconds * 60; i++) advance(1 / 60, input); return stage.inspectWorld(); };
  stage.hurt = amount => vehicle.crash.addImpact((4 + amount * 40) * 1300); // test hook: damage the car by about `amount`
  // Test hook: apply a steering input for a few physics steps and read the angle the front wheel nodes are given.
  stage.steerCheck = input => {
    for (let i = 0; i < 20; i++) { vehicle.setControls(input); physics.step(1 / 60); }
    placeCar(0);
    const front = wheelNodes.filter(wheel => wheel.front).map(wheel => wheel.node.rotation.y), rear = wheelNodes.filter(wheel => !wheel.front).map(wheel => wheel.node.rotation.y);
    return { front, rear };
  };
  stage.setHour = value => setHour(value);
  stage.setMission = index => setMission(index);
  stage.stampHit = () => { // test hook: show the passport, sweep the marker into the green zone and press
    if (!stamp) return false;
    if (stamp.state.phase === "show") pressPassport();
    stamp.state.value = (STAMP_ZONE[0] + STAMP_ZONE[1]) / 2;
    pressPassport();
    return true;
  };
  stage.setView = view => { fixedView = view; };
  stage.teleport = (x, z, heading = 0) => { previousPosition = null; vehicle.resetUpright({ position: { x, y: restHeight + 0.2, z }, heading, repair: true }); };

  return {
    dispose() {
      running = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      audio.dispose();
      pedestrians?.dispose();
      smoke.dispose();
      beam.geometry.dispose();
      beam.material.dispose();
      signalLights.dispose();
      for (const mesh of furnitureMeshes) mesh.dispose?.();
      for (const solid of solidVehicles.values()) solid.remove();
      for (const solid of solidWalkers.values()) solid.remove();
      activation.dispose();
      for (const key of [...tiles.keys()]) unload(key);
      physics.dispose();
      scene.traverse(node => { node.geometry?.dispose(); for (const m of [node.material].flat().filter(Boolean)) { m.map?.dispose(); m.dispose(); } });
      facade.texture.dispose();
      facade.glow.dispose();
      glass.texture.dispose();
      glass.glow.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
      disposeModels(kitScenes);
    },
  };
}
