import { AnimationMixer, Box3, LoopOnce } from "three";

export default function createAnimationPreview({ model, clips, container, onPlay }) {
  const mixer = new AnimationMixer(model);
  const toolbar = document.createElement("div");
  toolbar.className = "viewer-actions viewer-animation-actions";
  toolbar.setAttribute("role", "group");
  toolbar.setAttribute("aria-label", "Animation previews");
  const buttons = new Map();
  const clipBounds = new Map();
  let action;
  let bounds;

  function play(clip) {
    mixer.stopAllAction();
    action = mixer.clipAction(clip).reset().setLoop(LoopOnce, 1);
    action.clampWhenFinished = true;
    action.play();

    if (!clipBounds.has(clip)) {
      // Frame the travel of the source clip as well as the starting pose.
      const envelope = new Box3();
      const pose = new Box3();
      for (let sample = 0; sample <= 8; sample++) {
        action.time = clip.duration * sample / 8;
        mixer.update(0);
        envelope.union(pose.setFromObject(model, true));
      }
      clipBounds.set(clip, envelope);
    }
    action.time = 0;
    mixer.update(0);
    bounds = clipBounds.get(clip);
    for (const [name, button] of buttons) {
      button.setAttribute("aria-pressed", String(name === clip.name));
    }
    onPlay(bounds);
  }

  for (const [name, label] of [["run", "Run"], ["sit", "Sit"]]) {
    const clip = clips.find((candidate) => candidate.name === name);
    if (!clip) throw new Error(`Missing animation clip: ${name}`);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "outline-button";
    button.textContent = label;
    button.setAttribute("aria-pressed", "false");
    button.addEventListener("click", () => play(clip));
    buttons.set(name, button);
    toolbar.append(button);
  }
  container.insertAdjacentElement("afterend", toolbar);

  return {
    get bounds() { return bounds; },
    update(elapsed) {
      if (!action?.isRunning()) return false;
      mixer.update(Math.min(elapsed, 0.05));
      return action.isRunning();
    },
    reset() {
      mixer.stopAllAction();
      action = undefined;
      bounds = undefined;
      for (const button of buttons.values()) button.setAttribute("aria-pressed", "false");
    },
    dispose() {
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      toolbar.remove();
    },
  };
}
