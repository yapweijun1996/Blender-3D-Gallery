import { AnimationMixer, LoopOnce, LoopRepeat } from "three";
import { localize } from "./i18n/index.js";

// Each lazy adapter owns its model bindings and clip choices. The controller
// demonstrates authored clips and cosmetics without simulating the mall.
export function createVisitorDemo(
  { model, clips, container, invalidate },
  { createCustomization, appearance, accessories, animations, looping },
) {
  const custom = createCustomization(model);
  const defaults = custom.state;
  const mixer = new AnimationMixer(model);
  const available = new Map(clips.map(clip => [clip.name, clip]));
  const toolbar = document.createElement("section");
  toolbar.className = "visitor-v2-controls";
  localize(toolbar, "visitor.controls", undefined, "aria-label");
  const heading = localize(document.createElement("strong"), "visitor.controls");
  const note = localize(document.createElement("p"), "visitor.note");
  const fields = document.createElement("div");
  fields.className = "visitor-v2-fields";
  toolbar.append(heading, note, fields);
  const selects = {};
  let action = null, playing = false;

  function select(key, label, options, onChange) {
    const wrapper = document.createElement("label");
    const name = localize(document.createElement("span"), label);
    const input = document.createElement("select");
    input.dataset.visitorControl = key;
    for (const [value, text] of options) {
      const option = document.createElement("option");
      option.value = value;
      localize(option, text);
      input.append(option);
    }
    input.addEventListener("change", () => {
      onChange(input.value);
      invalidate();
    });
    wrapper.append(name, input);
    fields.append(wrapper);
    selects[key] = input;
  }

  function play(name) {
    const clip = available.get(name);
    if (!clip) throw new Error(`Visitor animation missing: ${name}`);
    mixer.stopAllAction();
    action = mixer.clipAction(clip);
    action.reset();
    const loop = looping.includes(name);
    action.setLoop(loop ? LoopRepeat : LoopOnce, loop ? Infinity : 1);
    action.clampWhenFinished = !loop;
    action.play();
    playing = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    mixer.update(0);
  }

  function reset() {
    custom.apply(defaults);
    for (const [key, value] of Object.entries(defaults)) {
      selects[key].value = typeof value === "boolean" ? (value ? "on" : "off") : value;
    }
    selects.animation.value = "idle";
    play("idle");
  }

  function dispose() {
    playing = false;
    mixer.stopAllAction();
    mixer.uncacheRoot(model);
    custom.dispose();
    toolbar.remove();
  }

  try {
    for (const [key, values] of Object.entries({ ...appearance, skin: ["light", "medium", "dark"] })) {
      select(key, `visitor.${key}`, values.map(value => [value, `visitor.${value}`]),
        value => custom.apply({ [key]: value }));
    }
    for (const key of accessories) {
      select(key, `visitor.${key}`, [["on", "common.on"], ["off", "common.off"]],
        value => custom.apply({ [key]: value === "on" }));
    }
    select("animation", "common.animation", animations, play);
    reset();
    container.insertAdjacentElement("afterend", toolbar);
  } catch (error) {
    dispose();
    throw error;
  }

  return {
    reset,
    update(dt) {
      if (!playing || !action) return false;
      mixer.update(Math.min(Math.max(dt, 0), 0.05));
      if (action.paused) playing = false;
      return playing;
    },
    dispose,
  };
}
