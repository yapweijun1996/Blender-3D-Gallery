import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createDacingDemo, { createDacingMotion, DACING_FIND_BALANCE_CLIP } from "../src/dacing/demo.js";

const seconds = 2.2;
const level = new Quaternion();
const tilt = new Quaternion().setFromAxisAngle(new Vector3(0, 0, 1), Math.PI / 20);
const correction = tilt.clone().invert();
const ready = [.15, 0, 0], parked = [.40, 0, 0];
function fixture() {
  const model = new Group(), nodes = {};
  for (const [key, name] of Object.entries({ beam: "DACING_BEAM", counterweight: "DACING_COUNTERWEIGHT",
    pan: "DACING_PAN_SWIVEL", poise: "DACING_POISE_SWIVEL", sample: "DACING_SAMPLE", stand: "STAND" })) {
    nodes[key] = new Group();
    nodes[key].name = name;
  }
  model.add(nodes.stand, nodes.beam);
  nodes.beam.add(nodes.pan, nodes.counterweight);
  nodes.pan.add(nodes.sample);
  nodes.counterweight.add(nodes.poise);
  nodes.beam.quaternion.copy(tilt);
  nodes.counterweight.position.fromArray(ready);
  nodes.pan.quaternion.copy(correction);
  nodes.poise.quaternion.copy(correction);
  nodes.sample.position.set(0, -.2, 0);
  const tracks = [
    new QuaternionKeyframeTrack("DACING_BEAM.quaternion", [0, seconds], [...tilt.toArray(), ...level.toArray()]),
    new VectorKeyframeTrack("DACING_COUNTERWEIGHT.position", [0, seconds], [...ready, ...parked]),
    new QuaternionKeyframeTrack("DACING_PAN_SWIVEL.quaternion", [0, seconds], [...correction.toArray(), ...level.toArray()]),
    new QuaternionKeyframeTrack("DACING_POISE_SWIVEL.quaternion", [0, seconds], [...correction.toArray(), ...level.toArray()]),
  ];
  const clips = [new AnimationClip(DACING_FIND_BALANCE_CLIP, seconds, tracks)];
  return { model, nodes, clips, tracks };
}
const near = (actual, expected) => assert.ok(actual.angleTo(expected) < .001);
function tilted({ beam, counterweight, pan, poise }) {
  assert.deepEqual(beam.quaternion.toArray(), tilt.toArray());
  assert.deepEqual(counterweight.position.toArray(), ready);
  assert.deepEqual(pan.quaternion.toArray(), correction.toArray());
  assert.deepEqual(poise.quaternion.toArray(), correction.toArray());
}
function finished({ beam, counterweight, pan, poise }) {
  near(beam.quaternion, level);
  assert.ok(counterweight.position.distanceTo(new Vector3().fromArray(parked)) < 1e-6);
  near(pan.quaternion, level);
  near(poise.quaternion, level);
}

test("dacing is exact ID only; previous demos and the existing dial scale are unchanged", () => {
  assert.equal(interactionKind({ id: "pasar-dacing-steelyard-scale" }), "dacing");
  for (const id of ["pasar-dacing-steelyard-scale-variant", "local-wet-market-weighing-scale", "dacing"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "shophouse-retractable-fabric-awning" }), "awning");
  assert.equal(interactionKind({ id: "shophouse-parcel-drop-hatch" }), "parcel-hatch");
  assert.equal(interactionKind({ id: "community-beverage-container-return-kiosk" }), "beverage-return");
});

test("manual balance translates weight along beam and levels it while sample and poise stay upright", () => {
  const { model, nodes, clips } = fixture();
  const states = [], motion = createDacingMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  tilted(nodes);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 20; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(nodes.beam.quaternion.angleTo(tilt) > .01 && nodes.beam.quaternion.angleTo(level) > .01);
  const x = nodes.counterweight.position.x;
  assert.ok(x > ready[0] && x < parked[0]);
  assert.equal(nodes.counterweight.position.y, 0);
  assert.equal(nodes.counterweight.position.z, 0);
  near(nodes.sample.getWorldQuaternion(new Quaternion()), level);
  near(nodes.poise.getWorldQuaternion(new Quaternion()), level);
  assert.deepEqual(nodes.sample.position.toArray(), [0, -.2, 0]);
  assert.deepEqual(nodes.stand.position.toArray(), [0, 0, 0]);
  for (let i = 0; i < 30; i++) motion.update(.05, false);
  assert.equal(motion.update(.05, false), false);
  finished(nodes);
  assert.equal(motion.play(false), false);
  motion.reset();
  tilted(nodes);
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["balancing", "complete", "ready"]);
});

test("reduced motion uses the authored level pose; interrupted reset and disposal restore the original tilt", () => {
  const { model, nodes, clips } = fixture();
  const states = [], motion = createDacingMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  finished(nodes);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  tilted(nodes);
  motion.play(false);
  motion.update(.04, false);
  motion.reset();
  tilted(nodes);
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  finished(nodes);
  motion.dispose();
  motion.dispose();
  tilted(nodes);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "balancing", "ready", "balancing", "complete"]);
});

test("all three exact named bindings require matching types; the authored poise swivel may also animate", () => {
  const { model, clips, nodes, tracks } = fixture();
  const [beam, weight, pan] = tracks;
  const wrongType = new VectorKeyframeTrack("DACING_PAN_SWIVEL.quaternion", [0, 1], [0, 0, 0, 1, 0, 0]);
  const probe = tracks => createDacingMotion(model, [new AnimationClip(DACING_FIND_BALANCE_CLIP, seconds, tracks)]);
  probe([beam, weight, pan]).dispose();
  assert.equal(createDacingMotion(model, []), null);
  for (const invalid of [[beam, weight], [beam, pan], [weight, pan], [beam, weight, wrongType], [beam, weight, pan, pan]])
    assert.equal(probe(invalid), null);
  assert.equal(createDacingMotion(model, [new AnimationClip("unrelated", seconds, tracks)]), null);
  nodes.beam.remove(nodes.pan);
  assert.equal(createDacingMotion(model, clips), null);
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
    const demo = createDacingDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [balance, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["dacing.title"]);
    assert.equal(disclaimer.textContent, messages.en["dacing.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["dacing.ready"]);
    assert.equal(balance.tag, "button");
    assert.equal(balance.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    balance.focus();
    balance.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["dacing.balancing"]);
    balance.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["dacing.complete"]);
    finished(nodes);
    reset.click();
    assert.equal(document.activeElement, balance);
    assert.equal(status.textContent, messages.en["dacing.ready"]);
    tilted(nodes);
    balance.click();
    finished(nodes);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    tilted(nodes);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    balance.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createDacingDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["dacing.unavailable"]);
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
  const keys = ["title", "disclaimer", "ready", "balancing", "complete", "unavailable", "balance", "reset"];
  for (const key of keys) {
    const localized = Object.values(messages).map(m => m[`dacing.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
