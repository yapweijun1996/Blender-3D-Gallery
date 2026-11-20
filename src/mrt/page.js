import {
  AmbientLight, BoxGeometry, Color, DirectionalLight, Fog, Group, HemisphereLight, InstancedMesh, Matrix4, Mesh, MeshLambertMaterial, PerspectiveCamera, Scene, Vector3, WebGLRenderer,
} from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { localize, mountMarkup, t } from "../i18n/index.js";
import { disposeModels } from "../chibi-dressup/view.js";
import { createDriveAudio } from "../drive/audio.js";
import { cloneModel, loadKitFrom } from "../drive/kit.js";
import { createQualityGovernor } from "../drive/quality.js";
import { createPeople } from "../drive/pedestrians.js";
import { passengerPose } from "./passengers.js";
import { trainState } from "./schedule.js";
import "../drive/style.css";

// A Singapore MRT platform built from the gallery's MRT kit: a train comes in, stops at the screen doors, the doors open,
// it waits and leaves. Platform along X, the track at +Z, the train three carriages long.
const urls = import.meta.glob("../../models/sg-{mrt-platform,mrt-carriage,platform-screen-door,fare-gate,station-sign,route-map}/*.glb", { eager: true, query: "?url", import: "default" });
const KIT = ["mrt-platform", "mrt-carriage", "platform-screen-door", "fare-gate", "station-sign", "route-map"];
const CARRIAGES = 3, CARRIAGE_PITCH = 20.7;
const TRACK_Z = 4.2, DECK = 1.15, WHEEL_RADIUS = 0.43;
const PLATFORM_EDGE_Z = 2.2;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const VIEWS = {
  platform: { position: [7, 2.6, -1.4], target: [0, 1.7, TRACK_Z] },
  overview: { position: [-30, 4.2, 7.4], target: [0, 1.8, 0] },
};

export async function mountMrt(root, thumbnail, signal) {
  mountMarkup(root, `<section class="drive">
    <header class="drive-heading">
      <h1 data-i18n="demo.sg-mrt.title"></h1>
      <p data-i18n="demo.sg-mrt.description"></p>
    </header>
    <div class="drive-stage mrt-stage" data-state="loading" aria-busy="true">
      <img class="drive-poster" alt="">
      <p class="drive-loading" role="status" data-i18n="mrt.loading"></p>
      <div class="drive-hud" hidden>
        <p class="drive-road mrt-status" aria-live="polite"></p>
        <p class="drive-trip mrt-next"></p>
      </div>
    </div>
    <div class="drive-controls" role="group">
      <div class="drive-modes" role="group">
        <button type="button" data-view="platform" aria-pressed="true" data-i18n="mrt.view.platform"></button>
        <button type="button" data-view="inside" aria-pressed="false" data-i18n="mrt.view.inside"></button>
        <button type="button" data-view="overview" aria-pressed="false" data-i18n="mrt.view.overview"></button>
      </div>
      <button type="button" class="drive-pause" data-i18n="common.pause"></button>
      <button type="button" class="drive-sound" aria-pressed="true" data-i18n="drive.sound"></button>
    </div>
    <p class="drive-hint" data-i18n="mrt.hint"></p>
    <p class="drive-credit" data-i18n="mrt.credit"></p>
  </section>`);
  const stage = root.querySelector(".drive-stage");
  for (const [name, value] of Object.entries({
    "--drive-sky": "#10151c", "--drive-ink": "#ffffff", "--drive-gold": "#ffd36a", "--drive-on-gold": "#1c1c1c",
    "--drive-line": "rgba(255,255,255,.3)", "--drive-shadow": "rgba(0,0,0,.7)", "--drive-panel-soft": "rgba(8,14,28,.55)",
    "--drive-panel": "rgba(10,18,36,.92)", "--drive-good": "rgba(70,170,100,.85)",
  })) root.querySelector(".drive").style.setProperty(name, value);
  root.querySelector(".drive-poster").src = thumbnail;
  const statusLabel = stage.querySelector(".mrt-status"), nextLabel = stage.querySelector(".mrt-next");
  localize(root.querySelector(".drive-controls"), "mrt.controls", undefined, "aria-label");

  const scenes = new Set();
  const kit = await loadKitFrom(KIT.map(name => [name, urls[`../../models/sg-${name}/sg-${name}.glb`]]), signal, scenes);
  signal.throwIfAborted();

  const scene = new Scene();
  scene.background = new Color(0x10151c);
  scene.fog = new Fog(0x10151c, 60, 240);
  scene.add(new HemisphereLight(0xe8f0ff, 0x3a3f46, 1.9), new AmbientLight(0xffffff, 0.5));
  const lamp = new DirectionalLight(0xffffff, 1.6);
  lamp.position.set(-10, 14, -6);
  scene.add(lamp);

  const camera = new PerspectiveCamera(58, 1, 0.1, 400);
  const renderer = new WebGLRenderer({ antialias: true, powerPreference: "high-performance" });
  const touchDevice = matchMedia("(pointer: coarse)").matches;
  renderer.setPixelRatio(Math.min(devicePixelRatio, touchDevice ? 1.5 : 2));
  renderer.domElement.setAttribute("aria-hidden", "true");
  stage.append(renderer.domElement);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.maxPolarAngle = Math.PI * 0.49;
  controls.minDistance = 1.5;
  controls.maxDistance = 70;

  // Station shell: track bed, rails, sleepers, a back wall and a ceiling.
  const concrete = new MeshLambertMaterial({ color: 0x5b5f66 }), steel = new MeshLambertMaterial({ color: 0x9aa0a8 }), tunnel = new MeshLambertMaterial({ color: 0x23272d });
  const bed = new Mesh(new BoxGeometry(400, 0.2, 7.4), concrete);
  bed.position.set(0, -0.2, TRACK_Z);
  scene.add(bed);
  for (const side of [-0.75, 0.75]) {
    const rail = new Mesh(new BoxGeometry(400, 0.16, 0.08), steel);
    rail.position.set(0, 0.03, TRACK_Z + side);
    scene.add(rail);
  }
  const sleepers = new InstancedMesh(new BoxGeometry(0.22, 0.08, 2.4), new MeshLambertMaterial({ color: 0x3b3d40 }), 330);
  const matrix = new Matrix4();
  for (let i = 0; i < 330; i++) { matrix.makeTranslation(-98.5 + i * 0.6, -0.04, TRACK_Z); sleepers.setMatrixAt(i, matrix); }
  scene.add(sleepers);
  const wall = new Mesh(new BoxGeometry(400, 9, 0.4), tunnel);
  wall.position.set(0, 4.3, TRACK_Z + 4.5);
  scene.add(wall);
  const ceiling = new Mesh(new BoxGeometry(400, 0.3, 14), tunnel);
  ceiling.position.set(0, 7.4, TRACK_Z - 1);
  scene.add(ceiling);

  const place = (name, x, y, z, yaw = 0) => {
    const copy = cloneModel(kit.get(name));
    copy.position.set(x, y, z);
    copy.rotation.y = yaw;
    scene.add(copy);
    return copy;
  };
  if (kit.has("mrt-platform")) place("mrt-platform", 0, 0, 0);

  // The train: carriages along X (yaw 90 degrees turns the carriage's +Z nose to +X and its right-hand doors towards the platform).
  const carriages = [];
  if (kit.has("mrt-carriage")) {
    for (let i = 0; i < CARRIAGES; i++) {
      const group = place("mrt-carriage", 0, -0.05, TRACK_Z, Math.PI / 2);
      const doors = [], wheels = [];
      group.traverse(node => {
        if (/^door_R/.test(node.name)) doors.push({ node, base: node.position.z, stroke: node.userData.openTranslationMeters?.[2] ?? 0 });
        if (/^wheel_/.test(node.name)) { node.rotation.order = "YXZ"; wheels.push(node); }
      });
      carriages.push({ group, doors, wheels, offset: (i - (CARRIAGES - 1) / 2) * CARRIAGE_PITCH });
    }
  }

  // Platform screen doors at every doorway of the stopped train, fixed panels between them.
  const screenDoors = [];
  if (kit.has("platform-screen-door")) {
    const doorwayXs = carriages.flatMap(carriage => [carriage.offset - 3.4, carriage.offset + 3.4]);
    for (const x of doorwayXs) {
      const group = place("platform-screen-door", x, DECK, PLATFORM_EDGE_Z);
      const leaves = [];
      group.traverse(node => { if (/^leaf_/.test(node.name)) leaves.push({ node, base: node.position.x, stroke: node.userData.openTranslationMeters?.[0] ?? 0 }); });
      screenDoors.push(leaves);
    }
    for (let x = -58.5; x <= 58.5; x += 3) {
      if (doorwayXs.some(doorway => Math.abs(doorway - x) < 3.1)) continue;
      place("platform-screen-door", x, DECK, PLATFORM_EDGE_Z);
    }
  }
  // Fare gates and signs at the far end of the platform.
  if (kit.has("fare-gate")) for (let i = 0; i < 4; i++) place("fare-gate", -38 + i * 2.2, DECK, -2.0, Math.PI);
  if (kit.has("station-sign")) { place("station-sign", 0, DECK + 2.6, -2.3, Math.PI); place("station-sign", -30, DECK + 2.6, -2.3, Math.PI); place("station-sign", 30, DECK + 2.6, -2.3, Math.PI); }
  if (kit.has("route-map")) for (const x of [-12, 12]) place("route-map", x, DECK + 1.0, -2.4, Math.PI);

  // Passengers: the dress-up chibis, loaded after the first frame; each follows passengerPose(index, clock).
  let passengers = null;
  createPeople({ scene, signal, count: touchDevice ? { female: 2, male: 1 } : { female: 3, male: 3 }, seed: 9 })
    .then(result => { if (signal.aborted) disposeModels(result.scenes); else { passengers = result; for (const person of passengers.people) { person.clip = null; person.root.visible = false; } } })
    .catch(error => { if (!signal.aborted) console.error("MRT: passengers failed to load", error); });

  let view = "platform", paused = false, clock = 0;
  const audio = createDriveAudio();
  let lastPhase = null, soundOn = true;
  const setView = name => {
    view = name;
    for (const button of root.querySelectorAll("[data-view]")) button.setAttribute("aria-pressed", String(button.dataset.view === name));
    if (name !== "inside") {
      const preset = VIEWS[name];
      camera.position.set(...preset.position);
      controls.target.set(...preset.target);
      controls.enabled = true;
    } else controls.enabled = false;
  };
  for (const button of root.querySelectorAll("[data-view]")) button.addEventListener("click", () => setView(button.dataset.view));
  const pauseButton = root.querySelector(".drive-pause");
  pauseButton.addEventListener("click", () => { paused = !paused; localize(pauseButton, paused ? "common.play" : "common.pause"); });
  const soundButton = root.querySelector(".drive-sound");
  soundButton.addEventListener("click", () => { soundOn = !soundOn; audio.enabled = soundOn; audio.start(); soundButton.setAttribute("aria-pressed", String(soundOn)); });
  for (const name of ["pointerdown", "keydown"]) addEventListener(name, () => audio.start(), { signal, passive: true });
  setView("platform");

  const eye = new Vector3(), ahead = new Vector3();
  function apply(state) {
    for (const carriage of carriages) {
      carriage.group.position.x = state.x + carriage.offset;
      for (const door of carriage.doors) door.node.position.z = door.base + door.stroke * state.doors;
    }
    for (const leaves of screenDoors) for (const leaf of leaves) leaf.node.position.x = leaf.base + leaf.stroke * state.doors;
  }
  let wheelAngle = 0;
  function spinWheels(state, dt) {
    wheelAngle += state.speed * dt / WHEEL_RADIUS;
    for (const carriage of carriages) for (const wheel of carriage.wheels) wheel.rotation.x = wheelAngle;
  }
  const phaseKeys = { arriving: "mrt.status.arriving", opening: "mrt.status.doors", boarding: "mrt.status.boarding", closing: "mrt.status.closing", departing: "mrt.status.departing", waiting: "mrt.status.waiting" };

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
  const governor = createQualityGovernor({ initial: Math.min(devicePixelRatio, touchDevice ? 1.5 : 2), onChange: ratio => { renderer.setPixelRatio(ratio); resize(); } });

  let frame = 0, last = performance.now(), running = true;
  function step(now) {
    if (!running) return;
    frame = requestAnimationFrame(step);
    governor.update(now);
    const dt = clamp((now - last) / 1000, 0, 0.1);
    last = now;
    if (!paused) clock += dt;
    const state = trainState(clock);
    apply(state);
    spinWheels(state, paused ? 0 : dt);
    if (view === "inside" && carriages[1]) {
      // Stand in the middle carriage, looking along the aisle towards the front of the train.
      const middle = carriages[1].group;
      eye.set(middle.position.x - 3.5, 1.75 - 0.05 + 0.2, middle.position.z - 0.2);
      ahead.set(middle.position.x + 8, 1.6, middle.position.z);
      camera.position.copy(eye);
      camera.lookAt(ahead);
    } else controls.update();
    if (passengers) {
      passengers.people.forEach((person, index) => {
        const pose = passengerPose(index, clock);
        person.root.visible = pose.visible;
        if (!pose.visible) return;
        if (person.clip !== pose.clip) { person.rig.select(pose.clip); person.clip = pose.clip; }
        person.rig.update(paused ? 0 : dt, { L: null, R: null });
        person.root.position.set(pose.x, DECK, pose.z);
        person.root.rotation.y = pose.heading;
      });
    }
    statusLabel.textContent = t(phaseKeys[state.phase]);
    nextLabel.textContent = state.phase === "arriving" ? t("mrt.next", { seconds: Math.ceil(state.remaining) }) : "";
    if (state.phase === "opening" && lastPhase !== "opening") audio.beep();
    lastPhase = state.phase;
    audio.update(Math.min(state.speed, 25), 0.2);
    renderer.render(scene, camera);
  }
  stage.querySelector(".drive-hud").hidden = false;
  stage.dataset.state = "ready";
  stage.removeAttribute("aria-busy");
  stage.querySelector(".drive-loading").hidden = true;
  stage.querySelector(".drive-poster").hidden = true;
  frame = requestAnimationFrame(step);

  stage.inspectMrt = () => ({ phase: trainState(clock).phase, clock, x: carriages[1]?.group.position.x ?? null, doors: trainState(clock).doors, calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, carriages: carriages.length, people: passengers ? passengers.people.filter(person => person.root.visible).length : 0, loadedPeople: passengers ? passengers.people.length : 0, screenDoors: screenDoors.length, view });
  stage.setClock = value => { clock = value; };

  return {
    dispose() {
      running = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      controls.dispose();
      audio.dispose();
      if (passengers) { for (const person of passengers.people) person.rig.dispose(); disposeModels(passengers.scenes); }
      scene.traverse(node => { node.geometry?.dispose(); for (const m of [node.material].flat().filter(Boolean)) { m.map?.dispose(); m.dispose(); } });
      disposeModels(scenes);
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    },
  };
}
