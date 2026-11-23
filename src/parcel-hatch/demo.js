import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const PARCEL_HATCH_OPEN_CLIP = "PARCEL_HATCH_OPEN";
const flapName = "PARCEL_DROP_FLAP";

export function createParcelHatchMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === PARCEL_HATCH_OPEN_CLIP &&
    clip.tracks.length === 1 && clip.tracks[0].name === `${flapName}.quaternion` &&
    clip.tracks[0].ValueTypeName === "quaternion" &&
    Number.isFinite(clip.duration) && clip.duration > 0);
  if (!clip || !model.getObjectByName(flapName)) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "opening" && finished === action) setPhase("complete");
  };
  mixer.addEventListener("finished", finish);

  function settle() {
    action.paused = true;
    action.time = clip.duration;
    mixer.update(0);
    setPhase("complete");
  }

  return {
    play(reducedMotion) {
      if (disposed || phase !== "ready") return false;
      action = mixer.clipAction(clip).reset().setLoop(LoopOnce, 1);
      action.clampWhenFinished = true;
      action.play();
      if (reducedMotion) settle();
      else setPhase("opening");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "opening") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "opening";
    },
    reset() {
      if (disposed) return;
      mixer.stopAllAction();
      action = undefined;
      setPhase("ready");
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      mixer.removeEventListener("finished", finish);
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
    },
    get phase() { return phase; },
  };
}

export default function createParcelHatchDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo parcel-hatch-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "parcelHatch.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "parcelHatch.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "parcelHatch.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.parcelHatchAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const open = button("open", "parcelHatch.open");
  const reset = button("reset", "parcelHatch.reset");
  const statusKeys = {
    ready: "parcelHatch.ready",
    opening: "parcelHatch.opening",
    complete: "parcelHatch.complete",
    unavailable: "parcelHatch.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    open.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createParcelHatchMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function openHatch() {
    const focused = document.activeElement === open;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetHatch() {
    motion?.reset();
    invalidate();
    open.focus();
  }
  open.addEventListener("click", openHatch);
  reset.addEventListener("click", resetHatch);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      open.removeEventListener("click", openHatch);
      reset.removeEventListener("click", resetHatch);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
