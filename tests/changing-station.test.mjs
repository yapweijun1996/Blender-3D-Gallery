import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createChangingStationDemo, { createChangingStationMotion, CHANGING_STATION_UNFOLD_CLIP } from "../src/changing-station/demo.js";

const seconds = 2.2;
const level = new Quaternion();
const folded = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), -Math.PI / 2);
function fixture() {
  const model = new Group(), hinge = new Group(), housing = new Group();
  hinge.name = "CHANGING_DECK_HINGE";
  housing.name = "CHANGING_STATION_HOUSING";
  hinge.quaternion.copy(folded);
  model.add(hinge, housing);
  const track = new QuaternionKeyframeTrack("CHANGING_DECK_HINGE.quaternion", [0, .1, 1.9, seconds],
    [...folded.toArray(), ...folded.toArray(), ...level.toArray(), ...level.toArray()]);
  return { model, hinge, housing, track, clips: [new AnimationClip(CHANGING_STATION_UNFOLD_CLIP, seconds, [track])] };
}
const near = (actual, expected) => assert.ok(actual.angleTo(expected) < .001);

test("only the exact asset enables the changing-station demo, with other allowlisted models unchanged", () => {
  assert.equal(interactionKind({ id: "mall-fold-down-changing-station" }), "changing-station");
  for (const id of ["changing-station", "mall-fold-down-changing-station-variant", "retail-stroller-rental-station"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "pasar-dacing-steelyard-scale" }), "dacing");
  assert.equal(interactionKind({ id: "shophouse-retractable-fabric-awning" }), "awning");
});

test("manual single play moves only the hinge, holds at open and never restarts without reset", () => {
  const { model, hinge, housing, clips } = fixture();
  const states = [], motion = createChangingStationMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.update(1, false), false);
  assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  for (let i = 0; i < 20; i++) assert.equal(motion.update(.05, false), true);
  assert.ok(hinge.quaternion.angleTo(folded) > .01 && hinge.quaternion.angleTo(level) > .01);
  assert.deepEqual(housing.position.toArray(), [0, 0, 0]);
  assert.deepEqual(housing.quaternion.toArray(), level.toArray());
  for (let i = 0; i < 30; i++) motion.update(.05, false);
  assert.equal(motion.update(.05, false), false);
  near(hinge.quaternion, level);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
  assert.equal(motion.update(2, false), false);
  assert.deepEqual(states, ["opening", "complete", "ready"]);
});

test("reduced motion immediately opens; interrupted reset and dispose restore the exact folded pose", () => {
  const { model, hinge, clips } = fixture();
  const states = [], motion = createChangingStationMotion(model, clips, phase => states.push(phase));
  assert.equal(motion.play(true), true);
  near(hinge.quaternion, level);
  assert.deepEqual(states, ["complete"]);
  motion.reset();
  assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
  motion.play(false);
  for (let i = 0; i < 8; i++) motion.update(.05, false);
  motion.reset();
  assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
  assert.equal(motion.update(5, false), false);
  motion.play(false);
  motion.update(.03, false);
  assert.equal(motion.update(.03, true), false);
  near(hinge.quaternion, level);
  motion.dispose();
  motion.dispose();
  assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(.01, false), false);
  motion.reset();
  assert.deepEqual(states, ["complete", "ready", "opening", "ready", "opening", "complete"]);
});

test("reject missing/extra tracks, wrong class or name, and absent hinge without moving the static fixture", () => {
  const { model, hinge, track, clips } = fixture();
  const mislabeled = new VectorKeyframeTrack("CHANGING_DECK_HINGE.quaternion", [0, 1], [0, 0, 0, 1, 0, 0]);
  const unrelated = new QuaternionKeyframeTrack("CHANGING_STATION_HOUSING.quaternion", [0, 1],
    [...folded.toArray(), ...level.toArray()]);
  const create = tracks => createChangingStationMotion(model, [new AnimationClip(CHANGING_STATION_UNFOLD_CLIP, seconds, tracks)]);
  assert.equal(createChangingStationMotion(model, []), null);
  for (const invalid of [[], [mislabeled], [unrelated], [track, unrelated]]) assert.equal(create(invalid), null);
  assert.equal(createChangingStationMotion(model, [new AnimationClip("unrelated", seconds, [track])]), null);
  model.remove(hinge);
  assert.equal(createChangingStationMotion(model, clips), null);
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
    const { model, hinge, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createChangingStationDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [open, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["changingStation.title"]);
    assert.equal(disclaimer.textContent, messages.en["changingStation.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["changingStation.ready"]);
    assert.equal(open.tag, "button");
    assert.equal(open.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    open.focus();
    open.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["changingStation.opening"]);
    open.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["changingStation.complete"]);
    near(hinge.quaternion, level);
    reset.click();
    assert.equal(document.activeElement, open);
    assert.equal(status.textContent, messages.en["changingStation.ready"]);
    assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
    open.click();
    near(hinge.quaternion, level);
    demo.reset(); // Standard viewer Reset invokes the same exact pose reset.
    assert.deepEqual(hinge.quaternion.toArray(), folded.toArray());
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    open.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createChangingStationDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["changingStation.unavailable"]);
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
    const localized = Object.values(messages).map(m => m[`changingStation.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
