import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const AWNING_FOLD_IN_CLIP = "AWNING_FOLD_IN";
const requiredTracks = [
  ["AWNING_FRONT_BAR", "position", "vector"],
  ["AWNING_FABRIC", "scale", "vector"],
  ["AWNING_ROLLER", "quaternion", "quaternion"],
];

export function createAwningMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === AWNING_FOLD_IN_CLIP &&
    Number.isFinite(clip.duration) && clip.duration > 0 &&
    requiredTracks.every(([node, property, type]) => {
      // Other authored tracks may also fold the arms or reposition the fabric.
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
    if (!disposed && phase === "retracting" && finished === action) setPhase("complete");
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
      else setPhase("retracting");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "retracting") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "retracting";
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

export default function createAwningDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo awning-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "awning.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "awning.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "awning.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.awningAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const retract = button("retract", "awning.retract");
  const reset = button("reset", "awning.reset");
  const statusKeys = {
    ready: "awning.ready",
    retracting: "awning.retracting",
    complete: "awning.complete",
    unavailable: "awning.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    retract.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createAwningMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function retractAwning() {
    const focused = document.activeElement === retract;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetAwning() {
    motion?.reset();
    invalidate();
    retract.focus();
  }
  retract.addEventListener("click", retractAwning);
  reset.addEventListener("click", resetAwning);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      retract.removeEventListener("click", retractAwning);
      reset.removeEventListener("click", resetAwning);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
