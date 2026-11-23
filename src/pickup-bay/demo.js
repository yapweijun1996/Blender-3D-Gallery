import { Vector3 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { localize } from "../i18n/index.js";
import carUrl from "../../models/hatchback-car/exports/optimized.glb?url";
import { APPROACH_SECONDS, pickupOffset, pickupPhase } from "./state.js";

const anchorNames = ["ANCHOR_PICKUP_B08", "ANCHOR_VEHICLE_STOP", "ANCHOR_BOARDING_POINT"];
const stateCopy = {
  ready: "pickup.ready",
  loading: "pickup.loading",
  approaching: "pickup.approaching",
  stopped: "pickup.stopped",
  boarded: "pickup.boarded",
  failed: "pickup.failed",
};

function release(mesh) {
  const geometries = new Set(), materials = new Set(), textures = new Set();
  mesh?.removeFromParent();
  mesh?.traverse(object => {
    if (object.geometry) geometries.add(object.geometry);
    for (const material of [object.material ?? []].flat()) {
      materials.add(material);
      for (const value of Object.values(material)) if (value?.isTexture) textures.add(value);
    }
  });
  for (const texture of textures) texture.dispose();
  for (const material of materials) material.dispose();
  for (const geometry of geometries) geometry.dispose();
}

export default function createPickupDemo({ model, container, signal, invalidate }) {
  const anchors = anchorNames.map(name => model.getObjectByName(name));
  if (anchors.some(anchor => !anchor)) return null;
  model.updateWorldMatrix(true, true);
  const stop = model.worldToLocal(anchors[1].getWorldPosition(new Vector3()));
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let car, controller, disposed = false, phase = "ready", elapsed = 0;
  const toolbar = document.createElement("div");
  // Reuse the shared viewer interaction toolbar styling.
  toolbar.className = "cart-demo pickup-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "pickup.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "pickup.title");
  const copy = document.createElement("p");
  copy.className = "cart-demo-status";
  localize(copy, "pickup.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function makeButton(action, label, callback) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.pickupAction = action;
    localize(button, label);
    button.addEventListener("click", callback);
    buttons.append(button);
    return button;
  }
  const select = makeButton("select", "pickup.select", () => void selectBay());
  const board = makeButton("board", "pickup.board", () => {
    if (disposed || phase !== "stopped") return;
    setPhase("board");
    resetButton.focus();
  });
  const resetButton = makeButton("reset", "pickup.reset", () => {
    reset();
    select.focus();
  });
  toolbar.append(title, copy, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);

  function render() {
    toolbar.dataset.state = phase;
    localize(status, stateCopy[phase]);
    select.disabled = phase !== "ready" && phase !== "failed";
    board.disabled = phase !== "stopped";
    // Reset remains operable during fetch, animation and failure.
    resetButton.disabled = phase === "ready";
  }

  function setPhase(action) {
    const next = pickupPhase(phase, action);
    if (phase !== next) {
      phase = next;
      render();
    }
  }

  function place(offset) {
    car.position.copy(stop);
    car.position.x += offset;
    // The inspected local hatchback faces +Z upright; the bay lane runs +X.
    car.rotation.y = Math.PI / 2;
  }

  async function selectBay() {
    if (disposed || signal.aborted || (phase !== "ready" && phase !== "failed")) return;
    const moveFocus = document.activeElement === select;
    setPhase("select");
    if (moveFocus) resetButton.focus();
    const active = new AbortController();
    controller = active;
    try {
      if (!car) {
        const response = await fetch(carUrl, { signal: active.signal });
        const bytes = await response.arrayBuffer();
        if (!response.ok) throw new Error("Unable to load the local simulation vehicle");
        if (disposed || active.signal.aborted || signal.aborted) return;
        const { scene } = await new GLTFLoader().parseAsync(bytes, "");
        if (disposed || active.signal.aborted || signal.aborted) {
          release(scene);
          return;
        }
        car = scene;
      }
      elapsed = 0;
      place(reducedMotion.matches ? 0 : pickupOffset(0));
      model.add(car);
      if (reducedMotion.matches) arrive();
      else setPhase("loaded");
      invalidate();
    } catch {
      if (!disposed && !active.signal.aborted && !signal.aborted) setPhase("fail");
    } finally {
      if (controller === active) controller = undefined;
    }
  }

  function arrive() {
    place(0);
    setPhase("arrive");
  }

  function update(deltaSeconds) {
    if (phase !== "approaching" || !car) return false;
    // Cap a delayed frame so switching tabs doesn't skip straight to boarding.
    elapsed += Math.max(0, Math.min(deltaSeconds, 0.05));
    if (reducedMotion.matches || elapsed >= APPROACH_SECONDS) {
      arrive();
      return false;
    }
    place(pickupOffset(elapsed));
    return true;
  }

  function reset() {
    controller?.abort();
    controller = undefined;
    elapsed = 0;
    car?.removeFromParent();
    setPhase("reset");
    invalidate();
  }

  function dispose() {
    disposed = true;
    controller?.abort();
    release(car);
    car = undefined;
    toolbar.remove();
  }

  render();
  return { update, reset, dispose };
}
