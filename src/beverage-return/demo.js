import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const BCR_SAMPLE_ACCEPT_CLIP = "BCR_SAMPLE_ACCEPT";
const requiredTracks = new Map([
  ["BCR_SAMPLE_CAN.position", ["BCR_SAMPLE_CAN", "vector"]],
  ["BCR_ACCEPT_FLAG.quaternion", ["BCR_ACCEPT_FLAG", "quaternion"]],
]);

export function createBeverageReturnMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === BCR_SAMPLE_ACCEPT_CLIP &&
    clip.tracks.length === requiredTracks.size &&
    new Set(clip.tracks.map(track => track.name)).size === requiredTracks.size &&
    clip.tracks.every(track => {
      const binding = requiredTracks.get(track.name);
      return binding && track.ValueTypeName === binding[1] && model.getObjectByName(binding[0]);
    }) &&
    Number.isFinite(clip.duration) && clip.duration > 0);
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "accepting" && finished === action) setPhase("complete");
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
      else setPhase("accepting");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "accepting") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "accepting";
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

export default function createBeverageReturnDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo beverage-return-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "beverageReturn.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "beverageReturn.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "beverageReturn.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.beverageReturnAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const accept = button("accept", "beverageReturn.accept");
  const reset = button("reset", "beverageReturn.reset");
  const statusKeys = {
    ready: "beverageReturn.ready",
    accepting: "beverageReturn.accepting",
    complete: "beverageReturn.complete",
    unavailable: "beverageReturn.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    accept.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createBeverageReturnMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  function acceptCan() {
    const focused = document.activeElement === accept;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  }
  function resetReturn() {
    motion?.reset();
    invalidate();
    accept.focus();
  }
  accept.addEventListener("click", acceptCan);
  reset.addEventListener("click", resetReturn);
  toolbar.append(title, disclaimer, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    update: elapsed => motion?.update(elapsed, reducedMotion.matches) ?? false,
    reset: () => motion?.reset(),
    dispose() {
      accept.removeEventListener("click", acceptCan);
      reset.removeEventListener("click", resetReturn);
      motion?.dispose();
      toolbar.remove();
    },
  };
}
