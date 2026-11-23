import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack, Vector3, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import createParcelHatchDemo, { createParcelHatchMotion, PARCEL_HATCH_OPEN_CLIP } from "../src/parcel-hatch/demo.js";

const seconds = 1.8;
const angle = 70 * Math.PI / 180;
const start = new Quaternion();
const end = new Quaternion().setFromAxisAngle(new Vector3(1, 0, 0), angle);
function fixture() {
  const model = new Group();
  const flap = new Group();
  flap.name = "PARCEL_DROP_FLAP";
  const sample = new Group();
  sample.name = "PARCEL_DROP_SAMPLE";
  sample.position.set(.15, .4, -.1);
  model.add(flap, sample);
  const clip = new AnimationClip(PARCEL_HATCH_OPEN_CLIP, seconds, [
    new QuaternionKeyframeTrack("PARCEL_DROP_FLAP.quaternion", [0, 1.2, seconds],
      [...start.toArray(), ...end.toArray(), ...end.toArray()]),
  ]);
  return { model, flap, sample, clips: [clip] };
}
const near = (actual, reference) => assert.ok(actual.angleTo(reference) < .001,
  `expected ${actual.toArray()} to equal ${reference.toArray()}`);

test("parcel hatch is allowlisted by exact ID without affecting existing interactions", () => {
  for (const [id, expected] of Object.entries({
    "shophouse-parcel-drop-hatch": "parcel-hatch",
    "shophouse-parcel-drop-hatch-variant": null,
    "wooden-mooncake-mould-workboard": null,
    "wet-market-coconut-scraper": "coconut-scraper",
    "mall-carpark-help-point": "carpark-help",
    "malaysia-rail-reload-counter": "rail-reload",
    "mall-ride-hail-pickup-bay": "pickup-bay",
    "loh-hei-yee-sang-platter": "loh-hei",
  })) assert.equal(interactionKind({ id }), expected);
});

test("manual single play moves only the flap, holds open, then reset restores the closed pose", () => {
  const { model, flap, sample, clips } = fixture();
  const states = [];
  const demo = createParcelHatchMotion(model, clips, phase => states.push(phase));
  assert.equal(demo.update(1, false), false);
  near(flap.quaternion, start);
  assert.equal(demo.play(false), true);
  assert.equal(demo.play(false), false);
  for (let i = 0; i < 10; i++) assert.equal(demo.update(.05, false), true);
  assert.ok(flap.quaternion.angleTo(start) > 0.1);
  assert.ok(flap.quaternion.angleTo(end) > 0.1);
  assert.deepEqual(sample.position.toArray(), [.15, .4, -.1]);
  assert.deepEqual(sample.quaternion.toArray(), start.toArray());
  for (let i = 0; i < 30; i++) demo.update(.05, false);
  assert.equal(demo.update(2, false), false);
  near(flap.quaternion, end);
  assert.equal(demo.play(false), false);
  demo.reset();
  near(flap.quaternion, start);
  assert.deepEqual(states, ["opening", "complete", "ready"]);
});

test("reduced motion and preference change settle at the actual final pose; interrupted play resets and disposes", () => {
  const { model, flap, clips } = fixture();
  const states = [];
  const demo = createParcelHatchMotion(model, clips, phase => states.push(phase));
  assert.equal(demo.play(true), true);
  near(flap.quaternion, end);
  assert.deepEqual(states, ["complete"]);
  demo.reset();
  near(flap.quaternion, start);
  demo.play(false);
  demo.update(.04, false);
  demo.reset();
  near(flap.quaternion, start);
  assert.equal(demo.update(5, false), false);
  demo.play(false);
  demo.update(.03, false);
  assert.equal(demo.update(.03, true), false);
  near(flap.quaternion, end);
  demo.dispose();
  demo.dispose();
  near(flap.quaternion, start);
  assert.equal(demo.play(false), false);
  assert.equal(demo.update(.01, false), false);
  demo.reset();
  assert.deepEqual(states, ["complete", "ready", "opening", "ready", "opening", "complete"]);
});

test("missing node or wrong motion contract leaves the native model unchanged", () => {
  const { model, clips, flap } = fixture();
  const sampleTrack = new VectorKeyframeTrack("PARCEL_DROP_SAMPLE.position", [0, 1], [0, 0, 0, 1, 0, 0]);
  assert.equal(createParcelHatchMotion(model, []), null);
  assert.equal(createParcelHatchMotion(model, [new AnimationClip("unrelated", seconds, clips[0].tracks)]), null);
  assert.equal(createParcelHatchMotion(model, [new AnimationClip(PARCEL_HATCH_OPEN_CLIP, seconds, [sampleTrack])]), null);
  assert.equal(createParcelHatchMotion(model,
    [new AnimationClip(PARCEL_HATCH_OPEN_CLIP, seconds, [...clips[0].tracks, sampleTrack])]), null);
  model.remove(flap);
  assert.equal(createParcelHatchMotion(model, clips), null);
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
    const { model, flap, clips } = fixture();
    const container = new Element("div");
    let renders = 0;
    const demo = createParcelHatchDemo({ model, clips, container, invalidate: () => renders++ });
    const toolbar = container.toolbar;
    const [, disclaimer, status, buttonRow] = toolbar.children;
    const [open, reset] = buttonRow.children;
    assert.equal(toolbar.getAttribute("role"), "group");
    assert.equal(toolbar.getAttribute("aria-label"), messages.en["parcelHatch.title"]);
    assert.equal(disclaimer.textContent, messages.en["parcelHatch.disclaimer"]);
    assert.equal(status.getAttribute("role"), "status");
    assert.equal(status.textContent, messages.en["parcelHatch.ready"]);
    assert.equal(open.tag, "button");
    assert.equal(open.type, "button");
    assert.equal(reset.type, "button");
    assert.equal(reset.disabled, true);
    open.focus();
    open.click();
    assert.equal(document.activeElement, reset);
    assert.equal(status.textContent, messages.en["parcelHatch.opening"]);
    open.click();
    assert.equal(renders, 1);
    preference.matches = true;
    assert.equal(demo.update(.02), false);
    assert.equal(status.textContent, messages.en["parcelHatch.complete"]);
    near(flap.quaternion, end);
    reset.click();
    assert.equal(document.activeElement, open);
    assert.equal(status.textContent, messages.en["parcelHatch.ready"]);
    near(flap.quaternion, start);
    open.click();
    near(flap.quaternion, end);
    demo.reset(); // The independent viewer Reset invokes the same exact pose reset.
    near(flap.quaternion, start);
    demo.dispose();
    assert.equal(toolbar.removed, true);
    const stoppedRenders = renders;
    open.click();
    assert.equal(renders, stoppedRenders);
    const fallback = createParcelHatchDemo({ model, clips: [], container, invalidate: () => renders++ });
    assert.equal(container.toolbar.dataset.state, "unavailable");
    assert.equal(container.toolbar.children[2].textContent, messages.en["parcelHatch.unavailable"]);
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
    const localized = Object.values(messages).map(m => m[`parcelHatch.${key}`]);
    assert.ok(localized.every(value => typeof value === "string" && value.trim() !== ""));
    assert.equal(new Set(localized).size, 3);
  }
});
