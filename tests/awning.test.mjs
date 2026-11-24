import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createAwningDemo, { createAwningMotion, AWNING_FOLD_IN_CLIP } from "../src/awning/demo.js";

const seconds = 2.4;
const start = new Quaternion();
const end = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), Math.PI);
const away = [0, 1.1, 1], parked = [0, 1.2, .12];
const full = [1, 1, 1], gathered = [1, 1, .1];
function fixture() {
  const model = new Group(), nodes = {};
  for (const [key, name] of Object.entries({ bar: "AWNING_FRONT_BAR", fabric: "AWNING_FABRIC",
    roller: "AWNING_ROLLER", arm: "AWNING_SIDE_ARM", wall: "WALL" })) {
    nodes[key] = new Group();
    nodes[key].name = name;
    model.add(nodes[key]);
  }
  nodes.bar.position.fromArray(away);
  const tracks = [
    new VectorKeyframeTrack("AWNING_FRONT_BAR.position", [0, seconds], [...away, ...parked]),
    new VectorKeyframeTrack("AWNING_FABRIC.scale", [0, seconds], [...full, ...gathered]),
    new QuaternionKeyframeTrack("AWNING_ROLLER.quaternion", [0, seconds], [...start.toArray(), ...end.toArray()]),
    new QuaternionKeyframeTrack("AWNING_SIDE_ARM.quaternion", [0, seconds], [...start.toArray(), ...end.toArray()]),
  ];
  const clips = [new AnimationClip(AWNING_FOLD_IN_CLIP, seconds, tracks)];
  return { model, nodes, clips, tracks };
}
const vectorNear = (actual, expected) => assert.ok(actual.distanceTo(new Vector3().fromArray(expected)) < 1e-6);
const quaternionNear = (actual, expected) => assert.ok(actual.angleTo(expected) < .001);
function extended({ bar, fabric, roller, arm }) {
  assert.deepEqual(bar.position.toArray(), away);
  assert.deepEqual(fabric.scale.toArray(), full);
  assert.deepEqual(roller.quaternion.toArray(), start.toArray());
  assert.deepEqual(arm.quaternion.toArray(), start.toArray());
}
function finished({ bar, fabric, roller, arm }) {
  vectorNear(bar.position, parked);
  vectorNear(fabric.scale, gathered);
  quaternionNear(roller.quaternion, end);
  quaternionNear(arm.quaternion, end);
}

test("awning is exact ID only, preserving the parcel and beverage-return models", () => {
  assert.equal(interactionKind({ id: "shophouse-retractable-fabric-awning" }), "awning");
  assert.equal(interactionKind({ id: "shophouse-retractable-fabric-awning-variant" }), null);
  assert.equal(interactionKind({ id: "awning" }), null);
  assert.equal(interactionKind({ id: "shophouse-parcel-drop-hatch" }), "parcel-hatch");
  assert.equal(interactionKind({ id: "community-beverage-container-return-kiosk" }), "beverage-return");
});

test("manual clip changes native bar, fabric, roller and optional arm without autoplay or moving the wall", () => {
  const { model, nodes, clips } = fixture();
  const states = [], motion = createAwningMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  extended(nodes);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 20; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(nodes.bar.position.z < away[2] && nodes.bar.position.z > parked[2]);
  assert.ok(nodes.fabric.scale.z < full[2] && nodes.fabric.scale.z > gathered[2]);
  assert.ok(nodes.roller.quaternion.angleTo(start) > .1 && nodes.roller.quaternion.angleTo(end) > .1);
  assert.ok(nodes.arm.quaternion.angleTo(start) > .1);
  assert.deepEqual(nodes.wall.position.toArray(), [0, 0, 0]);
  assert.deepEqual(nodes.wall.quaternion.toArray(), start.toArray());
  for (let i = 0; i < 35; i++) motion.update(.05, false);
  assert.equal(motion.update(.05, false), false);
  finished(nodes);
  assert.equal(motion.play(false), false);
  motion.reset();
  extended(nodes);
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["retracting", "complete", "ready"]);
});

test("reduced motion uses exact authored parked pose; interrupted reset and disposal restore the extended pose", () => {
  const { model, nodes, clips } = fixture();
  const states = [], motion = createAwningMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  finished(nodes);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  extended(nodes);
  motion.play(false);
  motion.update(.04, false);
  motion.reset();
  extended(nodes);
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  finished(nodes);
  motion.dispose();
  motion.dispose();
  extended(nodes);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "retracting", "ready", "retracting", "complete"]);
});

test("every required track and named node must exist with the right type; optional authored tracks are allowed", () => {
  const { model, clips, nodes, tracks } = fixture();
  const [bar, fabric, roller] = tracks;
  const wrongType = new VectorKeyframeTrack("AWNING_ROLLER.quaternion", [0, 1], [0, 0, 0, 1, 0, 0]);
  const probe = tracks => createAwningMotion(model, [new AnimationClip(AWNING_FOLD_IN_CLIP, seconds, tracks)]);
  probe([bar, fabric, roller]).dispose();
  assert.equal(createAwningMotion(model, []), null);
  for (const missing of [[bar, fabric], [bar, roller], [fabric, roller], [bar, fabric, wrongType], [bar, bar, fabric, roller]])
    assert.equal(probe(missing), null);
  assert.equal(createAwningMotion(model, [new AnimationClip("unrelated", seconds, tracks)]), null);
  model.remove(nodes.fabric);
  assert.equal(createAwningMotion(model, clips), null);
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
    const { model, nodes, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createAwningDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [retract, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["awning.title"]);
    assert.equal(disclaimer.textContent, messages.en["awning.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["awning.ready"]);
    assert.equal(retract.tag, "button");
    assert.equal(retract.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    retract.focus();
    retract.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["awning.retracting"]);
    retract.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["awning.complete"]);
    finished(nodes);
    reset.click();
    assert.equal(document.activeElement, retract);
    assert.equal(status.textContent, messages.en["awning.ready"]);
    extended(nodes);
    retract.click();
    finished(nodes);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    extended(nodes);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    retract.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createAwningDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["awning.unavailable"]);
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
  const keys = ["title", "disclaimer", "ready", "retracting", "complete", "unavailable", "retract", "reset"];
  for (const key of keys) {
    const localized = Object.values(messages).map(m => m[`awning.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
