import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createBeverageReturnDemo, { createBeverageReturnMotion, BCR_SAMPLE_ACCEPT_CLIP } from "../src/beverage-return/demo.js";

const seconds = 2;
const start = new Quaternion();
const end = new Quaternion().setFromAxisAngle(new Vector3(0, 1, 0), Math.PI);
const readyPosition = [0, 1.09, .260];
const insidePosition = [0, 1.09, -.165];
function fixture() {
  const model = new Group();
  const can = new Group();
  can.name = "BCR_SAMPLE_CAN";
  can.position.fromArray(readyPosition);
  const flag = new Group();
  flag.name = "BCR_ACCEPT_FLAG";
  const casework = new Group();
  casework.name = "BCR_CASEWORK";
  model.add(can, flag, casework);
  const clip = new AnimationClip(BCR_SAMPLE_ACCEPT_CLIP, seconds, [
    new VectorKeyframeTrack("BCR_SAMPLE_CAN.position", [0, 1.3, seconds],
      [...readyPosition, ...insidePosition, ...insidePosition]),
    new QuaternionKeyframeTrack("BCR_ACCEPT_FLAG.quaternion", [0, .72, 1.7, seconds],
      [...start.toArray(), ...start.toArray(), ...end.toArray(), ...end.toArray()]),
  ]);
  return { model, can, flag, casework, clips: [clip] };
}
const vectorNear = (actual, expected) => assert.ok(actual.distanceTo(new Vector3().fromArray(expected)) < 1e-6);
const quaternionNear = (actual, expected) => assert.ok(actual.angleTo(expected) < .001);
function closed(can, flag) {
  assert.deepEqual(can.position.toArray(), readyPosition);
  assert.deepEqual(flag.quaternion.toArray(), start.toArray());
}
function finished(can, flag) {
  vectorNear(can.position, insidePosition);
  quaternionNear(flag.quaternion, end);
}

test("container return has its exact ID only, preserving the parcel model interaction", () => {
  assert.equal(interactionKind({ id: "community-beverage-container-return-kiosk" }), "beverage-return");
  assert.equal(interactionKind({ id: "community-beverage-container-return-kiosk-variant" }), null);
  assert.equal(interactionKind({ id: "beverage-return" }), null);
  assert.equal(interactionKind({ id: "shophouse-parcel-drop-hatch" }), "parcel-hatch");
});

test("manual single-play moves the sample then turns the flag; no autoplay or motion after reset", () => {
  const { model, can, flag, casework, clips } = fixture();
  const states = [];
  const motion = createBeverageReturnMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  closed(can, flag);
  motion.play(false);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 10; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(insidePosition[2] < can.position.z && can.position.z < readyPosition[2]);
  quaternionNear(flag.quaternion, start);
  for (let i = 0; i < 20; i++) motion.update(.05, false);
  vectorNear(can.position, insidePosition);
  assert.ok(flag.quaternion.angleTo(start) > .1 && flag.quaternion.angleTo(end) > .1);
  assert.deepEqual(casework.position.toArray(), [0, 0, 0]);
  assert.deepEqual(casework.quaternion.toArray(), start.toArray());
  for (let i = 0; i < 15; i++) motion.update(.05, false);
  assert.equal(motion.update(.05, false), false);
  finished(can, flag);
  assert.equal(motion.play(false), false);
  motion.reset();
  closed(can, flag);
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["accepting", "complete", "ready"]);
});

test("reduced-motion final is immediate; preference changes, interrupted reset and disposal are safe", () => {
  const { model, can, flag, clips } = fixture();
  const states = [];
  const motion = createBeverageReturnMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  finished(can, flag);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  closed(can, flag);
  motion.play(false);
  motion.update(.04, false);
  motion.reset();
  closed(can, flag);
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  finished(can, flag);
  motion.dispose();
  motion.dispose();
  closed(can, flag);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "accepting", "ready", "accepting", "complete"]);
});

test("strict binding rejects missing, extra, colliding or wrong-type native tracks", () => {
  const { model, clips, flag } = fixture();
  const [canMotion, flagMotion] = clips[0].tracks;
  const unexpected = new VectorKeyframeTrack("BCR_CASEWORK.position", [0, 1], [0, 0, 0, 1, 0, 0]);
  const wrongType = new VectorKeyframeTrack("BCR_ACCEPT_FLAG.quaternion", [0, 1], [0, 0, 0, 1, 0, 0]);
  assert.equal(createBeverageReturnMotion(model, []), null);
  const unusable = tracks => createBeverageReturnMotion(model, [new AnimationClip(BCR_SAMPLE_ACCEPT_CLIP, seconds, tracks)]);
  for (const tracks of [[canMotion], [canMotion, canMotion], [canMotion, wrongType],
    [canMotion, unexpected], [canMotion, flagMotion, unexpected]]) assert.equal(unusable(tracks), null);
  assert.equal(createBeverageReturnMotion(model, [new AnimationClip("unrelated", seconds, clips[0].tracks)]), null);
  model.remove(flag);
  assert.equal(createBeverageReturnMotion(model, clips), null);
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
    const { model, can, flag, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createBeverageReturnDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [accept, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["beverageReturn.title"]);
    assert.equal(disclaimer.textContent, messages.en["beverageReturn.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["beverageReturn.ready"]);
    assert.equal(accept.tag, "button");
    assert.equal(accept.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    accept.focus();
    accept.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["beverageReturn.accepting"]);
    accept.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["beverageReturn.complete"]);
    finished(can, flag);
    reset.click();
    assert.equal(document.activeElement, accept);
    assert.equal(status.textContent, messages.en["beverageReturn.ready"]);
    closed(can, flag);
    accept.click();
    finished(can, flag);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    closed(can, flag);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    accept.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createBeverageReturnDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["beverageReturn.unavailable"]);
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
  const keys = ["title", "disclaimer", "ready", "accepting", "complete", "unavailable", "accept", "reset"];
  for (const key of keys) {
    const localized = Object.values(messages).map(m => m[`beverageReturn.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
