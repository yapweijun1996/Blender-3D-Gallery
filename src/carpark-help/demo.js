import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const HELP_PRESS_CLIP = "CARPARK_HELP_PRESS";

export function createHelpPressMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === HELP_PRESS_CLIP &&
    clip.tracks.length > 0 && Number.isFinite(clip.duration) && clip.duration > 0);
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "pressing" && finished === action) setPhase("complete");
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
      else setPhase("pressing");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "pressing") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "pressing";
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

export default function createCarparkHelpDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo carpark-help-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "carparkHelp.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "carparkHelp.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "carparkHelp.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.carparkHelpAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const press = button("press", "carparkHelp.press");
  const reset = button("reset", "carparkHelp.reset");
  const statusKeys = {
    ready: "carparkHelp.ready",
    pressing: "carparkHelp.pressing",
    complete: "carparkHelp.complete",
    unavailable: "carparkHelp.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    press.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createHelpPressMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  press.addEventListener("click", () => {
    const focused = document.activeElement === press;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  });
  reset.addEventListener("click", () => {
    motion?.reset();
    invalidate();
    press.focus();
  });
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      motion?.dispose();
      toolbar.remove();
    },
  };
}
