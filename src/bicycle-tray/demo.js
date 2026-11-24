import { AnimationMixer, LoopOnce, QuaternionKeyframeTrack, VectorKeyframeTrack } from "three";
import { localize } from "../i18n/index.js";

export const TWO_TIER_TRAY_SLIDE_TIP_CLIP = "TWO_TIER_TRAY_SLIDE_TIP";
const requiredTracks = [
  ["BIKE_UPPER_CARRIAGE", "position", VectorKeyframeTrack],
  ["BIKE_UPPER_TRAY_PIVOT", "quaternion", QuaternionKeyframeTrack],
];

export function createBicycleTrayMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === TWO_TIER_TRAY_SLIDE_TIP_CLIP &&
    Number.isFinite(clip.duration) && clip.duration > 0 &&
    requiredTracks.every(([node, property, Track]) => {
      const tracks = clip.tracks.filter(track => track.name === `${node}.${property}`);
      return tracks.length === 1 && tracks[0] instanceof Track && model.getObjectByName(node);
    }));
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "lowering" && finished === action) setPhase("complete");
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
      else setPhase("lowering");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "lowering") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "lowering";
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

export default function createBicycleTrayDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo bicycle-tray-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "bicycleTray.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "bicycleTray.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "bicycleTray.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.bicycleTrayAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const lower = button("lower", "bicycleTray.lower");
  const reset = button("reset", "bicycleTray.reset");
  const statusKeys = {
    ready: "bicycleTray.ready",
    lowering: "bicycleTray.lowering",
    complete: "bicycleTray.complete",
    unavailable: "bicycleTray.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    lower.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createBicycleTrayMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function lowerBicycleTray() {
    const focused = document.activeElement === lower;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetBicycleTray() {
    motion?.reset();
    invalidate();
    lower.focus();
  }
  lower.addEventListener("click", lowerBicycleTray);
  reset.addEventListener("click", resetBicycleTray);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      lower.removeEventListener("click", lowerBicycleTray);
      reset.removeEventListener("click", resetBicycleTray);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
