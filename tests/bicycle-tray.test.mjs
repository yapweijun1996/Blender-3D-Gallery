import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createBicycleTrayDemo, { createBicycleTrayMotion, TWO_TIER_TRAY_SLIDE_TIP_CLIP } from "../src/bicycle-tray/demo.js";

const seconds = 2.4;
const ready = new Quaternion();
const tipped = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), Math.PI / 4);
function fixture() {
  const model = new Group(), carriage = new Group(), pivot = new Group(), stand = new Group();
  carriage.name = "BIKE_UPPER_CARRIAGE";
  pivot.name = "BIKE_UPPER_TRAY_PIVOT";
  model.add(carriage, stand);
  carriage.add(pivot);
  const tracks = [
    new VectorKeyframeTrack("BIKE_UPPER_CARRIAGE.position", [0, 1.2, seconds], [0, 0, 0, 0, 0, .7, 0, 0, .7]),
    new QuaternionKeyframeTrack("BIKE_UPPER_TRAY_PIVOT.quaternion", [0, 1.2, 2.1, seconds],
      [...ready.toArray(), ...ready.toArray(), ...tipped.toArray(), ...tipped.toArray()]),
  ];
  return { model, carriage, pivot, stand, tracks,
    clips: [new AnimationClip(TWO_TIER_TRAY_SLIDE_TIP_CLIP, seconds, tracks)] };
}
function assertPose(carriage, pivot, lowered) {
  assert.ok(Math.abs(carriage.position.z - (lowered ? .7 : 0)) < 1e-6);
  assert.ok(pivot.quaternion.clone().normalize().angleTo(lowered ? tipped : ready) < .001);
  assert.equal(carriage.position.x, 0);
  assert.equal(carriage.position.y, 0);
}

test("the exact transit rack alone gets this demo, preserving older mappings", () => {
  assert.equal(interactionKind({ id: "transit-two-tier-bicycle-tray" }), "bicycle-tray");
  for (const id of ["bicycle-tray", "transit-two-tier-bicycle-tray-variant", "bicycle-parking-rack"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "hawker-tray-return-counterweight-cover" }), "tray-return-cover");
  assert.equal(interactionKind({ id: "mall-fold-down-changing-station" }), "changing-station");
});

test("the full authored clip slides first, tips second, holds and never restarts without reset", () => {
  const { model, carriage, pivot, stand, clips } = fixture();
  const states = [], motion = createBicycleTrayMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  assertPose(carriage, pivot, false);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 20; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(carriage.position.z > 0 && carriage.position.z < .7);
  assert.deepEqual(pivot.quaternion.toArray(), ready.toArray());
  for (let i = 0; i < 15; i++) motion.update(.05, false);
  assert.ok(Math.abs(carriage.position.z - .7) < 1e-6);
  assert.ok(pivot.quaternion.angleTo(ready) > .1);
  assert.ok(pivot.quaternion.angleTo(tipped) > .1);
  assert.deepEqual(stand.position.toArray(), [0, 0, 0]);
  for (let i = 0; i < 20; i++) motion.update(.05, false);
  assert.equal(motion.update(1, false), false);
  assertPose(carriage, pivot, true);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.deepEqual(carriage.position.toArray(), [0, 0, 0]);
  assert.deepEqual(pivot.quaternion.toArray(), ready.toArray());
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["lowering", "complete", "ready"]);
});

test("reduced final and live preference changes use the same pose; interruption and disposal restore it safely", () => {
  const { model, carriage, pivot, clips } = fixture();
  const states = [], motion = createBicycleTrayMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  assertPose(carriage, pivot, true);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  assertPose(carriage, pivot, false);
  motion.play(false);
  for (let i = 0; i < 8; i++) motion.update(.05, false);
  motion.reset();
  assertPose(carriage, pivot, false);
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  assertPose(carriage, pivot, true);
  motion.dispose();
  motion.dispose();
  assertPose(carriage, pivot, false);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "lowering", "ready", "lowering", "complete"]);
});

test("each exact named node and actual track class is required; duplicate tracks fall back", () => {
  const { model, carriage, pivot, tracks, clips } = fixture();
  const [slide, tip] = tracks;
  const wrongSlide = new QuaternionKeyframeTrack("BIKE_UPPER_CARRIAGE.position", [0, 1],
    [...ready.toArray(), ...tipped.toArray()]);
  const wrongTip = new VectorKeyframeTrack("BIKE_UPPER_TRAY_PIVOT.quaternion", [0, 1], [0, 0, 0, 0, 0, 1]);
  const create = tracks => createBicycleTrayMotion(model, [new AnimationClip(TWO_TIER_TRAY_SLIDE_TIP_CLIP, seconds, tracks)]);
  assert.equal(createBicycleTrayMotion(model, []), null);
  for (const invalid of [[], [slide], [tip], [wrongSlide, tip], [slide, wrongTip], [slide, tip, tip]])
    assert.equal(create(invalid), null);
  assert.equal(createBicycleTrayMotion(model, [new AnimationClip("unrelated", seconds, tracks)]), null);
  carriage.remove(pivot);
  assert.equal(createBicycleTrayMotion(model, clips), null);
});

test("native toolbar labels, status, focus, reset, fallback and detach are wired", () => {
  let document;
  class Element extends EventTarget {
    constructor(tag) {
      super();
      this.tag = tag;
      this.attributes = new Map();
      this.dataset = {};
      this.children = [];
    }
    setAttribute(key, value) { this.attributes.set(key, value); }
    getAttribute(key) { return this.attributes.get(key); }
    append(...children) { this.children.push(...children); }
    insertAdjacentElement(where, element) { assert.equal(where, "afterend"); this.toolbar = element; }
    remove() { this.removed = true; }
    focus() { assert.ok(!this.disabled); document.activeElement = this; }
    click() { if (!this.disabled) this.dispatchEvent(new Event("click")); }
  }
  const restoreDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
  const restoreWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
  document = { createElement: tag => new Element(tag) };
  const preference = { matches: false };
  Object.defineProperty(globalThis, "document", { configurable: true, value: document });
  Object.defineProperty(globalThis, "window", { configurable: true, value: {
    matchMedia(query) {
      assert.equal(query, "(prefers-reduced-motion: reduce)");
      return preference;
    },
  } });
  try {
    const { model, carriage, pivot, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createBicycleTrayDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [lower, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["bicycleTray.title"]);
    assert.equal(disclaimer.textContent, messages.en["bicycleTray.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["bicycleTray.ready"]);
    assert.equal(lower.tag, "button");
    assert.equal(lower.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    lower.focus();
    lower.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["bicycleTray.lowering"]);
    lower.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["bicycleTray.complete"]);
    assertPose(carriage, pivot, true);
    reset.click();
    assert.equal(document.activeElement, lower);
    assert.equal(status.textContent, messages.en["bicycleTray.ready"]);
    assertPose(carriage, pivot, false);
    lower.click();
    assertPose(carriage, pivot, true);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    assertPose(carriage, pivot, false);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    lower.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createBicycleTrayDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["bicycleTray.unavailable"]);
    assert.ok(container.toolbar.children[3].children.every(button => button.disabled));
    assert.equal(fallback.update(1), false);
    fallback.dispose();
  } finally {
    for (const [key, descriptor] of [["document", restoreDocument], ["window", restoreWindow]]) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else delete globalThis[key];
    }
  }
});

test("all eight model-facing strings have independently localized EN, zh-Hans and Malaysian Malay entries", () => {
  assert.deepEqual(Object.keys(messages).sort(), ["en", "ms", "zh-Hans"]);
  const keys = ["title", "disclaimer", "ready", "lowering", "complete", "unavailable", "lower", "reset"];
  for (const key of keys) {
    const localized = Object.values(messages).map(m => m[`bicycleTray.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
