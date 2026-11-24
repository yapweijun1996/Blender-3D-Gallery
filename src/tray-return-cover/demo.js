import { AnimationMixer, LoopOnce, VectorKeyframeTrack } from "three";
import { localize } from "../i18n/index.js";

export const TRAY_RETURN_COVER_LIFT_CLIP = "TRAY_RETURN_COVER_LIFT";
const movingNodes = ["TRAY_RETURN_COVER", "TRAY_RETURN_COUNTERWEIGHT"];

export function createTrayReturnCoverMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === TRAY_RETURN_COVER_LIFT_CLIP &&
    Number.isFinite(clip.duration) && clip.duration > 0 &&
    movingNodes.every(node => {
      const tracks = clip.tracks.filter(track => track.name === `${node}.position`);
      return tracks.length === 1 && tracks[0] instanceof VectorKeyframeTrack && model.getObjectByName(node);
    }));
  if (!clip) return null;

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

export default function createTrayReturnCoverDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo tray-return-cover-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "trayReturnCover.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "trayReturnCover.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "trayReturnCover.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.trayReturnCoverAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const open = button("open", "trayReturnCover.open");
  const reset = button("reset", "trayReturnCover.reset");
  const statusKeys = {
    ready: "trayReturnCover.ready",
    opening: "trayReturnCover.opening",
    complete: "trayReturnCover.complete",
    unavailable: "trayReturnCover.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    open.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createTrayReturnCoverMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function openTrayReturnCover() {
    const focused = document.activeElement === open;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetTrayReturnCover() {
    motion?.reset();
    invalidate();
    open.focus();
  }
  open.addEventListener("click", openTrayReturnCover);
  reset.addEventListener("click", resetTrayReturnCover);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      open.removeEventListener("click", openTrayReturnCover);
      reset.removeEventListener("click", resetTrayReturnCover);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
