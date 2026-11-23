import { AnimationMixer, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const KELAPA_CRANK_TURN_CLIP = "KELAPA_CRANK_TURN";

export function createCoconutCrankMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === KELAPA_CRANK_TURN_CLIP &&
    clip.tracks.length > 0 && Number.isFinite(clip.duration) && clip.duration > 0);
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(next);
  };
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "turning" && finished === action) setPhase("complete");
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
      else setPhase("turning");
      return true;
    },
    update(elapsed, reducedMotion) {
      if (disposed || phase !== "turning") return false;
      if (reducedMotion) settle();
      else mixer.update(Math.max(0, Math.min(elapsed, .05)));
      return phase === "turning";
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

export default function createCoconutScraperDemo({ model, clips, container, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo coconut-scraper-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "coconutScraper.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "coconutScraper.title");
  const disclaimer = document.createElement("p");
  disclaimer.className = "cart-demo-status";
  localize(disclaimer, "coconutScraper.disclaimer");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(action, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.coconutScraperAction = action;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const turn = button("turn", "coconutScraper.turn");
  const reset = button("reset", "coconutScraper.reset");
  const statusKeys = {
    ready: "coconutScraper.ready",
    turning: "coconutScraper.turning",
    complete: "coconutScraper.complete",
    unavailable: "coconutScraper.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    turn.disabled = phase !== "ready";
    reset.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createCoconutCrankMotion(model, clips, render);
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  turn.addEventListener("click", () => {
    const focused = document.activeElement === turn;
    if (!motion?.play(reducedMotion.matches)) return;
    if (focused) reset.focus();
    invalidate();
  });
  reset.addEventListener("click", () => {
    motion?.reset();
    invalidate();
    turn.focus();
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
