import profile from "../../../scripts/world/fort-canning-tunnel.json" with { type: "json" };
import { localize, mountMarkup } from "../../i18n/index.js";
import { disposeModels } from "../../chibi-dressup/view.js";
import { cloneModel, loadKitFrom } from "../../drive/kit.js";
import { createPhysicsWorld, FIXED_DT } from "../physics/world.js";
import { installTunnelColliders } from "./colliders.js";
import { createTunnelGeometry, nearestTunnelSection } from "./geometry.js";
import { createTunnelScene } from "./scene.js";
import "./style.css";

const carUrl = new URL("../../../models/drive/kit/car_saga.glb", import.meta.url).href;
const keyMap = { arrowup: "gas", w: "gas", arrowdown: "brake", s: "brake", arrowleft: "left", a: "left", arrowright: "right", d: "right" };

function bindControls(root, signal) {
  const keys = new Map(), pointers = new Map();
  const clear = () => { keys.clear(); pointers.clear(); };
  addEventListener("keydown", event => {
    const key = event.key.toLowerCase(), action = keyMap[key];
    if (!action || event.target.closest?.("input, textarea, select")) return;
    event.preventDefault();
    keys.set(key, action);
  }, { signal });
  addEventListener("keyup", event => keys.delete(event.key.toLowerCase()), { signal });
  addEventListener("blur", clear, { signal });
  for (const button of root.querySelectorAll("[data-key]")) {
    const action = button.dataset.key;
    localize(button, `drive.key.${action}`, undefined, "aria-label");
    button.addEventListener("pointerdown", event => {
      if (event.button !== 0) return;
      event.preventDefault();
      button.setPointerCapture(event.pointerId);
      pointers.set(event.pointerId, action);
    }, { signal });
    for (const type of ["pointerup", "pointercancel", "lostpointercapture"]) {
      button.addEventListener(type, event => pointers.delete(event.pointerId), { signal });
    }
  }
  return { clear, held: action => [...keys.values(), ...pointers.values()].includes(action) };
}

export async function mountTunnelPrototype(root, thumbnail, signal) {
  mountMarkup(root, `<section class="drive tunnel-preview">
    <header class="drive-heading">
      <h1 data-i18n="world.tunnel.title"></h1>
      <p data-i18n="world.tunnel.description"></p>
    </header>
    <div class="drive-stage tunnel-stage" data-state="loading" aria-busy="true">
      <img class="drive-poster" alt="">
      <p class="drive-loading" role="status" data-i18n="world.loading"></p>
      <div class="drive-hud" hidden>
        <div class="drive-readout"><strong class="drive-speed">0</strong><span data-i18n="drive.kmh"></span></div>
        <p class="tunnel-status" role="status"></p>
        <progress class="tunnel-progress" max="1" value="0" data-i18n-aria-label="world.tunnel.progress"></progress>
        <div class="drive-pad">
          <div class="drive-steer"><button type="button" data-key="left">◀</button><button type="button" data-key="right">▶</button></div>
          <div class="drive-pedals"><button type="button" data-key="brake">■</button><button type="button" data-key="gas">▲</button></div>
        </div>
      </div>
    </div>
    <div class="drive-controls" role="group" data-i18n-aria-label="drive.controls">
      <button type="button" class="outline-button tunnel-pause" data-i18n="common.pause"></button>
      <button type="button" class="outline-button tunnel-reset" data-i18n="world.tunnel.reset"></button>
      <a class="outline-button" href="?page=sg-world" data-page="sg-world" data-i18n="world.tunnel.back"></a>
    </div>
    <p class="drive-hint tunnel-keyboard-hint" data-i18n="world.tunnel.hint"></p>
    <a class="drive-credit" href="https://www.openstreetmap.org/copyright" data-i18n="world.tunnel.credit"></a>
  </section>`);
  const stage = root.querySelector(".tunnel-stage");
  const poster = stage.querySelector(".drive-poster"), loading = stage.querySelector(".drive-loading");
  const hud = stage.querySelector(".drive-hud"), status = stage.querySelector(".tunnel-status");
  const speedLabel = stage.querySelector(".drive-speed"), progress = stage.querySelector(".tunnel-progress");
  const pause = root.querySelector(".tunnel-pause"), reset = root.querySelector(".tunnel-reset");
  poster.src = thumbnail;
  const input = bindControls(root, signal);
  const kitScenes = new Set();
  let physics, unloadColliders, scene, frameId, snapshot, readSnapshot, disposed = false;

  function dispose() {
    if (disposed) return;
    disposed = true;
    cancelAnimationFrame(frameId);
    if (window.render_game_to_text === readSnapshot) delete window.render_game_to_text;
    scene?.dispose();
    unloadColliders?.();
    physics?.dispose();
    disposeModels(kitScenes);
  }

  try {
    signal.throwIfAborted();
    const kit = await loadKitFrom([["car", carUrl]], signal, kitScenes);
    signal.throwIfAborted();
    physics = await createPhysicsWorld();
    signal.throwIfAborted();
    const geometry = createTunnelGeometry(profile);
    const start = geometry.sections.find(({ s }) => s >= -18);
    const spawn = { position: { x: start.x, y: 1.45, z: start.z }, heading: Math.atan2(start.tx, start.tz) };
    unloadColliders = installTunnelColliders(physics, geometry.surfaces);
    if (!kit.has("car")) throw new Error("The tunnel car model did not load");
    const car = cloneModel(kit.get("car"));
    scene = createTunnelScene(stage, profile, geometry, car);
    const vehicle = physics.addVehicle({ ...spawn, type: "sedan", topSpeed: 15 });
    const settle = () => { for (let step = 0; step < 72; step++) physics.step(FIXED_DT); };
    settle();
    const restHeight = vehicle.getState().position.y;
    let paused = false, crossedInterior = false, complete = false, lastPhase, lastTime;

    function draw(dt, snap = false) {
      const state = vehicle.getState();
      const { s, y, lateral } = nearestTunnelSection(geometry.sections, state.position);
      const onRoute = Math.abs(lateral) < profile.width / 2 && Math.abs(state.position.y - y - restHeight) < .85;
      if (onRoute && s >= geometry.coveredFrom && s <= geometry.coveredTo && state.position.y < -3) crossedInterior = true;
      if (onRoute && crossedInterior && s >= profile.length + 12) complete = true;
      const phase = complete ? "complete" : s < 0 ? "approach" : s < geometry.coveredFrom ? "descent"
        : s <= geometry.coveredTo ? "covered" : s < profile.length ? "ascent" : "surface";
      if (phase !== lastPhase) {
        localize(status, `world.tunnel.phase.${phase}`);
        lastPhase = phase;
      }
      speedLabel.textContent = String(Math.round(state.speed * 3.6));
      progress.value = Math.max(0, Math.min(1, s / profile.length));
      scene.draw(state, s, restHeight, dt, snap);
      snapshot = { ready: true, position: state.position, heading: state.heading, speed: state.speed, along: s, lateral, depth: Math.max(0, -y), phase, complete };
    }

    function restart() {
      input.clear();
      crossedInterior = complete = false;
      vehicle.resetUpright({ ...spawn, repair: true });
      settle();
      draw(0, true);
    }

    function frame(time) {
      const dt = (time - (lastTime ?? time)) / 1000;
      lastTime = time;
      if (!paused && !document.hidden) {
        const brake = input.held("brake"), gas = input.held("gas");
        const forward = vehicle.getState().forwardSpeed;
        vehicle.setControls({
          throttle: Number(gas && !brake), brake: Number(brake && (gas || forward > 1)),
          reverse: Number(brake && !gas && forward <= 1), steer: Number(input.held("left")) - Number(input.held("right")),
        });
        physics.step(dt);
        if (vehicle.getState().position.y < -12) restart();
        else draw(dt);
      }
      frameId = requestAnimationFrame(frame);
    }

    pause.addEventListener("click", () => {
      paused = !paused;
      input.clear();
      localize(pause, paused ? "common.play" : "common.pause");
    }, { signal });
    reset.addEventListener("click", restart, { signal });
    draw(0, true);
    readSnapshot = () => JSON.stringify(snapshot);
    window.render_game_to_text = readSnapshot;
    stage.dataset.state = "ready";
    stage.setAttribute("aria-busy", "false");
    poster.hidden = loading.hidden = true;
    hud.hidden = false;
    signal.addEventListener("abort", dispose, { once: true });
    frameId = requestAnimationFrame(frame);
    return { dispose };
  } catch (error) {
    dispose();
    throw error;
  }
}
