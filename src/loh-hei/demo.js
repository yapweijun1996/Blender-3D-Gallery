import { AnimationMixer, Box3, LoopOnce } from "three";
import { localize } from "../i18n/index.js";

export const TOSS_CLIP = "LOH_HEI_TOSS";

export function createTossMotion(model, clips, onState = () => {}) {
  const clip = clips.find(clip => clip.name === TOSS_CLIP &&
    clip.tracks.length > 0 && Number.isFinite(clip.duration) && clip.duration > 0);
  if (!clip) return null;

  const mixer = new AnimationMixer(model);
  let phase = "ready", action, bounds, envelope, disposed = false;
  const setPhase = next => {
    phase = next;
    onState(phase);
  };
  function pose(time) {
    action.time = time;
    mixer.update(0);
  }
  const finish = ({ action: finished }) => {
    if (!disposed && phase === "tossing" && finished === action) setPhase("mixed");
  };
  mixer.addEventListener("finished", finish);

  function play(reducedMotion) {
    if (disposed || phase !== "ready") return false;
    action = mixer.clipAction(clip).reset().setLoop(LoopOnce, 1);
    action.clampWhenFinished = true;
    action.play();
    if (!envelope) {
      // Frame the travel once per viewer, including the raised toss and final pose.
      envelope = new Box3();
      const sample = new Box3();
      for (let i = 0; i <= 12; i++) {
        pose(clip.duration * i / 12);
        envelope.union(sample.setFromObject(model, true));
      }
    }
    bounds = envelope;
    if (reducedMotion) {
      action.paused = true;
      pose(clip.duration);
      setPhase("mixed");
    } else {
      pose(0);
      setPhase("tossing");
    }
    return true;
  }

  function update(elapsed, reducedMotion) {
    if (disposed || phase !== "tossing") return false;
    if (reducedMotion) {
      action.paused = true;
      pose(clip.duration);
      setPhase("mixed");
    } else {
      // Do not jump after a backgrounded tab or delayed draw.
      mixer.update(Math.max(0, Math.min(elapsed, 0.05)));
    }
    return phase === "tossing";
  }

  function reset() {
    if (disposed) return;
    mixer.stopAllAction();
    action = undefined;
    bounds = undefined;
    setPhase("ready");
  }

  function dispose() {
    disposed = true;
    mixer.removeEventListener("finished", finish);
    mixer.stopAllAction();
    mixer.uncacheRoot(model);
  }

  return { play, update, reset, dispose, get phase() { return phase; }, get bounds() { return bounds; } };
}

export default function createLohHeiDemo({ model, clips, container, onPlay, invalidate }) {
  const toolbar = document.createElement("div");
  toolbar.className = "cart-demo loh-hei-demo";
  toolbar.setAttribute("role", "group");
  localize(toolbar, "lohHei.title", undefined, "aria-label");
  const title = document.createElement("strong");
  localize(title, "lohHei.title");
  const status = document.createElement("p");
  status.className = "cart-demo-status";
  status.setAttribute("role", "status");
  const buttons = document.createElement("div");
  buttons.className = "cart-demo-buttons";
  function button(id, label) {
    const node = document.createElement("button");
    node.type = "button";
    node.dataset.lohHeiAction = id;
    localize(node, label);
    buttons.append(node);
    return node;
  }
  const toss = button("toss", "lohHei.toss");
  const resetButton = button("reset", "lohHei.reset");
  const statusKeys = {
    ready: "lohHei.ready",
    tossing: "lohHei.tossing",
    mixed: "lohHei.mixed",
    unavailable: "lohHei.unavailable",
  };
  function render(phase) {
    toolbar.dataset.state = phase;
    localize(status, statusKeys[phase]);
    toss.disabled = phase !== "ready";
    resetButton.disabled = phase === "ready" || phase === "unavailable";
  }
  const motion = createTossMotion(model, clips, render);
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  toss.addEventListener("click", () => {
    const keyboardFocus = document.activeElement === toss;
    if (!motion?.play(reduced.matches)) return;
    if (keyboardFocus) resetButton.focus();
    onPlay(motion.bounds);
  });
  resetButton.addEventListener("click", () => {
    motion?.reset();
    invalidate();
    toss.focus();
  });
  toolbar.append(title, status, buttons);
  container.insertAdjacentElement("afterend", toolbar);
  render(motion ? "ready" : "unavailable");
  return {
    get bounds() { return motion?.bounds; },
    update(elapsed) { return motion?.update(elapsed, reduced.matches) ?? false; },
    reset() { motion?.reset(); },
    dispose() {
      motion?.dispose();
      toolbar.remove();
    },
  };
}
