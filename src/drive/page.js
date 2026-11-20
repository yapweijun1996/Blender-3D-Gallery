import { localize, mountMarkup, t, onLanguageChange } from "../i18n/index.js";
import routeData from "../../models/drive/route-mbs-jb.json";
import { buildRoute, findRoad, roadAt, sample, tripHour } from "./route.js";
import { createRig } from "../chibi-dressup/rig.js";
import { disposeModels, loadModels } from "../chibi-dressup/view.js";
import { Color, InstancedMesh, Matrix4, MeshBasicMaterial, SphereGeometry } from "three";
import { cloneModel, instanceModel, loadKit } from "./kit.js";
import { createDriveAudio } from "./audio.js";
import { goToPage } from "./nav.js";
import { createQualityGovernor } from "./quality.js";
import { addPedestrians } from "./pedestrians.js";
import { zoneAt } from "./scenery.js";
import { ROAD_HALF_WIDTH, buildCar, buildWorld } from "./world.js";
import "./style.css";

// The driver is the dress-up boy, loaded after the first frame so the road appears at once.
const driverUrls = import.meta.glob("../../models/chibi-dressup/bodies/male/{body,motion,gestures}.glb", { eager: true, query: "?url", import: "default" });
const CRUISE = 24;       // m/s, about 86 km/h
const TOP = 34;          // m/s in manual mode
const LANE = 2.6;
const STAMP_ZONE = [0.4, 0.62];
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

export async function mountDrive(root, thumbnail, signal) {
  const route = buildRoute(routeData);
  mountMarkup(root, `<section class="drive">
    <header class="drive-heading">
      <h1 data-i18n="demo.drive-jb.title"></h1>
      <p data-i18n="demo.drive-jb.description"></p>
    </header>
    <div class="drive-stage" data-state="loading" aria-busy="true">
      <img class="drive-poster" alt="">
      <p class="drive-loading" role="status" data-i18n="drive.loading"></p>
      <div class="drive-hud" hidden>
        <div class="drive-readout"><strong class="drive-speed">0</strong><span data-i18n="drive.kmh"></span></div>
        <p class="drive-road" aria-live="polite"></p>
        <div class="drive-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100"><i></i></div>
        <p class="drive-trip"></p>
        <p class="drive-event" role="status" aria-live="polite"></p>
        <div class="drive-pad">
          <div class="drive-steer"><button type="button" data-key="left">◀</button><button type="button" data-key="right">▶</button></div>
          <div class="drive-pedals"><button type="button" data-key="brake">■</button><button type="button" data-key="gas">▲</button></div>
        </div>
        <canvas class="drive-minimap" width="160" height="200" aria-hidden="true"></canvas>
        <div class="drive-passport" role="dialog" hidden>
          <h2 data-i18n="drive.passport.title"></h2>
          <p class="drive-passport-text"></p>
          <div class="drive-stamp-bar" hidden><i class="drive-stamp-zone"></i><b class="drive-stamp-marker"></b></div>
          <button type="button" class="drive-passport-action"></button>
        </div>
        <div class="drive-arrival" role="dialog" hidden>
          <h2 data-i18n="drive.arrival.title"></h2>
          <p data-i18n="drive.arrival.text"></p>
          <button type="button" class="drive-replay" data-i18n="drive.replay"></button>
          <button type="button" class="drive-home" data-i18n="drive.arrival.home"></button>
        </div>
      </div>
    </div>
    <div class="drive-controls" role="group">
      <div class="drive-modes" role="group">
        <button type="button" data-mode="auto" data-i18n="drive.mode.auto"></button>
        <button type="button" data-mode="manual" data-i18n="drive.mode.manual"></button>
      </div>
      <button type="button" class="drive-pause" data-i18n="common.pause"></button>
      <button type="button" class="drive-horn" data-i18n="drive.horn"></button>
      <button type="button" class="drive-sound" aria-pressed="true" data-i18n="drive.sound"></button>
    </div>
    <p class="drive-hint" data-i18n="drive.hint"></p>
    <p class="drive-credit" data-i18n="drive.credit"></p>
  </section>`);

  const stage = root.querySelector(".drive-stage");
  // Colours of the overlay on the 3D scene; set here so the stylesheet only uses roles.
  for (const [name, value] of Object.entries({
    "--drive-sky": "#0d1530", "--drive-ink": "#ffffff", "--drive-gold": "#ffd36a", "--drive-on-gold": "#1c1c1c",
    "--drive-line": "rgba(255,255,255,.3)", "--drive-shadow": "rgba(0,0,0,.7)", "--drive-panel-soft": "rgba(8,14,28,.55)",
    "--drive-panel": "rgba(10,18,36,.92)", "--drive-good": "rgba(70,170,100,.85)",
  })) root.querySelector(".drive").style.setProperty(name, value);
  root.querySelector(".drive-poster").src = thumbnail;
  const hud = stage.querySelector(".drive-hud");
  const speedLabel = stage.querySelector(".drive-speed");
  const roadLabel = stage.querySelector(".drive-road");
  const progressBar = stage.querySelector(".drive-progress");
  const tripLabel = stage.querySelector(".drive-trip");
  const minimap = stage.querySelector(".drive-minimap");
  const passport = stage.querySelector(".drive-passport");
  const passportText = stage.querySelector(".drive-passport-text");
  const stampBar = stage.querySelector(".drive-stamp-bar");
  const stampZone = stage.querySelector(".drive-stamp-zone");
  const stampMarker = stage.querySelector(".drive-stamp-marker");
  const passportAction = stage.querySelector(".drive-passport-action");
  const arrival = stage.querySelector(".drive-arrival");
  const pauseButton = root.querySelector(".drive-pause");
  const modeButtons = [...root.querySelectorAll("[data-mode]")];
  localize(root.querySelector(".drive-controls"), "drive.controls", undefined, "aria-label");
  for (const button of root.querySelectorAll("[data-key]")) localize(button, `drive.key.${button.dataset.key}`, undefined, "aria-label");
  stampZone.style.left = `${STAMP_ZONE[0] * 100}%`;
  stampZone.style.width = `${(STAMP_ZONE[1] - STAMP_ZONE[0]) * 100}%`;

  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let mode = "auto", paused = false;
  try { mode = localStorage.getItem("drive-jb-mode") === "manual" ? "manual" : "auto"; } catch { /* Use auto. */ }
  const kitScenes = new Set();
  const kit = await loadKit(signal, kitScenes).catch(error => { if (signal.aborted) throw error; console.error("Drive: model kit failed to load", error); return new Map(); });
  const lowEnd = matchMedia("(pointer: coarse)").matches; // phones draw a shorter stretch of road and fewer vehicles
  const world = buildWorld(stage, route, kit, { low: lowEnd });
  // The player drives the 1985 Proton Saga from the gallery (game-ready copy); the toy car is only a fallback.
  const playerName = kit.has("car_saga") ? "car_saga" : kit.has("car_hatchback") ? "car_hatchback" : null;
  const car = playerName === "car_saga" ? cloneModel(kit.get("car_saga")) : playerName ? cloneModel(kit.get(playerName), 0xd9453a) : buildCar();
  const wheels = { front: [], all: [], radius: 0.3 };
  car.traverse(node => {
    if (!/^wheel_/.test(node.name)) return;
    node.rotation.order = "YXZ";
    wheels.all.push(node);
    if (/^wheel_F[LR]?$/.test(node.name)) wheels.front.push(node);
  });
  world.scene.add(car);
  const { stop: stopDistance, gates } = world.landmarks;
  const START = 22; // the road begins at 0, so start a little way along it and the camera has road behind the car
  const state = { s: START, speed: 0, offset: -LANE, target: -LANE, passing: null, yaw: 0, stage: "drive", pass: false, stamp: 0, stampDir: 1, done: false, time: 0, bumpAt: -9, redAt: -9, stage0: "drive" };
  const audio = createDriveAudio();
  const eventLine = stage.querySelector(".drive-event");
  let eventTimer = 0;
  const notify = key => { eventLine.textContent = t(key); eventTimer = 2.4; };
  const soundButton = root.querySelector(".drive-sound");
  let soundOn = true;
  try { soundOn = localStorage.getItem("drive-jb-sound") !== "off"; } catch { /* Sound stays on. */ }
  audio.enabled = soundOn;
  soundButton.setAttribute("aria-pressed", String(soundOn));
  soundButton.addEventListener("click", () => {
    soundOn = !soundOn; audio.enabled = soundOn; audio.start();
    soundButton.setAttribute("aria-pressed", String(soundOn));
    try { localStorage.setItem("drive-jb-sound", soundOn ? "on" : "off"); } catch { /* Not saved. */ }
  });
  root.querySelector(".drive-horn").addEventListener("click", () => { audio.start(); audio.horn(); });
  // Browsers only start audio after a gesture.
  for (const name of ["pointerdown", "keydown"]) addEventListener(name, () => audio.start(), { signal, once: false, passive: true });
  const keys = new Set();
  const cameraTarget = { x: 0, y: 0, z: 0, yaw: 0 };
  let frameDt = 0.016;

  function localizeAll() {
    localize(pauseButton, paused ? "common.play" : "common.pause");
    for (const button of modeButtons) button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
    stage.dataset.mode = mode;
  }
  onLanguageChange(() => { renderPassport(); localizeAll(); }, signal);
  localizeAll();

  function setMode(next) {
    const changed = mode !== next;
    mode = next;
    if (changed && next === "manual" && eventLine) notify("drive.event.manual");
    try { localStorage.setItem("drive-jb-mode", mode); } catch { /* Not saved. */ }
    localizeAll();
  }
  for (const button of modeButtons) button.addEventListener("click", () => setMode(button.dataset.mode));
  pauseButton.addEventListener("click", () => { paused = !paused; localizeAll(); });

  const keyOf = event => ({ ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right",
    ArrowUp: "gas", w: "gas", W: "gas", ArrowDown: "brake", s: "brake", S: "brake" })[event.key];
  addEventListener("keydown", event => { if (event.key === "h" || event.key === "H") { audio.start(); audio.horn(); } }, { signal });
  addEventListener("keydown", event => {
    const key = keyOf(event);
    if (key) { keys.add(key); if (mode === "auto") setMode("manual"); event.preventDefault(); }
    if ((event.key === " " || event.key === "Enter") && state.stage === "passport") { event.preventDefault(); passportAction.click(); }
  }, { signal });
  addEventListener("keyup", event => { const key = keyOf(event); if (key) keys.delete(key); }, { signal });
  for (const button of root.querySelectorAll("[data-key]")) {
    const key = button.dataset.key;
    const down = event => { event.preventDefault(); keys.add(key); if (mode === "auto") setMode("manual"); };
    const up = () => keys.delete(key);
    button.addEventListener("pointerdown", down);
    for (const name of ["pointerup", "pointerleave", "pointercancel"]) button.addEventListener(name, up);
  }

  function renderPassport() {
    if (state.stage !== "passport") return;
    passport.hidden = false;
    if (!state.pass) {
      passportText.textContent = t("drive.passport.show");
      stampBar.hidden = true;
      localize(passportAction, "drive.passport.showButton");
    } else {
      passportText.textContent = t("drive.passport.stamp");
      stampBar.hidden = false;
      localize(passportAction, "drive.passport.stampButton");
    }
  }
  passportAction.addEventListener("click", () => {
    if (state.stage !== "passport") return;
    if (!state.pass) { state.pass = true; state.stamp = 0; stampMarker.style.left = "0%"; renderPassport(); return; }
    if (state.stamp >= STAMP_ZONE[0] && state.stamp <= STAMP_ZONE[1]) {
      audio.stamp();
      state.stage = "gate";
      passport.hidden = true;
    } else {
      passportText.textContent = t("drive.passport.again");
    }
  });
  stage.querySelector(".drive-home").addEventListener("click", () => goToPage("sg-heartland"));
  stage.querySelector(".drive-replay").addEventListener("click", () => {
    Object.assign(state, { s: START, speed: 0, offset: -LANE, target: -LANE, passing: null, yaw: 0, stage: "drive", pass: false, done: false });
    arrival.hidden = true;
    for (const barrier of gateBarriers()) barrier.rotation.z = 0;
  });

  function drawMinimap() {
    const g = minimap.getContext("2d");
    const { width, height } = minimap;
    g.clearRect(0, 0, width, height);
    const xs = route.points.map(p => p.x), zs = route.points.map(p => p.z);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minZ = Math.min(...zs), maxZ = Math.max(...zs);
    const scale = Math.min((width - 24) / (maxX - minX), (height - 24) / (maxZ - minZ));
    const map = p => [12 + (p.x - minX) * scale, 12 + (p.z - minZ) * scale];
    g.lineWidth = 2; g.strokeStyle = "rgba(255,255,255,.55)"; g.beginPath();
    route.points.forEach((p, i) => { const [x, y] = map(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
    g.stroke();
    const done = route.points.filter(p => p.s <= state.s);
    g.strokeStyle = "#ffd36a"; g.lineWidth = 3; g.beginPath();
    done.forEach((p, i) => { const [x, y] = map(p); if (i) g.lineTo(x, y); else g.moveTo(x, y); });
    g.stroke();
    const here = sample(route, state.s);
    const [cx, cy] = map(here);
    g.fillStyle = "#ff5a4a"; g.beginPath(); g.arc(cx, cy, 4, 0, Math.PI * 2); g.fill();
  }

  let last = performance.now(), frame = 0, minimapAt = 0, running = true;
  const governor = createQualityGovernor({
    initial: Math.min(devicePixelRatio, lowEnd ? 1.5 : 2),
    onChange: ratio => { world.renderer.setPixelRatio(ratio); resize(); },
  });
  function step(now) {
    if (!running) return;
    frame = requestAnimationFrame(step);
    governor.update(now);
    // requestAnimationFrame stamps can precede the mount time, so never let time run backwards.
    const dt = clamp((now - last) / 1000, 0, 0.05);
    frameDt = Math.max(dt, 0.001);
    last = now;
    if (!paused) update(dt);
    render(now);
  }

  function update(dt) {
    state.time += dt;
    const limit = zoneLimit();
    if (state.stage === "drive") {
      if (mode === "auto") {
        const target = Math.min(CRUISE, limit, signalLimit());
        state.speed += clamp(target - state.speed, -14 * dt, 5 * dt);
        planLane();
        state.offset += (state.target - state.offset) * Math.min(1, dt * 1.3);
        state.yaw += (clamp((state.target - state.offset) * 0.12, -0.3, 0.3) - state.yaw) * Math.min(1, dt * 4);
      } else {
        const gas = keys.has("gas") ? 1 : 0, brake = keys.has("brake") ? 1 : 0;
        state.speed += (gas * 7 - brake * 16 - (gas ? 0 : 2.5)) * dt;
        state.speed = clamp(state.speed, 0, Math.min(TOP, limit * 1.25));
        const steer = (keys.has("right") ? 1 : 0) - (keys.has("left") ? 1 : 0);
        state.yaw = clamp(state.yaw + (steer * 1.8 - state.yaw * 1.4) * dt, -0.45, 0.45);
        // Positive offset is the right-hand side of the direction of travel; steering right (positive yaw) moves right.
        state.offset += Math.sin(state.yaw) * state.speed * dt;
        const edge = ROAD_HALF_WIDTH - 1.2;
        if (Math.abs(state.offset) > edge) { state.offset = clamp(state.offset, -edge, edge); state.speed *= 1 - Math.min(1, dt * 3); state.yaw *= 0.5; }
      }
      state.speed = Math.max(0, state.speed);
      const slow = trafficAhead();
      if (slow !== null) state.speed = Math.min(state.speed, slow);
      checkOncoming();
      checkRedLight();
      state.s += state.speed * Math.cos(state.yaw) * dt;
      if (state.s >= stopDistance - 6 && state.stage === "drive" && !state.pass && !state.done) {
        state.s = Math.min(state.s, stopDistance - 6);
        state.speed = Math.max(0, state.speed - 20 * dt);
        if (state.speed < 0.2) { state.stage = "passport"; state.speed = 0; renderPassport(); audio.beep(); }
      }
      if (state.s >= route.length - 25) {
        state.s = route.length - 25; state.speed = Math.max(0, state.speed - 18 * dt);
        if (state.speed < 0.2 && !state.done) { state.done = true; state.stage = "arrived"; arrival.hidden = false; audio.arrive(); }
      }
    } else if (state.stage === "passport" && state.pass) {
      state.stamp += state.stampDir * dt * 0.75;
      if (state.stamp > 1) { state.stamp = 1; state.stampDir = -1; }
      if (state.stamp < 0) { state.stamp = 0; state.stampDir = 1; }
      stampMarker.style.left = `${state.stamp * 100}%`;
    } else if (state.stage === "gate") {
      const barriers = gateBarriers();
      for (const barrier of barriers) barrier.rotation.z = Math.min(1.4, barrier.rotation.z + dt * 1.6);
      if (!barriers.length || barriers[0].rotation.z >= 1.4) { state.stage = "drive"; state.pass = true; audio.gate(); }
    }
    updateTraffic(dt);
    pedestrians?.update(dt, state.s);
    updateSignals();
    if (eventTimer > 0 && (eventTimer -= dt) <= 0) eventLine.textContent = "";
    audio.update(state.speed, zoneAt(route, state.s) === "expressway" || zoneAt(route, state.s) === "water" ? 0.2 : 1);
  }

  // Lane choice in auto mode: overtake a slower car when the oncoming lane is clear, then return to the right lane.
  function planLane() {
    const overtaking = state.target > 0;
    if (!overtaking) {
      const blocker = vehicles.find(v => v.dir > 0 && v.s - state.s > 4 && v.s - state.s < 40 && v.speed < state.speed - 2);
      const oncoming = vehicles.some(v => v.dir < 0 && v.s > state.s - 20 && v.s < state.s + 190);
      const nearSignal = signals.some(signal => signal.s - state.s > -5 && signal.s - state.s < 120);
      if (blocker && !oncoming && !nearSignal && state.stage === "drive" && state.speed > 8 && (!state.pass ? stopDistance - state.s > 260 : true)) {
        state.target = LANE; state.passing = blocker; notify("drive.event.overtake");
      }
    } else {
      const passed = !state.passing || state.s - state.passing.s > state.passing.length + 10 || state.passing.s - state.s > 80;
      const rightClear = !vehicles.some(v => v.dir > 0 && v.s - state.s > -12 && v.s - state.s < 24);
      if (passed && rightClear) { state.target = -LANE; state.passing = null; }
    }
  }

  // Traffic lights: lamps on the poles by the zebra crossings, on a shared cycle; auto mode stops at a red.
  const signals = world.scenery?.signals ?? [];
  const signalPhase = index => { const t0 = (state.time + index * 7.3) % 26; return t0 < 15 ? "green" : t0 < 18 ? "amber" : "red"; };
  let signalLamps = null;
  if (signals.length) {
    signalLamps = new InstancedMesh(new SphereGeometry(0.3, 8, 6), new MeshBasicMaterial({ color: 0xffffff }), signals.length);
    signalLamps.frustumCulled = false;
    const matrix = new Matrix4();
    signals.forEach((signal, index) => { signalLamps.setMatrixAt(index, matrix.makeTranslation(signal.x, 4.55, signal.z)); signalLamps.setColorAt(index, new Color(0x3cd070)); });
    world.scene.add(signalLamps);
  }
  const lampColors = { green: new Color(0x3cd070), amber: new Color(0xffb429), red: new Color(0xff3b30) };
  function updateSignals() {
    if (!signalLamps) return;
    signals.forEach((signal, index) => { if (Math.abs(signal.s - state.s) < 700) signalLamps.setColorAt(index, lampColors[signalPhase(index)]); });
    signalLamps.instanceColor.needsUpdate = true;
  }
  let freeRoad = false; // test hook: ignore traffic lights and slow traffic so a run can finish quickly
  function signalLimit() {
    if (freeRoad) return Infinity;
    for (const [index, signal] of signals.entries()) {
      const distance = signal.s - 9 - state.s;
      if (distance < -2 || distance > 90) continue;
      const phase = signalPhase(index);
      if (phase === "green") continue;
      if (phase === "amber" && distance < state.speed * 1.3) continue;
      return Math.sqrt(Math.max(0, distance - 1.5) * 2 * 6);
    }
    return Infinity;
  }
  function checkRedLight() {
    for (const [index, signal] of signals.entries()) {
      if (state.s > signal.s - 9 && state.s < signal.s - 9 + state.speed * 0.1 + 0.3 && signalPhase(index) === "red" && state.speed > 3 && state.time - state.redAt > 3) {
        state.redAt = state.time; notify("drive.event.red");
      }
    }
  }
  function checkOncoming() {
    if (state.time - state.bumpAt < 1.5) return;
    for (const v of vehicles) {
      if (v.dir > 0) continue;
      const gap = v.s - state.s;
      if (gap > -v.length && gap < 14 && Math.abs(LANE - state.offset) < 1.9) {
        state.bumpAt = state.time; state.speed = Math.min(state.speed, 4); audio.bump(); notify("drive.event.careful"); return;
      }
    }
  }

  function zoneLimit() {
    const toStop = stopDistance - state.s;
    if (state.pass || state.done) return 40;
    if (toStop < 260) return Math.max(3, Math.sqrt(Math.max(0, toStop - 8)) * 2.1);
    return 40;
  }

  const gateBarriers = () => gates[0] ? (gates[0].barriers ?? [gates[0].barrier]).filter(Boolean) : [];

  // Traffic: a few vehicles live in a window around the car and are respawned ahead when they fall out of it.
  const vehicles = [], fleets = [];
  const paints = [0x3a6ea5, 0xd8d8d8, 0xe0a030, 0x4f8f5a, 0x8a4f9e, 0xc9473b, 0x2f2f33, 0x9fb7c9];
  const pickName = (hd, plain) => kit.has(hd) ? hd : plain;
  for (const [name, count] of [[pickName("car_saga", "car_sedan"), 5], [pickName("car_hatchback_hd", "car_hatchback"), 3], [pickName("van_hd", "car_sedan"), 1],
    [pickName("bus_hd", "bus"), 2], [pickName("truck_hd", "bus"), 1], [pickName("motorbike_hd", "motorbike"), 3]]) {
    const model = kit.get(name);
    if (!model) continue;
    const list = [];
    for (let i = 0; i < (lowEnd ? Math.max(1, Math.ceil(count / 2)) : count); i++) {
      const vehicle = { name, dir: i % 3 === 0 ? -1 : 1, speed: (name === "bus" ? 10 : name === "motorbike" ? 17 : 12 + (i % 4) * 2.5) + i * 0.1,
        length: model.size.z, color: /bus|truck|van/.test(name) ? 0xf4f4f0 : paints[(i + vehicles.length) % paints.length], s: 0, x: 0, z: 0, yaw: 0 };
      respawn(vehicle, i);
      list.push(vehicle); vehicles.push(vehicle);
    }
    const instanced = instanceModel(model, list.map(v => ({ x: v.x, z: v.z, yaw: v.yaw, y: 0.12, color: v.color })), { dynamic: true });
    for (const mesh of instanced.meshes) world.scene.add(mesh);
    fleets.push({ list, instanced });
  }
  function respawn(vehicle, seed = Math.random() * 100) {
    const jitter = (seed * 37.7) % 1;
    vehicle.s = state.s + (vehicle.dir > 0 ? 140 + jitter * 340 : 220 + jitter * 280);
    place(vehicle);
  }
  function place(vehicle) {
    const pose = sample(route, vehicle.s, vehicle.dir > 0 ? -LANE : LANE);
    vehicle.x = pose.x; vehicle.z = pose.z; vehicle.yaw = pose.heading + (vehicle.dir > 0 ? 0 : Math.PI);
  }
  function updateTraffic(dt) {
    for (const vehicle of vehicles) {
      vehicle.s += vehicle.dir * vehicle.speed * dt;
      if (vehicle.s < state.s - 130 || vehicle.s > state.s + 540 || vehicle.s > route.length - 40) respawn(vehicle);
      else place(vehicle);
    }
    for (const { list, instanced } of fleets) instanced.write(list.map(v => ({ x: v.x, z: v.z, yaw: v.yaw, y: 0.12, color: v.color })));
  }
  function trafficAhead() {
    let allowed = null;
    if (freeRoad) return allowed;
    for (const vehicle of vehicles) {
      if (vehicle.dir < 0) continue;
      const gap = vehicle.s - state.s - vehicle.length;
      if (gap > 0 && gap < 28 && Math.abs(-LANE - state.offset) < 2.4) allowed = Math.min(allowed ?? Infinity, Math.max(0, vehicle.speed - (28 - gap) * 0.2));
    }
    return allowed;
  }

  function render(now) {
    const pose = sample(route, state.s, state.offset);
    car.position.set(pose.x, 0.12, pose.z);
    car.rotation.y = pose.heading + state.yaw * -1;
    // Wheels roll with the distance driven and the front pair follows the steering.
    wheels.spin = (wheels.spin ?? 0) + state.speed * frameDt / wheels.radius;
    for (const wheel of wheels.all) wheel.rotation.x = -wheels.spin;
    for (const wheel of wheels.front) wheel.rotation.y = -state.yaw * 1.4;
    // Chase camera: behind the car along its own heading, so it follows steering and lane changes.
    const carYaw = car.rotation.y;
    let turn = carYaw - cameraTarget.yaw;
    while (turn > Math.PI) turn -= 2 * Math.PI;
    while (turn < -Math.PI) turn += 2 * Math.PI;
    const follow = 1 - Math.exp(-frameDt * 4.5);
    const unsnappedWanted = { x: pose.x - Math.sin(cameraTarget.yaw) * 12.5, z: pose.z - Math.cos(cameraTarget.yaw) * 12.5 };
    const jumped = !cameraTarget.ready || Math.hypot(unsnappedWanted.x - cameraTarget.x, unsnappedWanted.z - cameraTarget.z) > 40; // a jump, not a drive
    if (jumped) { cameraTarget.ready = true; cameraTarget.yaw = carYaw; } else cameraTarget.yaw += turn * follow;
    const sinYaw = Math.sin(cameraTarget.yaw), cosYaw = Math.cos(cameraTarget.yaw);
    const wanted = { x: pose.x - sinYaw * 12.5, z: pose.z - cosYaw * 12.5 };
    if (jumped) { cameraTarget.x = wanted.x; cameraTarget.z = wanted.z; }
    else { const glide = 1 - Math.exp(-frameDt * 7); cameraTarget.x += (wanted.x - cameraTarget.x) * glide; cameraTarget.z += (wanted.z - cameraTarget.z) * glide; }
    const wobble = reduced.matches ? 0 : Math.sin(now / 400) * 0.03;
    world.scenery?.update(state.s);
    world.camera.position.set(cameraTarget.x, 5.2 + wobble, cameraTarget.z);
    // Look past the car along the camera heading, glancing at the landmark near the start and the end of the trip.
    let look = { x: pose.x + sinYaw * 22, y: 1.7, z: pose.z + cosYaw * 22 };
    for (const focus of world.focuses) {
      const t = focus.rising ? clamp((state.s - focus.from) / (focus.to - focus.from), 0, 1) : clamp(1 - (state.s - focus.from) / (focus.to - focus.from), 0, 1);
      const w = t * focus.weight;
      look = { x: look.x + (focus.x - look.x) * w, y: look.y + (focus.y - look.y) * w, z: look.z + (focus.z - look.z) * w };
    }
    world.camera.lookAt(look.x, look.y, look.z);
    const hour = tripHour(route, state.s);
    world.setHour(hour);
    world.renderer.render(world.scene, world.camera);
    speedLabel.textContent = String(Math.round(state.speed * 3.6));
    const road = roadAt(route, state.s);
    roadLabel.textContent = road.name.replace(/\s*\(.*\)$/, "");
    progressBar.firstElementChild.style.width = `${(state.s / route.length * 100).toFixed(1)}%`;
    progressBar.setAttribute("aria-valuenow", String(Math.round(state.s / route.length * 100)));
    const hh = Math.floor(hour), mm = Math.floor((hour - hh) * 60);
    tripLabel.textContent = `${t("drive.clock")} ${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")} · ${(state.s / 1000).toFixed(1)} / ${(route.length / 1000).toFixed(1)} km`;
    if (now - minimapAt > 250) { minimapAt = now; drawMinimap(); }
  }

  function resize() {
    const { clientWidth, clientHeight } = stage;
    if (clientWidth && clientHeight) world.resize(clientWidth, clientHeight);
  }
  const observer = new ResizeObserver(resize);
  observer.observe(stage);
  resize();
  stage.inspectDrive = () => ({
    car: { x: car.position.x, z: car.position.z, yaw: car.rotation.y }, camera: { x: world.camera.position.x, z: world.camera.position.z },
    quality: governor.ratio, pedestrians: pedestrians?.count ?? 0, driver: car.children.includes(driverBody), s: state.s, speed: state.speed, mode, stage: state.stage, paused, offset: state.offset,
    road: roadAt(route, state.s).name, length: route.length, stop: stopDistance, hour: tripHour(route, state.s),
    triangles: world.renderer.info.render.triangles, calls: world.renderer.info.render.calls,
  });
  stage.driveTo = distance => { state.s = clamp(distance, 0, route.length); };
  stage.freeRoad = () => { freeRoad = true; };
  stage.skipCheckpoint = () => { state.pass = true; gateBarriers().forEach(barrier => { barrier.rotation.z = 1.4; }); }; // for tests and screenshots
  stage.dataset.state = "ready";
  stage.setAttribute("aria-busy", "false");
  stage.querySelector(".drive-loading").remove();
  root.querySelector(".drive-poster").remove();
  hud.hidden = false;
  frame = requestAnimationFrame(step);
  void findRoad;

  const driverScenes = new Set();
  let driverBody = null;
  (async () => {
    try {
      const url = name => driverUrls[`../../models/chibi-dressup/bodies/male/${name}.glb`];
      const [body, motion, gestures] = await loadModels(["body", "motion", "gestures"].map(url), signal, driverScenes);
      if (signal.aborted) return;
      let skeleton;
      body.scene.traverse(node => { if (node.isSkinnedMesh) { skeleton = node.skeleton; node.frustumCulled = false; } });
      const rig = createRig(body.scene, skeleton, [motion], gestures.animations);
      rig.select("sit");
      for (let i = 0; i < 4; i++) rig.update(0.5, { L: "grip_small", R: "grip_small" }); // sit down, settle, hold the wheel
      const seat = playerName === "car_saga" ? [-0.42, 0.3, -0.05] : playerName ? [-0.4, 0.34, 0.1] : [-0.38, 0.28, -0.3];
      body.scene.scale.setScalar(playerName === "car_saga" ? 0.6 : playerName ? 0.66 : 0.72);
      body.scene.position.set(...seat);
      car.getObjectByName("driver-placeholder")?.removeFromParent();
      car.add(body.scene);
      driverBody = body.scene;
    } catch (error) {
      console.error("Drive: chibi driver failed to load", error);
    }
  })();

  let pedestrians = null;
  if (world.kitMode) {
    const touch = matchMedia("(pointer: coarse)").matches;
    addPedestrians({ scene: world.scene, route, signal, count: touch ? { female: 1, male: 0 } : { female: 1, male: 1 } })
      .then(result => { if (signal.aborted) result.dispose(); else pedestrians = result; })
      .catch(error => { if (!signal.aborted) console.error("Drive: pedestrians failed to load", error); });
  }

  return {
    dispose() {
      running = false;
      pedestrians?.dispose();
      audio.dispose();
      cancelAnimationFrame(frame);
      observer.disconnect();
      delete stage.inspectDrive;
      disposeModels(driverScenes);
      disposeModels(kitScenes);
      world.dispose();
    },
  };
}
