import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createTrayReturnCoverDemo, { createTrayReturnCoverMotion, TRAY_RETURN_COVER_LIFT_CLIP } from "../src/tray-return-cover/demo.js";

const seconds = 2.2;
const origin = new Quaternion();
const rotated = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), Math.PI / 2);
function fixture() {
  const model = new Group(), cover = new Group(), weight = new Group(), pulley = new Group(), cable = new Group(), housing = new Group();
  cover.name = "TRAY_RETURN_COVER";
  weight.name = "TRAY_RETURN_COUNTERWEIGHT";
  pulley.name = "TRAY_RETURN_PULLEY";
  cable.name = "TRAY_RETURN_CABLE";
  cover.position.y = .4;
  weight.position.y = 1.2;
  model.add(cover, weight, pulley, cable, housing);
  const tracks = [
    new VectorKeyframeTrack("TRAY_RETURN_COVER.position", [0, 1.9, seconds], [0, .4, 0, 0, .75, 0, 0, .75, 0]),
    new VectorKeyframeTrack("TRAY_RETURN_COUNTERWEIGHT.position", [0, 1.9, seconds], [0, 1.2, 0, 0, .85, 0, 0, .85, 0]),
    new QuaternionKeyframeTrack("TRAY_RETURN_PULLEY.quaternion", [0, seconds], [...origin.toArray(), ...rotated.toArray()]),
    new VectorKeyframeTrack("TRAY_RETURN_CABLE.scale", [0, seconds], [1, 1, 1, 1, .5, 1]),
  ];
  return { model, cover, weight, pulley, cable, housing, tracks,
    clips: [new AnimationClip(TRAY_RETURN_COVER_LIFT_CLIP, seconds, tracks)] };
}
const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-6);
function assertPose(cover, weight, opened) {
  near(cover.position.y, opened ? .75 : .4);
  near(weight.position.y, opened ? .85 : 1.2);
  assert.equal(cover.position.x, 0);
  assert.equal(weight.position.x, 0);
}

test("only the exact asset unlocks the tray return demo; previous fixture IDs are unchanged", () => {
  assert.equal(interactionKind({ id: "hawker-tray-return-counterweight-cover" }), "tray-return-cover");
  for (const id of ["tray-return-cover", "hawker-tray-return-counterweight-cover-variant", "hawker-stall-queue-sign"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "mall-fold-down-changing-station" }), "changing-station");
  assert.equal(interactionKind({ id: "pasar-dacing-steelyard-scale" }), "dacing");
});

test("manual one-shot moves cover and weight oppositely, retaining optional pulley and cable tracks in full clip", () => {
  const { model, cover, weight, pulley, cable, housing, clips } = fixture();
  const states = [], motion = createTrayReturnCoverMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  assertPose(cover, weight, false);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 20; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(.4 < cover.position.y && cover.position.y < .75);
  assert.ok(.85 < weight.position.y && weight.position.y < 1.2);
  near(cover.position.y + weight.position.y, 1.6);
  assert.ok(pulley.quaternion.angleTo(origin) > .1);
  assert.ok(.5 < cable.scale.y && cable.scale.y < 1);
  assert.deepEqual(housing.position.toArray(), [0, 0, 0]);
  for (let i = 0; i < 30; i++) motion.update(.05, false);
  assert.equal(motion.update(1, false), false);
  assertPose(cover, weight, true);
  near(pulley.quaternion.clone().normalize().angleTo(rotated), 0);
  near(cable.scale.y, .5);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.deepEqual(cover.position.toArray(), [0, .4, 0]);
  assert.deepEqual(weight.position.toArray(), [0, 1.2, 0]);
  assert.deepEqual(pulley.quaternion.toArray(), origin.toArray());
  assert.deepEqual(cable.scale.toArray(), [1, 1, 1]);
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["opening", "complete", "ready"]);
});

test("reduced final is immediate; live preference changes, interrupted reset and disposal restore correctly", () => {
  const { model, cover, weight, clips } = fixture();
  const states = [], motion = createTrayReturnCoverMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  assertPose(cover, weight, true);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  assertPose(cover, weight, false);
  motion.play(false);
  for (let i = 0; i < 8; i++) motion.update(.05, false);
  motion.reset();
  assertPose(cover, weight, false);
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  assertPose(cover, weight, true);
  motion.dispose();
  motion.dispose();
  assertPose(cover, weight, false);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "opening", "ready", "opening", "complete"]);
});

test("both named tracks require actual VectorKeyframeTrack instances and nodes; an optional track is never required", () => {
  const { model, cover, tracks, clips } = fixture();
  const [coverTrack, weightTrack] = tracks;
  const mislabeled = new QuaternionKeyframeTrack("TRAY_RETURN_COVER.position", [0, 1],
    [...origin.toArray(), ...rotated.toArray()]);
  const create = tracks => createTrayReturnCoverMotion(model, [new AnimationClip(TRAY_RETURN_COVER_LIFT_CLIP, seconds, tracks)]);
  create([coverTrack, weightTrack]).dispose();
  assert.equal(createTrayReturnCoverMotion(model, []), null);
  for (const invalid of [[], [coverTrack], [weightTrack], [mislabeled, weightTrack], [coverTrack, weightTrack, weightTrack]])
    assert.equal(create(invalid), null);
  assert.equal(createTrayReturnCoverMotion(model, [new AnimationClip("unrelated", seconds, tracks)]), null);
  model.remove(cover);
  assert.equal(createTrayReturnCoverMotion(model, clips), null);
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
    const { model, cover, weight, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createTrayReturnCoverDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [open, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["trayReturnCover.title"]);
    assert.equal(disclaimer.textContent, messages.en["trayReturnCover.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["trayReturnCover.ready"]);
    assert.equal(open.tag, "button");
    assert.equal(open.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    open.focus();
    open.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["trayReturnCover.opening"]);
    open.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["trayReturnCover.complete"]);
    assertPose(cover, weight, true);
    reset.click();
    assert.equal(document.activeElement, open);
    assert.equal(status.textContent, messages.en["trayReturnCover.ready"]);
    assertPose(cover, weight, false);
    open.click();
    assertPose(cover, weight, true);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    assertPose(cover, weight, false);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    open.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createTrayReturnCoverDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["trayReturnCover.unavailable"]);
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
  const keys = ["title", "disclaimer", "ready", "opening", "complete", "unavailable", "open", "reset"];
  for (const key of keys) {
    const localized = Object.values(messages).map(m => m[`trayReturnCover.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
