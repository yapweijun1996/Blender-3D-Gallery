import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const DACING_FIND_BALANCE_CLIP = "DACING_FIND_BALANCE";
const requiredTracks = [
  ["DACING_COUNTERWEIGHT", "position", "vector"],
  ["DACING_PAN_SWIVEL", "quaternion", "quaternion"],
  ["DACING_BEAM", "quaternion", "quaternion"],
];

export function createDacingMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === DACING_FIND_BALANCE_CLIP &&
    Number.isFinite(clip.duration) && clip.duration > 0 &&
    requiredTracks.every(([node, property, type]) => {
      // Other authored tracks may also keep the moving counterweight upright.
      const tracks = clip.tracks.filter(track => track.name === `${node}.${property}`);
      return tracks.length === 1 && tracks[0].ValueTypeName === type && model.getObjectByName(node);
    }));
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "balancing" && finished === action) setPhase("complete");
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
      else setPhase("balancing");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "balancing") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "balancing";
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

export default function createDacingDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo dacing-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "dacing.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "dacing.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "dacing.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.dacingAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const balance = button("balance", "dacing.balance");
  const reset = button("reset", "dacing.reset");
  const statusKeys = {
    ready: "dacing.ready",
    balancing: "dacing.balancing",
    complete: "dacing.complete",
    unavailable: "dacing.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    balance.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createDacingMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function balanceDacing() {
    const focused = document.activeElement === balance;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetDacing() {
    motion?.reset();
    invalidate();
    balance.focus();
  }
  balance.addEventListener("click", balanceDacing);
  reset.addEventListener("click", resetDacing);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      balance.removeEventListener("click", balanceDacing);
      reset.removeEventListener("click", resetDacing);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
