import {
  AmbientLight, Color, DirectionalLight, DoubleSide, Fog, Group, HemisphereLight, Mesh, MeshLambertMaterial, PerspectiveCamera, PlaneGeometry, Quaternion, Scene, Vector3, WebGLRenderer,
} from "three";
import { localize, mountMarkup, t } from "../i18n/index.js";
import { disposeModels } from "../chibi-dressup/view.js";
import { createDriveAudio } from "../drive/audio.js";
import { cloneModel, instanceModel, loadKitFrom } from "../drive/kit.js";
import { createQualityGovernor } from "../drive/quality.js";
import { createPhysicsWorld } from "./physics/world.js";
import { LANDMARKS, hiddenOutline } from "./landmarks.js";
import { VEHICLE_TYPES, buildTrafficGraph, createRandom, createTraffic } from "./traffic.js";
import { TILE_SIZE, buildTile, buildingMesh } from "./tile-mesh.js";
import "../drive/style.css";

// Open-world study: the real OpenStreetMap road network and buildings around Marina Bay, streamed in 250 m tiles,
// with a car driven by the Rapier vehicle physics (crashes, flips). Built from models/world/tiles (scripts/world/build-tiles.mjs).
const tileUrls = import.meta.glob("../../models/world/tiles/*.json", { eager: true, query: "?url", import: "default" });
const kitUrls = import.meta.glob([
  "../../models/drive/kit/car_saga.glb", "../../models/drive/kit/car_hatchback_hd.glb", "../../models/sg-{taxi,bus-double,lorry,police,ambulance,school-bus}-hd/*.glb", "../../models/sg-rain-tree/*.glb", "../../models/sg-angsana/*.glb", "../../models/sg-coconut-palm/*.glb",
  "../../models/sg-road-light/*.glb",
], { eager: true, query: "?url", import: "default" });
const landmarkUrls = import.meta.glob("../../models/sg-{marina-bay-sands-towers,marina-bay-sands-podium,esplanade-domes,esplanade-base,merlion,merlion-park,artscience-museum,helix-bridge}/*.glb", { eager: true, query: "?url", import: "default" });
const KIT = { car_saga: "drive/kit/car_saga", car_hatchback_hd: "drive/kit/car_hatchback_hd", "sg-taxi-hd": "sg-taxi-hd/sg-taxi-hd", "sg-bus-double-hd": "sg-bus-double-hd/sg-bus-double-hd", "sg-lorry-hd": "sg-lorry-hd/sg-lorry-hd", "sg-police-hd": "sg-police-hd/sg-police-hd", "sg-ambulance-hd": "sg-ambulance-hd/sg-ambulance-hd", "sg-school-bus-hd": "sg-school-bus-hd/sg-school-bus-hd", rain_tree: "sg-rain-tree/sg-rain-tree", angsana: "sg-angsana/sg-angsana", coconut_palm: "sg-coconut-palm/sg-coconut-palm", road_light: "sg-road-light/sg-road-light" };
const TREES = ["rain_tree", "angsana", "coconut_palm"];
const LOAD_RADIUS = 2, SOLID_RADIUS = 1; // in tiles around the car
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const tileKey = (x, z) => `${x}_${z}`;

async function fetchTile(key, signal) {
  const url = tileUrls[`../../models/world/tiles/${key}.json`];
  if (!url) return null;
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`tile ${key}: HTTP ${response.status}`);
  return response.json();
}

export async function mountWorld(root, thumbnail, signal) {
  mountMarkup(root, `<section class="drive">
    <header class="drive-heading">
      <h1 data-i18n="demo.sg-world.title"></h1>
      <p data-i18n="demo.sg-world.description"></p>
    </header>
    <div class="drive-stage" data-state="loading" data-mode="manual" aria-busy="true">
      <img class="drive-poster" alt="">
      <p class="drive-loading" role="status" data-i18n="world.loading"></p>
      <div class="drive-hud" hidden>
        <div class="drive-readout"><strong class="drive-speed">0</strong><span data-i18n="drive.kmh"></span></div>
        <p class="drive-road" aria-live="polite"></p>
        <p class="drive-trip"></p>
        <p class="drive-event" role="status" aria-live="polite"></p>
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
      <button type="button" class="drive-sound" aria-pressed="true" data-i18n="drive.sound"></button>
    </div>
    <p class="drive-hint" data-i18n="world.hint"></p>
    <p class="drive-credit" data-i18n="world.credit"></p>
  </section>`);
  const stage = root.querySelector(".drive-stage");
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
  physics.addGround({ halfWidth: 3000, halfDepth: 3000 });
  signal.throwIfAborted();

  const scene = new Scene();
  scene.background = new Color(0x9fcdea);
  scene.fog = new Fog(0x9fcdea, 260, 700);
  scene.add(new HemisphereLight(0xdff0ff, 0x7a8a68, 1.5), new AmbientLight(0xffffff, 0.35));
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
  const buildingMaterial = new MeshLambertMaterial({ vertexColors: true, side: DoubleSide });
  const flatGround = new Mesh(new PlaneGeometry(6000, 6000).rotateX(-Math.PI / 2), new MeshLambertMaterial({ color: 0x8aa06f }));
  flatGround.position.y = -0.3;
  scene.add(flatGround);

  for (const landmark of LANDMARKS) {
    for (const name of landmark.models) {
      const model = landmarkKit.get(name);
      if (!model) continue;
      const copy = cloneModel(model);
      copy.position.set(landmark.pose.x, 0, landmark.pose.z);
      copy.rotation.y = landmark.pose.yaw;
      scene.add(copy);
    }
  }

  // Streaming: tiles near the car are fetched and built one per frame; colliders only exist for the nearest ring.
  let graphDirty = true;
  const tiles = new Map(); // key -> { x, z, group, solids, colliders, instances }
  const pending = new Set();
  let tileCount = 0;
  const failed = new Set();
  function addInstances(entry, built) {
    const lists = new Map();
    built.trees.forEach(([x, z], index) => {
      const name = TREES[(Math.abs(Math.round(x * 7 + z * 13)) + index) % TREES.length];
      if (!kit.has(name)) return;
      (lists.get(name) ?? lists.set(name, []).get(name)).push({ x, z, yaw: ((x * 12.9898 + z * 78.233) % 6.283), scale: 1.2 });
    });
    if (kit.has("road_light")) lists.set("road_light", built.lamps.map(([x, z]) => ({ x, z, yaw: 0, scale: 1 })));
    for (const [name, placements] of lists) {
      if (!placements.length) continue;
      const set = instanceModel(kit.get(name), placements);
      for (const mesh of set.meshes) { entry.group.add(mesh); entry.instances.push(mesh); }
    }
  }
  function buildEntry(x, z, data) {
    const built = buildTile(data, { hide: hiddenOutline });
    const group = new Group();
    const entry = { x, z, data, group, solids: built.solids, colliders: null, instances: [], geometries: [] };
    if (built.ground) { const mesh = new Mesh(built.ground, groundMaterial); mesh.matrixAutoUpdate = false; group.add(mesh); entry.geometries.push(built.ground); }
    if (built.buildings) { const mesh = new Mesh(built.buildings, buildingMaterial); mesh.matrixAutoUpdate = false; group.add(mesh); entry.geometries.push(built.buildings); }
    addInstances(entry, built);
    scene.add(group);
    tiles.set(tileKey(x, z), entry);
    tileCount++;
    graphDirty = true;
    return entry;
  }
  function setColliders(entry, wanted) {
    if (wanted && !entry.colliders) {
      entry.colliders = entry.solids.map(solid => {
        const { vertices, indices } = buildingMesh(solid.ring, solid.height);
        return physics.addStaticTrimesh({ vertices, indices });
      });
    } else if (!wanted && entry.colliders) {
      for (const collider of entry.colliders) physics.removeStatic(collider);
      entry.colliders = null;
    }
  }
  function unload(key) {
    const entry = tiles.get(key);
    if (!entry) return;
    setColliders(entry, false);
    scene.remove(entry.group);
    for (const geometry of entry.geometries) geometry.dispose();
    for (const mesh of entry.instances) mesh.dispose?.();
    tiles.delete(key);
    graphDirty = true;
  }
  let loadChain = Promise.resolve();
  function request(x, z) {
    const key = tileKey(x, z);
    if (tiles.has(key) || pending.has(key) || failed.has(key) || !tileUrls[`../../models/world/tiles/${key}.json`]) return;
    pending.add(key);
    loadChain = loadChain.then(() => fetchTile(key, signal)).then(data => { if (data && !signal.aborted) ready.push({ x, z, data }); })
      .catch(error => { if (!signal.aborted) { failed.add(key); console.error("World: tile failed", key, error); } })
      .finally(() => pending.delete(key));
  }
  const ready = [];
  function updateTiles(cx, cz) {
    for (let dz = -LOAD_RADIUS; dz <= LOAD_RADIUS; dz++) for (let dx = -LOAD_RADIUS; dx <= LOAD_RADIUS; dx++) request(cx + dx, cz + dz);
    const next = ready.shift();
    if (next && !tiles.has(tileKey(next.x, next.z))) buildEntry(next.x, next.z, next.data);
    for (const [key, entry] of tiles) {
      const distance = Math.max(Math.abs(entry.x - cx), Math.abs(entry.z - cz));
      if (distance > LOAD_RADIUS + 1) unload(key);
      else setColliders(entry, distance <= SOLID_RADIUS);
    }
  }

  // Load the tiles around the start before the first frame, so the car does not spawn in the void.
  const startTile = [0, 0];
  const startData = new Map();
  for (let dz = -1; dz <= 1; dz++) for (let dx = -1; dx <= 1; dx++) {
    const x = startTile[0] + dx, z = startTile[1] + dz;
    const data = await fetchTile(tileKey(x, z), signal).catch(() => null);
    if (!data) continue;
    startData.set(tileKey(x, z), data);
    buildEntry(x, z, data);
  }
  signal.throwIfAborted();

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

  const vehicle = physics.addVehicle({ type: "sedan", position: { x: start.x, y: 1.2, z: start.z }, heading: start.heading });
  for (let i = 0; i < 90; i++) physics.step(1 / 60);
  const restHeight = vehicle.getState().position.y; // the chassis centre height when standing on the road
  const car = kit.has("car_saga") ? cloneModel(kit.get("car_saga")) : new Group();
  const carHolder = new Group();
  carHolder.add(car);
  scene.add(carHolder);

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
  const solidVehicles = new Map();
  function updateTraffic(dt, state) {
    if (graphDirty) { traffic.setGraph(buildTrafficGraph([...tiles.values()].map(entry => entry.data))); graphDirty = false; }
    traffic.update(dt, state.position);
    const lists = new Map([...trafficSets.keys()].map(name => [name, []]));
    const alive = new Set();
    for (const vehicle of traffic.vehicles) {
      const list = lists.get(vehicle.type.model);
      if (!list) continue;
      const pose = traffic.pose(vehicle);
      if (!pose) continue;
      list.push({ x: pose.x, y: 0, z: pose.z, yaw: pose.heading });
      alive.add(vehicle.id);
      const near = Math.hypot(pose.x - state.position.x, pose.z - state.position.z) < 55;
      let solid = solidVehicles.get(vehicle.id);
      if (near && !solid) {
        solid = physics.addKinematicBox({ halfExtents: { x: vehicle.type.width / 2, y: 0.8, z: vehicle.type.length / 2 }, position: { x: pose.x, y: 0.8, z: pose.z }, yaw: pose.heading });
        solidVehicles.set(vehicle.id, solid);
      } else if (!near && solid) { solid.remove(); solidVehicles.delete(vehicle.id); solid = null; }
      solid?.setPose(pose.x, 0.8, pose.z, pose.heading);
    }
    for (const [id, solid] of solidVehicles) if (!alive.has(id)) { solid.remove(); solidVehicles.delete(id); }
    for (const [name, set] of trafficSets) set.write(lists.get(name));
  }

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
  const notify = key => { eventLine.textContent = t(key); eventTimer = 2.6; };
  function resetCar() {
    // Right the car where it stands (lifted a little); repairs it as well.
    vehicle.resetUpright({ repair: true });
    notify("world.righted");
  }
  root.querySelector(".drive-reset").addEventListener("click", resetCar);

  function controlsNow() {
    const state = vehicle.getState();
    const forward = state.forwardSpeed;
    const wantsBrake = held("brake");
    return {
      throttle: held("gas") ? 1 : 0,
      brake: wantsBrake && forward > 1 ? 1 : 0,
      reverse: wantsBrake && forward <= 1 ? 1 : 0,
      steer: (held("left") ? 1 : 0) - (held("right") ? 1 : 0),
      handbrake: keys.has("hand") ? 1 : 0,
    };
  }

  const camTarget = new Vector3(), camPosition = new Vector3(), quaternion = new Quaternion();
  let camHeading = start.heading, camReady = false;
  function placeCar() {
    const state = vehicle.getState();
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
    const back = 8.5 + clamp(state.speed * 0.12, 0, 4), up = 3.4 + clamp(state.speed * 0.04, 0, 1.4);
    camPosition.set(state.position.x - Math.sin(camHeading) * back, state.position.y + up, state.position.z - Math.cos(camHeading) * back);
    camTarget.set(state.position.x + Math.sin(camHeading) * 6, state.position.y + 1.2, state.position.z + Math.cos(camHeading) * 6);
    camera.position.copy(camPosition);
    camera.lookAt(camTarget);
  }

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
  let frame = 0, last = performance.now(), running = true, carTile = [startTile[0], startTile[1]], distanceDriven = 0, previousPosition = null;
  function step(now) {
    if (!running) return;
    frame = requestAnimationFrame(step);
    governor.update(now);
    const dt = clamp((now - last) / 1000, 0, 0.1);
    last = now;
    if (!paused) {
      vehicle.setControls(controlsNow());
      updateTraffic(dt, vehicle.getState());
      physics.step(dt);
    }
    const state = placeCar();
    if (fixedView) { camera.position.set(...fixedView.position); camera.lookAt(...fixedView.target); } else placeCamera(state, dt);
    const tx = Math.floor(state.position.x / TILE_SIZE), tz = Math.floor(state.position.z / TILE_SIZE);
    carTile = [tx, tz];
    updateTiles(tx, tz);
    if (previousPosition) distanceDriven += Math.hypot(state.position.x - previousPosition.x, state.position.z - previousPosition.z);
    previousPosition = { x: state.position.x, z: state.position.z };
    speedLabel.textContent = String(Math.round(state.speed * 3.6));
    roadLabel.textContent = state.flipped ? t("world.flipped") : "";
    tripLabel.textContent = `${t("world.damage")} ${Math.round(state.damage * 100)}%  ·  ${(distanceDriven / 1000).toFixed(2)} km`;
    if (state.damage - lastCrash > 0.02) { audio.bump(); notify("world.crash"); }
    lastCrash = state.damage;
    if (state.flipped && !lastFlip) notify("world.flippedHint");
    lastFlip = state.flipped;
    if (eventTimer > 0) { eventTimer -= dt; if (eventTimer <= 0) eventLine.textContent = ""; }
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
  stage.inspectWorld = () => {
    const state = vehicle.getState();
    return { tiles: tiles.size, calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, x: state.position.x, z: state.position.z, speed: state.speed, damage: state.damage, flipped: state.flipped, carTile, start, traffic: traffic.vehicles.length, trafficTypes: [...new Set(traffic.vehicles.map(item => item.type.id))] };
  };
  stage.simulate = (seconds, input) => { for (let i = 0; i < seconds * 60; i++) { vehicle.setControls(input); updateTraffic(1 / 60, vehicle.getState()); physics.step(1 / 60); } return stage.inspectWorld(); };
  stage.setView = view => { fixedView = view; };
  stage.teleport = (x, z, heading = 0) => { previousPosition = null; vehicle.resetUpright({ position: { x, y: restHeight + 0.2, z }, heading, repair: true }); };

  return {
    dispose() {
      running = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      audio.dispose();
      for (const solid of solidVehicles.values()) solid.remove();
      for (const key of [...tiles.keys()]) unload(key);
      physics.dispose();
      scene.traverse(node => { node.geometry?.dispose(); for (const m of [node.material].flat().filter(Boolean)) { m.map?.dispose(); m.dispose(); } });
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
      disposeModels(kitScenes);
    },
  };
}
