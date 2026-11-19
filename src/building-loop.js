import { createBayReflection } from "./sands-water.js";
import { AnimationMixer, LoopRepeat } from "three";
import { localize } from "./i18n/index.js";

export default function createBuildingLoop({ model, clip, container, invalidate }) {
  if (!clip) throw new Error("Missing Marina Bay Sands construction clip.");
  const reflection = createBayReflection(model);
  const mixer = new AnimationMixer(model);
  const action = mixer.clipAction(clip).setLoop(LoopRepeat, Infinity);
  const preference = matchMedia("(prefers-reduced-motion: reduce)");
  const toolbar = document.createElement("div");
  toolbar.className = "viewer-actions viewer-animation-actions";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "outline-button";
  const phase = document.createElement("span");
  const stages = model.getObjectByName("ASSET_MarinaBaySands").userData.constructionStages;
  let lastStage;
  function showStage(time) {
    const forward = Math.min(time, clip.duration - time);
    const key = time > clip.duration / 2 && forward < 9.2 && forward >= 0.54
      ? "return" : stages.findLast(([start]) => forward >= start)[1];
    if (key !== lastStage) localize(phase, "sands." + key);
    lastStage = key;
  }
  showStage(preference.matches ? clip.duration / 2 : 0);
  toolbar.append(button, phase);
  container.insertAdjacentElement("afterend", toolbar);

  function setPlaying(playing) {
    action.paused = !playing;
    if (playing) {
      action.play();
      mixer.update(0);
    }
    localize(button, playing ? "common.pause" : "common.play");
    invalidate();
  }

  function syncPreference() {
    setPlaying(!preference.matches);
  }

  button.addEventListener("click", () => setPlaying(action.paused));
  preference.addEventListener("change", syncPreference);
  syncPreference();
  return {
    update(elapsed) {
      if (!action.isRunning()) return false;
      mixer.update(Math.min(elapsed, 0.05));
      reflection.sample(action.time / clip.duration);
      showStage(action.time);
      return true;
    },
    dispose() {
      preference.removeEventListener("change", syncPreference);
      reflection.dispose();
      mixer.stopAllAction();
      mixer.uncacheRoot(model);
      toolbar.remove();
    },
  };
}
