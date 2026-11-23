import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import { CARD_TAP_CLIP, createCardTapMotion } from "../src/rail-reload/demo.js";

function fixture() {
  const model = new Group();
  const card = new Group();
  const indicator = new Group();
  const booth = new Group();
  card.name = "RAIL_DEMO_CARD";
  indicator.name = "RAIL_READER_INDICATOR";
  card.position.set(0, 0, .25);
  indicator.scale.setScalar(.125);
  model.add(card, indicator, booth);
  const clip = new AnimationClip(CARD_TAP_CLIP, 2, [
    new VectorKeyframeTrack(`${card.name}.position`, [0, 1, 2], [0, 0, .25, .25, .125, .125, .5, 0, 0]),
    new VectorKeyframeTrack(`${indicator.name}.scale`, [0, 1, 2], [.125, .125, .125, .125, .125, .125, 1, 1, 1]),
  ]);
  return { model, card, indicator, booth, clip };
}

test("only the exact Malaysian rail booth advertises a rail-reload model interaction", () => {
  assert.equal(interactionKind({ id: "malaysia-rail-reload-counter" }), "rail-reload");
  for (const id of ["ticket-machine", "train-ticket-gate", "bus-fare-card-reader", "rail-reload-counter"])
    assert.equal(interactionKind({ id }), null);
  for (const strings of Object.values(messages)) {
    for (const k of ["title", "disclaimer", "ready", "tapping", "complete", "unavailable", "tap", "reset"])
      assert.ok(strings["railReload." + k]);
  }
});

test("plays only on tap, holds final card and indicator, and resets the authored scene", () => {
  const { model, card, indicator, booth, clip } = fixture(), states = [];
  const motion = createCardTapMotion(model, [clip], value => states.push(value));
  assert.equal(motion.phase, "ready");
  assert.equal(motion.update(1, false), false);
  assert.deepEqual(card.position.toArray(), [0, 0, .25]);
  assert.deepEqual(indicator.scale.toArray(), [.125, .125, .125]);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(10, false), true, "long background intervals do not skip the clip");
  assert.ok(card.position.x > 0 && card.position.x < .05);
  for (let i = 0; i < 60; i++) motion.update(.05, false);
  assert.deepEqual(states, ["tapping", "complete"]);
  assert.deepEqual(card.position.toArray(), [.5, 0, 0]);
  assert.deepEqual(indicator.scale.toArray(), [1, 1, 1]);
  assert.deepEqual(booth.position.toArray(), [0, 0, 0]);
  assert.equal(motion.update(1, false), false);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.equal(motion.phase, "ready");
  assert.deepEqual(card.position.toArray(), [0, 0, .25]);
  assert.deepEqual(indicator.scale.toArray(), [.125, .125, .125]);
  assert.equal(motion.play(false), true);
  motion.update(.05, false);
  motion.reset();
  assert.deepEqual(card.position.toArray(), [0, 0, .25]);
  assert.equal(motion.update(.05, false), false);
  motion.dispose();
  motion.dispose();
  assert.equal(motion.play(true), false);
});

test("reduced motion and a mid-play preference change settle immediately", () => {
  const { model, card, indicator, clip } = fixture(), states = [];
  const motion = createCardTapMotion(model, [clip], value => states.push(value));
  assert.equal(motion.play(true), true);
  assert.deepEqual(states, ["complete"]);
  assert.deepEqual(card.position.toArray(), [.5, 0, 0]);
  assert.deepEqual(indicator.scale.toArray(), [1, 1, 1]);
  motion.reset();
  motion.play(false);
  assert.equal(motion.update(.05, true), false);
  assert.deepEqual(states, ["complete", "ready", "tapping", "complete"]);
  motion.dispose();
  assert.deepEqual(card.position.toArray(), [0, 0, .25]);
});

test("missing, unrelated, or invalid named clips leave the ordinary model usable", () => {
  const { model, clip } = fixture();
  for (const clips of [[], [new AnimationClip("OTHER", 2, clip.tracks)],
    [new AnimationClip(CARD_TAP_CLIP, 0, clip.tracks)], [new AnimationClip(CARD_TAP_CLIP, 2, [])],
    [new AnimationClip(CARD_TAP_CLIP, Infinity, clip.tracks)]])
    assert.equal(createCardTapMotion(model, clips), null);
});
