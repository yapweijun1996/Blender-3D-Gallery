import {
  AmbientLight, BoxGeometry, Color, DirectionalLight, DoubleSide, Fog, Group, HemisphereLight, Mesh, MeshLambertMaterial, PerspectiveCamera,
  PlaneGeometry, Scene, WebGLRenderer,
} from "three";
import { clone } from "three/addons/utils/SkeletonUtils.js";
import manifestData from "../../models/chibi-dressup/manifest.json";
import { getLanguage, localize, mountMarkup, onLanguageChange, t } from "../i18n/index.js";
import { loadConfig, validateManifest } from "../chibi-dressup/config.js";
import { bindModule, createRig } from "../chibi-dressup/rig.js";
import { disposeModels, getBounds, loadModels } from "../chibi-dressup/view.js";
import { createDriveAudio } from "../drive/audio.js";
import { cloneModel, instanceModel, loadKitFrom } from "../drive/kit.js";
import { addPedestrians } from "../drive/pedestrians.js";
import { locate, polylineRoute, sample } from "../drive/route.js";
import { ROAD_HALF_WIDTH, ribbon, roadTexture, stripBetween } from "../drive/world.js";
import { BUILDINGS, CAR_SPOT, CROSSINGS, PROPS, RING, ringPoints } from "./layout.js";
import "./style.css";

const kitUrls = import.meta.glob("../../models/city/kit/*.glb", { eager: true, query: "?url", import: "default" });
const driveUrls = import.meta.glob("../../models/drive/kit/{car_saga,car_hatchback_hd,bus_hd,van_hd}.glb", { eager: true, query: "?url", import: "default" });
const dressupUrls = import.meta.glob("../../models/chibi-dressup/{*.glb,bodies/**/*.glb,modules/*.glb}", { eager: true, query: "?url", import: "default" });
const KIT = ["hdb_block", "hdb_void_deck", "hdb_coffee_shop", "provision_shop", "shoplot", "public_market", "mrt_entrance", "hawker_stall", "chicken_rice_stall", "bus_shelter",
  "signal_pole", "zebra_crossing", "street_sign", "heritage_lamp", "bench", "block_sign", "playground_slide", "playground_swing", "rain_tree_hd", "angsana_tree",
  "tembusu_tree_hd", "frangipani_tree", "coconut_palm"];
const WALK = 2.4, RUN = 5.6, SCALE = 1.45, RADIUS = 0.45;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const rng = seed => () => (seed = (seed * 1664525 + 1013904223) >>> 0) / 4294967296;

/** Push a circle out of an oriented box (a placed solid building). */
function pushOut(x, z, box, radius = RADIUS) {
  const dx = x - box.x, dz = z - box.z;
  const c = Math.cos(box.yaw), s = Math.sin(box.yaw);
  // Local frame: +Z forward (sin, cos), +X to the left of forward looking down +Z (cos, -sin).
  const lx = dx * c - dz * s, lz = dx * s + dz * c;
  const ox = box.hx + radius - Math.abs(lx), oz = box.hz + radius - Math.abs(lz);
  if (ox <= 0 || oz <= 0) return null;
  if (ox < oz) { const k = Math.sign(lx || 1) * ox; return [x + k * c, z - k * s]; }
  const k = Math.sign(lz || 1) * oz;
  return [x + k * s, z + k * c];
}

export async function mountCity(root, thumbnail, signal) {
  mountMarkup(root, `<section class="city">
    <header class="city-heading"><h1 data-i18n="demo.sg-heartland.title"></h1><p data-i18n="demo.sg-heartland.description"></p></header>
    <div class="city-stage" data-state="loading" aria-busy="true">
      <img class="city-poster" alt=""><p class="city-loading" role="status" data-i18n="city.loading"></p>
      <div class="city-hud" hidden>
        <p class="city-place"></p>
        <div class="city-stick" aria-hidden="true"><i></i></div>
        <button type="button" class="city-run" aria-pressed="false" data-i18n="city.run"></button>
        <button type="button" class="city-action" hidden></button>
        <button type="button" class="city-sound" aria-pressed="true" data-i18n="drive.sound"></button>
      </div>
    </div>
    <p class="city-hint" data-i18n="city.hint"></p>
    <p class="city-credit" data-i18n="city.credit"></p>
  </section>`);
  for (const [name, value] of Object.entries({
    "--city-sky": "#f2c48f", "--city-panel": "#1c2a22", "--city-ink": "#ffffff", "--city-line": "rgba(255,255,255,.5)",
    "--city-panel-soft": "rgba(11,26,20,.5)", "--city-gold": "#ffd36a", "--city-on-gold": "#1c1c1c",
  })) root.querySelector(".city").style.setProperty(name, value);
  const stage = root.querySelector(".city-stage");
  root.querySelector(".city-poster").src = thumbnail;
  const hud = stage.querySelector(".city-hud"), placeLabel = stage.querySelector(".city-place");
  const stick = stage.querySelector(".city-stick"), knob = stick.querySelector("i"), runButton = stage.querySelector(".city-run");
  const actionButton = stage.querySelector(".city-action"), soundButton = stage.querySelector(".city-sound");

  // Models: the district kit plus the drive kit's lamps for the ring road.
  const scenes = new Set();
  const kit = await loadKitFrom(KIT.map(name => [name, kitUrls[`../../models/city/kit/${name}.glb`]]), signal, scenes);
  const vehicleKit = await loadKitFrom(["car_saga", "car_hatchback_hd", "bus_hd", "van_hd"].map(name => [name, driveUrls[`../../models/drive/kit/${name}.glb`]]), signal, scenes);
  const scene = new Scene();
  scene.background = new Color(0xf2c48f);
  scene.fog = new Fog(0xf2c48f, 140, 520);
  scene.add(new HemisphereLight(0xffffff, 0x6f7a55, 1.5), new DirectionalLight(0xffe2b8, 2.2).translateX(-120).translateY(180).translateZ(90));
  const ground = new Mesh(new PlaneGeometry(900, 900), new MeshLambertMaterial({ color: 0x6f8a4f }));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
  // Ring road and pavements from the drive demo's road kit.
  const ring = polylineRoute(ringPoints(4), [{ name: "Heartland Ring", from_m: 0 }], 4);
  scene.add(ribbon(ring, 6, ROAD_HALF_WIDTH, 0.12, roadTexture(), 24));
  const pavement = new MeshLambertMaterial({ color: 0xcfc6b2, side: DoubleSide }), kerb = new MeshLambertMaterial({ color: 0xb9b2a2, side: DoubleSide });
  for (const side of [-1, 1]) {
    const edge = side * (ROAD_HALF_WIDTH + 0.2);
    scene.add(stripBetween(ring, 8, edge, side * (ROAD_HALF_WIDTH + 3.6), 0.3, 0.3, () => true, pavement));
    scene.add(stripBetween(ring, 8, edge, edge, 0.12, 0.3, () => true, kerb));
  }
  const plaza = new Mesh(new PlaneGeometry(RING.halfX * 2 - 40, RING.halfZ * 2 - 40), new MeshLambertMaterial({ color: 0xc9bfa7 }));
  plaza.rotation.x = -Math.PI / 2; plaza.position.y = 0.05;
  scene.add(plaza);

  // Place everything; solid buildings also become collision boxes.
  const colliders = [];
  const lists = new Map();
  const add = (name, placement) => (lists.get(name) ?? lists.set(name, []).get(name)).push(placement);
  const random = rng(31);
  const tints = [0xf2e9d8, 0xe6d3b3, 0xd9e3e0, 0xf0d9c8];
  for (const b of BUILDINGS) {
    const model = kit.get(b.model);
    if (!model) continue;
    add(b.model, { x: b.x, z: b.z, yaw: b.yaw, sx: b.sx, sy: b.sy, sz: b.sz, color: tints[Math.floor(random() * tints.length)] });
    if (b.solid) colliders.push({ x: b.x, z: b.z, yaw: b.yaw, hx: (model.size.x * b.sx) / 2, hz: (model.size.z * b.sz) / 2 });
  }
  for (const p of PROPS) add(p.model, { x: p.x, z: p.z, yaw: p.yaw, scale: p.s });
  for (const c of CROSSINGS) {
    add("zebra_crossing", { x: c.x, y: 0.14, z: c.z, yaw: c.across === "x" ? Math.PI / 2 : 0, scale: 1 });
    add("signal_pole", { x: c.x + (c.across === "x" ? -ROAD_HALF_WIDTH - 1.6 : 6.5), z: c.z + (c.across === "x" ? 6.5 : -ROAD_HALF_WIDTH - 1.6), yaw: 0, scale: 1.4 });
  }
  // Lamps and trees along the ring road, further trees around the plaza and the playground.
  for (let d = 10; d < ring.length - 5; d += 38) for (const side of [-1, 1]) {
    const pose = sample(ring, d, side * (ROAD_HALF_WIDTH + 1.3));
    add("heritage_lamp", { x: pose.x, z: pose.z, yaw: 0, scale: 1.5 });
  }
  const treeNames = ["rain_tree_hd", "angsana_tree", "tembusu_tree_hd", "frangipani_tree", "coconut_palm"];
  for (let d = 5; d < ring.length - 5; d += 26) for (const side of [-1, 1]) {
    const pose = sample(ring, d + random() * 6, side * (ROAD_HALF_WIDTH + 5.5 + random() * 3));
    add(treeNames[Math.floor(random() * treeNames.length)], { x: pose.x, z: pose.z, yaw: random() * 6.28, scale: 1.2 + random() * 0.4 });
  }
  for (const [x, z] of [[62, 20], [92, 28], [66, 44], [-76, -36], [-76, 36], [-100, 0], [100, 0], [0, -70], [0, 72], [-30, 8], [30, -8]])
    add(treeNames[Math.floor(random() * treeNames.length)], { x, z, yaw: random() * 6.28, scale: 1.4 + random() * 0.4 });
  for (const [name, placements] of lists) {
    const set = instanceModel(kit.get(name), placements);
    for (const mesh of set.meshes) scene.add(mesh);
  }

  const camera = new PerspectiveCamera(58, 1, 0.3, 900);
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(devicePixelRatio, matchMedia("(pointer: coarse)").matches ? 1.5 : 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  stage.append(renderer.domElement);

  // The player: the dress-up chibi in the saved outfit.
  const manifest = validateManifest(manifestData);
  const config = loadConfig(manifest);
  const dressUrl = file => dressupUrls[`../../models/chibi-dressup/${file}`];
  const bodySpec = manifest.bodies.find(item => item.id === config.body) ?? manifest.bodies[0];
  const fits = m => (m.bodyIds ?? [manifest.bodies[0].id]).includes(bodySpec.id);
  // A visitor who never opened the dress-up demo still gets clothes: a T-shirt, jeans and sneakers of the body's family.
  for (const [slot, family] of [["top", "top-tshirt"], ["bottom", "bottom-jeans"], ["shoes", "shoes-sneakers"]]) {
    if (config.modules[slot]) continue;
    const found = manifest.modules.find(m => fits(m) && (m.family ?? m.id) === family);
    if (found && !(slot === "bottom" && manifest.modules.find(m => m.id === config.modules.top)?.excludesSlots?.includes("bottom"))) config.modules[slot] = found.id;
  }
  const worn = manifest.modules.filter(m => config.modules[m.slot] === m.id && fits(m));
  const playerScenes = new Set();
  const loaded = await loadModels([bodySpec.body, bodySpec.gestures, ...bodySpec.motion, ...worn.map(m => m.file)].map(dressUrl), signal, playerScenes);
  const [body, gestures] = loaded, motions = loaded.slice(2, 2 + bodySpec.motion.length), parts = loaded.slice(2 + bodySpec.motion.length);
  let skeleton;
  body.scene.traverse(node => { if (node.isSkinnedMesh) { skeleton = node.skeleton; node.frustumCulled = false; } });
  for (const gltf of parts) for (const mesh of bindModule(body.scene, gltf.scene, skeleton)) mesh.visible = true;
  const covered = new Set(worn.flatMap(m => m.excludesSlots ?? []));
  void covered;
  const rig = createRig(body.scene, skeleton, motions, gestures.animations);
  rig.select("idle");
  body.scene.scale.setScalar(SCALE);
  const player = { x: 0, z: 22, yaw: Math.PI, speed: 0, clip: "idle" };
  scene.add(body.scene);

  // The Proton Saga waits at the kerb; press E (or tap the button) beside it to get in.
  const car = vehicleKit.has("car_saga") ? cloneModel(vehicleKit.get("car_saga")) : null;
  const drive = { x: CAR_SPOT.x, z: CAR_SPOT.z, yaw: CAR_SPOT.yaw, speed: 0, wheel: 0 };
  if (car) scene.add(car);
  let mode = "walk";
  const audio = createDriveAudio();
  let soundOn = true;
  soundButton.addEventListener("click", () => { soundOn = !soundOn; audio.enabled = soundOn; audio.start(); soundButton.setAttribute("aria-pressed", String(soundOn)); });
  for (const name of ["pointerdown", "keydown"]) addEventListener(name, () => audio.start(), { signal, passive: true });

  // Traffic circulates on the ring road, driving on the left like the real thing.
  const fleets = [], cars = [];
  const paints = [0x3a6ea5, 0xd8d8d8, 0xe0a030, 0x4f8f5a, 0x8a4f9e, 0xc9473b, 0x9fb7c9];
  for (const [name, count, speed] of [["car_saga", 2, 9], ["car_hatchback_hd", 1, 10], ["van_hd", 1, 8], ["bus_hd", 1, 7]]) {
    const model = vehicleKit.get(name);
    if (!model) continue;
    const list = [];
    for (let i = 0; i < count; i++) list.push({ s: random() * ring.length, speed: speed + random() * 2, color: /bus|van/.test(name) ? 0xf4f4f0 : paints[Math.floor(random() * paints.length)], x: 0, z: 0, yaw: 0 });
    const instanced = instanceModel(model, list.map(v => ({ x: 0, z: 0 })), { dynamic: true });
    for (const mesh of instanced.meshes) scene.add(mesh);
    fleets.push({ list, instanced });
    cars.push(...list);
  }
  function updateTraffic(dt) {
    for (const { list, instanced } of fleets) {
      for (const v of list) {
        v.s = (v.s + v.speed * dt) % ring.length;
        const pose = sample(ring, v.s, -2.6);
        v.x = pose.x; v.z = pose.z; v.yaw = pose.heading;
      }
      instanced.write(list.map(v => ({ x: v.x, z: v.z, y: 0.12, yaw: v.yaw, color: v.color })));
    }
  }

  // Pedestrians walk the ring road pavements.
  let pedestrians = null;
  addPedestrians({ scene, route: ring, signal, count: matchMedia("(pointer: coarse)").matches ? { female: 1, male: 0 } : { female: 1, male: 1 }, allowed: () => true })
    .then(result => { if (signal.aborted) result.dispose(); else pedestrians = result; })
    .catch(error => { if (!signal.aborted) console.error("City: pedestrians failed to load", error); });
  let ringS = 0;

  // Input: keyboard, a virtual stick for touch, and drag-to-orbit.
  const keys = new Set();
  const cam = { yaw: Math.PI, pitch: 0.35, distance: 7.5 };
  const input = { x: 0, z: 0 };
  let running = false;
  const keyDir = event => ({ ArrowLeft: "l", a: "l", A: "l", ArrowRight: "r", d: "r", D: "r", ArrowUp: "u", w: "u", W: "u", ArrowDown: "b", s: "b", S: "b" })[event.key];
  addEventListener("keydown", event => { const k = keyDir(event); if (k) { keys.add(k); event.preventDefault(); } if (event.key === "Shift") running = true; }, { signal });
  addEventListener("keyup", event => { const k = keyDir(event); if (k) keys.delete(k); if (event.key === "Shift") running = false; }, { signal });
  runButton.addEventListener("click", () => { running = !running; runButton.setAttribute("aria-pressed", String(running)); });
  let stickId = null, orbitId = null, orbitFrom = null;
  const stickCentre = { x: 0, y: 0 };
  stick.addEventListener("pointerdown", event => {
    stickId = event.pointerId; stick.setPointerCapture(stickId);
    const r = stick.getBoundingClientRect(); stickCentre.x = r.left + r.width / 2; stickCentre.y = r.top + r.height / 2;
    event.preventDefault();
  });
  stick.addEventListener("pointermove", event => {
    if (event.pointerId !== stickId) return;
    const radius = stick.clientWidth / 2;
    const dx = clamp((event.clientX - stickCentre.x) / radius, -1, 1), dy = clamp((event.clientY - stickCentre.y) / radius, -1, 1);
    input.x = dx; input.z = dy; knob.style.transform = `translate(${dx * radius * 0.6}px, ${dy * radius * 0.6}px)`;
  });
  const endStick = event => { if (event.pointerId !== stickId) return; stickId = null; input.x = input.z = 0; knob.style.transform = ""; };
  stick.addEventListener("pointerup", endStick); stick.addEventListener("pointercancel", endStick);
  renderer.domElement.addEventListener("pointerdown", event => { orbitId = event.pointerId; orbitFrom = { x: event.clientX, y: event.clientY }; });
  addEventListener("pointermove", event => {
    if (event.pointerId !== orbitId) return;
    cam.yaw -= (event.clientX - orbitFrom.x) * 0.006; cam.pitch = clamp(cam.pitch + (event.clientY - orbitFrom.y) * 0.004, 0.08, 1.1);
    orbitFrom = { x: event.clientX, y: event.clientY };
  }, { signal });
  addEventListener("pointerup", event => { if (event.pointerId === orbitId) orbitId = null; }, { signal });

  const places = [["public_market", "city.place.hawker"], ["hdb_coffee_shop", "city.place.coffee"], ["provision_shop", "city.place.provision"], ["hdb_void_deck", "city.place.voiddeck"], ["mrt_entrance", "city.place.mrt"]];
  const placeList = BUILDINGS.filter(b => places.some(([m]) => m === b.model)).map(b => ({ ...b, key: places.find(([m]) => m === b.model)[1], r: Math.max(kit.get(b.model).size.x * b.sx, kit.get(b.model).size.z * b.sz) * 0.55 }));
  let last = performance.now(), frame = 0, running2 = true;
  const carNear = () => car && Math.hypot(player.x - drive.x, player.z - drive.z) < 4.5;
  function toggleCar() {
    if (!car) return;
    if (mode === "walk" && carNear()) {
      mode = "drive"; body.scene.visible = false; player.speed = 0; rig.select("idle"); player.clip = "idle";
      cam.yaw = drive.yaw + Math.PI; cam.distance = 9;
    } else if (mode === "drive" && Math.abs(drive.speed) < 3) {
      mode = "walk"; body.scene.visible = true; drive.speed = 0;
      player.x = drive.x + Math.cos(drive.yaw) * 2.4; player.z = drive.z - Math.sin(drive.yaw) * 2.4; // step out on the left side
      cam.distance = 7.5;
    }
  }
  addEventListener("keydown", event => { if (event.key === "e" || event.key === "E") toggleCar(); }, { signal });
  actionButton.addEventListener("click", toggleCar);
  function step(now) {
    if (!running2) return;
    frame = requestAnimationFrame(step);
    const dt = clamp((now - last) / 1000, 0, 0.05);
    last = now;
    const ix = (keys.has("r") ? 1 : 0) - (keys.has("l") ? 1 : 0) + input.x, iz = (keys.has("b") ? 1 : 0) - (keys.has("u") ? 1 : 0) + input.z;
    const magnitude = Math.min(1, Math.hypot(ix, iz));
    if (mode === "drive") {
      // Arcade car: up to accelerate, down to brake and reverse, left and right to steer.
      const gas = clamp(-iz, -1, 1), steer = clamp(ix, -1, 1);
      drive.speed += (gas > 0 ? gas * 6 : gas * 9) * dt - drive.speed * 0.25 * dt;
      if (gas === 0) drive.speed -= Math.sign(drive.speed) * Math.min(Math.abs(drive.speed), 4 * dt);
      drive.speed = clamp(drive.speed, -4, 16);
      drive.yaw -= steer * (drive.speed / 3.2) * 0.62 * dt; // right (positive) turns right, which lowers the yaw
      let x = drive.x + Math.sin(drive.yaw) * drive.speed * dt, z = drive.z + Math.cos(drive.yaw) * drive.speed * dt;
      for (const box of colliders) { const out = pushOut(x, z, box, 2.1); if (out) { [x, z] = out; drive.speed *= 0.6; } }
      drive.x = clamp(x, -140, 140); drive.z = clamp(z, -112, 112);
      player.x = drive.x; player.z = drive.z; player.speed = 0;
    } else if (magnitude > 0.1) {
      const forwardX = -Math.sin(cam.yaw), forwardZ = -Math.cos(cam.yaw);
      const rightX = Math.cos(cam.yaw), rightZ = -Math.sin(cam.yaw);
      let dirX = forwardX * -iz + rightX * ix, dirZ = forwardZ * -iz + rightZ * ix;
      const length = Math.hypot(dirX, dirZ) || 1; dirX /= length; dirZ /= length;
      const speed = (running || magnitude > 0.85 && stickId !== null ? RUN : WALK) * (stickId !== null ? Math.max(0.5, magnitude) : 1);
      player.speed = speed;
      let x = player.x + dirX * speed * dt, z = player.z + dirZ * speed * dt;
      for (const box of colliders) { const out = pushOut(x, z, box); if (out) [x, z] = out; }
      player.x = clamp(x, -140, 140); player.z = clamp(z, -112, 112);
      let turn = Math.atan2(dirX, dirZ) - player.yaw;
      while (turn > Math.PI) turn -= 2 * Math.PI; while (turn < -Math.PI) turn += 2 * Math.PI;
      player.yaw += turn * (1 - Math.exp(-dt * 12));
    } else player.speed = 0;
    if (mode === "walk") {
      const wanted = player.speed > RUN * 0.6 ? "run" : player.speed > 0 ? "walk" : "idle";
      if (wanted !== player.clip) { player.clip = wanted; rig.select(wanted); }
      rig.update(dt, { L: null, R: null });
      body.scene.position.set(player.x, 0.05, player.z);
      body.scene.rotation.y = player.yaw;
    }
    if (car) { car.position.set(drive.x, 0.12, drive.z); car.rotation.y = drive.yaw; }
    updateTraffic(dt);
    ringS = locate(ring, player.x, player.z, ringS, 120).distance;
    pedestrians?.update(dt, ringS);
    audio.update(mode === "drive" ? Math.abs(drive.speed) : 0, 0.8);
    if (mode === "drive") { // chase camera behind the car, swinging with it
      let turn = drive.yaw + Math.PI - cam.yaw;
      while (turn > Math.PI) turn -= 2 * Math.PI; while (turn < -Math.PI) turn += 2 * Math.PI;
      if (!orbitFrom || orbitId === null) cam.yaw += turn * (1 - Math.exp(-dt * 3));
    }
    const cx = player.x + Math.sin(cam.yaw) * Math.cos(cam.pitch) * cam.distance, cz = player.z + Math.cos(cam.yaw) * Math.cos(cam.pitch) * cam.distance;
    camera.position.set(cx, 1.2 + Math.sin(cam.pitch) * cam.distance, cz);
    camera.lookAt(player.x, 1.2, player.z);
    let near = "";
    for (const p of placeList) if (Math.hypot(player.x - p.x, player.z - p.z) < p.r) { near = t(p.key); break; }
    placeLabel.textContent = near;
    placeLabel.hidden = !near;
    const action = mode === "drive" ? (Math.abs(drive.speed) < 3 ? "city.action.out" : "") : carNear() ? "city.action.in" : "";
    actionButton.hidden = !action;
    if (action) actionButton.textContent = t(action);
    renderer.render(scene, camera);
  }
  const resize = () => {
    const { clientWidth, clientHeight } = stage;
    if (!clientWidth || !clientHeight) return;
    renderer.setSize(clientWidth, clientHeight, false); camera.aspect = clientWidth / clientHeight; camera.updateProjectionMatrix();
  };
  const observer = new ResizeObserver(resize); observer.observe(stage); resize();
  onLanguageChange(() => { runButton.textContent = t("city.run"); }, signal);
  stage.inspectCity = () => ({ mode, car: { x: drive.x, z: drive.z, speed: drive.speed }, pedestrians: pedestrians?.count ?? 0, x: player.x, z: player.z, yaw: player.yaw, clip: player.clip, speed: player.speed, triangles: renderer.info.render.triangles, calls: renderer.info.render.calls, place: placeLabel.textContent });
  stage.teleport = (x, z) => { player.x = x; player.z = z; };
  stage.dataset.state = "ready"; stage.setAttribute("aria-busy", "false");
  stage.querySelector(".city-loading").remove(); root.querySelector(".city-poster").remove();
  hud.hidden = false;
  frame = requestAnimationFrame(step);
  void getBounds; void Group; void BoxGeometry; void AmbientLight; void clone; void driveUrls; void getLanguage; void localize;
  return {
    dispose() {
      running2 = false; cancelAnimationFrame(frame); observer.disconnect(); rig.dispose(); pedestrians?.dispose(); audio.dispose();
      delete stage.inspectCity;
      disposeModels(scenes); disposeModels(playerScenes);
      scene.traverse(node => { node.geometry?.dispose(); for (const m of [node.material].flat().filter(Boolean)) { m.map?.dispose(); m.dispose(); } });
      renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    },
  };
}
