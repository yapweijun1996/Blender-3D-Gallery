import { localize, mountMarkup, t, onLanguageChange } from "../i18n/index.js";
import routeData from "../../models/drive/route-mbs-jb.json";
import { buildRoute, findRoad, roadAt, sample, tripHour } from "./route.js";
import { createRig } from "../chibi-dressup/rig.js";
import { disposeModels, loadModels } from "../chibi-dressup/view.js";
import { cloneModel, instanceModel, loadKit } from "./kit.js";
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
        </div>
      </div>
    </div>
    <div class="drive-controls" role="group">
      <div class="drive-modes" role="group">
        <button type="button" data-mode="auto" data-i18n="drive.mode.auto"></button>
        <button type="button" data-mode="manual" data-i18n="drive.mode.manual"></button>
      </div>
      <button type="button" class="drive-pause" data-i18n="common.pause"></button>
      <div class="drive-pad" aria-hidden="true">
        <button type="button" data-key="left">◀</button>
        <button type="button" data-key="brake">■</button>
        <button type="button" data-key="gas">▲</button>
        <button type="button" data-key="right">▶</button>
      </div>
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
  stampZone.style.left = `${STAMP_ZONE[0] * 100}%`;
  stampZone.style.width = `${(STAMP_ZONE[1] - STAMP_ZONE[0]) * 100}%`;

  const reduced = matchMedia("(prefers-reduced-motion: reduce)");
  let mode = "auto", paused = false;
  try { mode = localStorage.getItem("drive-jb-mode") === "manual" ? "manual" : "auto"; } catch { /* Use auto. */ }
  const kitScenes = new Set();
  const kit = await loadKit(signal, kitScenes).catch(error => { if (signal.aborted) throw error; console.error("Drive: model kit failed to load", error); return new Map(); });
  const world = buildWorld(stage, route, kit);
  const car = kit.has("car_hatchback") ? cloneModel(kit.get("car_hatchback"), 0xd9453a) : buildCar();
  world.scene.add(car);
  const { stop: stopDistance, gates } = world.landmarks;
  const state = { s: 0, speed: 0, offset: -LANE, yaw: 0, stage: "drive", pass: false, stamp: 0, stampDir: 1, done: false, time: 0 };
  const keys = new Set();
  const cameraTarget = { x: 0, y: 0, z: 0 };

  function localizeAll() {
    localize(pauseButton, paused ? "common.play" : "common.pause");
    for (const button of modeButtons) button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  onLanguageChange(() => { renderPassport(); localizeAll(); }, signal);
  localizeAll();

  function setMode(next) {
    mode = next;
    try { localStorage.setItem("drive-jb-mode", mode); } catch { /* Not saved. */ }
    localizeAll();
  }
  for (const button of modeButtons) button.addEventListener("click", () => setMode(button.dataset.mode));
  pauseButton.addEventListener("click", () => { paused = !paused; localizeAll(); });

  const keyOf = event => ({ ArrowLeft: "left", a: "left", A: "left", ArrowRight: "right", d: "right", D: "right",
    ArrowUp: "gas", w: "gas", W: "gas", ArrowDown: "brake", s: "brake", S: "brake" })[event.key];
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
      state.stage = "gate";
      passport.hidden = true;
    } else {
      passportText.textContent = t("drive.passport.again");
    }
  });
  stage.querySelector(".drive-replay").addEventListener("click", () => {
    Object.assign(state, { s: 0, speed: 0, offset: -LANE, yaw: 0, stage: "drive", pass: false, done: false });
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
  function step(now) {
    if (!running) return;
    frame = requestAnimationFrame(step);
    // requestAnimationFrame stamps can precede the mount time, so never let time run backwards.
    const dt = clamp((now - last) / 1000, 0, 0.05);
    last = now;
    if (!paused) update(dt);
    render(now);
  }

  function update(dt) {
    state.time += dt;
    const limit = zoneLimit();
    if (state.stage === "drive") {
      if (mode === "auto") {
        const target = Math.min(CRUISE, limit);
        state.speed += clamp(target - state.speed, -14 * dt, 5 * dt);
        state.offset += (-LANE - state.offset) * Math.min(1, dt * 2);
        state.yaw += (0 - state.yaw) * Math.min(1, dt * 4);
      } else {
        const gas = keys.has("gas") ? 1 : 0, brake = keys.has("brake") ? 1 : 0;
        state.speed += (gas * 7 - brake * 16 - (gas ? 0 : 2.5)) * dt;
        state.speed = clamp(state.speed, 0, Math.min(TOP, limit * 1.25));
        const steer = (keys.has("right") ? 1 : 0) - (keys.has("left") ? 1 : 0);
        state.yaw = clamp(state.yaw + (steer * 1.8 - state.yaw * 1.4) * dt, -0.45, 0.45);
        state.offset += Math.sin(state.yaw) * state.speed * dt * -1;
        const edge = ROAD_HALF_WIDTH - 1.2;
        if (Math.abs(state.offset) > edge) { state.offset = clamp(state.offset, -edge, edge); state.speed *= 1 - Math.min(1, dt * 3); state.yaw *= 0.5; }
      }
      state.speed = Math.max(0, state.speed);
      const slow = trafficAhead();
      if (slow !== null) state.speed = Math.min(state.speed, slow);
      state.s += state.speed * Math.cos(state.yaw) * dt;
      if (state.s >= stopDistance - 6 && state.stage === "drive" && !state.pass && !state.done) {
        state.s = Math.min(state.s, stopDistance - 6);
        state.speed = Math.max(0, state.speed - 20 * dt);
        if (state.speed < 0.2) { state.stage = "passport"; state.speed = 0; renderPassport(); }
      }
      if (state.s >= route.length - 25) {
        state.s = route.length - 25; state.speed = Math.max(0, state.speed - 18 * dt);
        if (state.speed < 0.2 && !state.done) { state.done = true; state.stage = "arrived"; arrival.hidden = false; }
      }
    } else if (state.stage === "passport" && state.pass) {
      state.stamp += state.stampDir * dt * 0.75;
      if (state.stamp > 1) { state.stamp = 1; state.stampDir = -1; }
      if (state.stamp < 0) { state.stamp = 0; state.stampDir = 1; }
      stampMarker.style.left = `${state.stamp * 100}%`;
    } else if (state.stage === "gate") {
      const barriers = gateBarriers();
      for (const barrier of barriers) barrier.rotation.z = Math.min(1.4, barrier.rotation.z + dt * 1.6);
      if (!barriers.length || barriers[0].rotation.z >= 1.4) { state.stage = "drive"; state.pass = true; }
    }
    updateTraffic(dt);
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
  for (const [name, count] of [["car_hatchback", 9], ["car_sedan", 6], ["bus", 3], ["motorbike", 4]]) {
    const model = kit.get(name);
    if (!model) continue;
    const list = [];
    for (let i = 0; i < count; i++) {
      const vehicle = { name, dir: i % 3 === 0 ? -1 : 1, speed: (name === "bus" ? 10 : name === "motorbike" ? 17 : 12 + (i % 4) * 2.5) + i * 0.1,
        length: model.size.z, color: paints[(i + vehicles.length) % paints.length], s: 0, x: 0, z: 0, yaw: 0 };
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
    const back = sample(route, Math.max(0, state.s - 13), state.offset * 0.6);
    const ahead = sample(route, state.s + 22, state.offset * 0.3);
    const wobble = reduced.matches ? 0 : Math.sin(now / 400) * 0.03;
    cameraTarget.x += (back.x - cameraTarget.x) * 0.12;
    cameraTarget.z += (back.z - cameraTarget.z) * 0.12;
    if (Math.hypot(back.x - cameraTarget.x, back.z - cameraTarget.z) > 40) { cameraTarget.x = back.x; cameraTarget.z = back.z; } // a jump, not a drive
    world.scenery?.update(state.s);
    world.camera.position.set(cameraTarget.x, 5.4 + wobble, cameraTarget.z);
    world.camera.lookAt(ahead.x, 1.6, ahead.z);
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
    driver: car.children.includes(driverBody), s: state.s, speed: state.speed, mode, stage: state.stage, paused, offset: state.offset,
    road: roadAt(route, state.s).name, length: route.length, stop: stopDistance, hour: tripHour(route, state.s),
    triangles: world.renderer.info.render.triangles, calls: world.renderer.info.render.calls,
  });
  stage.driveTo = distance => { state.s = clamp(distance, 0, route.length); };
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
      const seat = kit.has("car_hatchback") ? [-0.4, 0.34, 0.1] : [-0.38, 0.28, -0.3];
      body.scene.scale.setScalar(kit.has("car_hatchback") ? 0.66 : 0.72);
      body.scene.position.set(...seat);
      car.getObjectByName("driver-placeholder")?.removeFromParent();
      car.add(body.scene);
      driverBody = body.scene;
    } catch (error) {
      console.error("Drive: chibi driver failed to load", error);
    }
  })();

  return {
    dispose() {
      running = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      delete stage.inspectDrive;
      disposeModels(driverScenes);
      disposeModels(kitScenes);
      world.dispose();
    },
  };
}
