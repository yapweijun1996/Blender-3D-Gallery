import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, QuaternionKeyframeTrack, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import { AIR_BALANG_POUR_CLIP, createAirBalangPourMotion } from "../src/air-balang/demo.js";

function fixture() {
  const model = new Group(), lever = new Group(), stream = new Group(), fill = new Group(), stall = new Group();
  lever.name = "AIR_BALANG_TAP_LEVER";
  stream.name = "AIR_BALANG_STREAM";
  fill.name = "AIR_BALANG_CUP_FILL";
  stream.scale.y = .0078125;
  fill.scale.y = .125;
  fill.position.y = .25;
  model.add(lever, stream, fill, stall);
  const clip = new AnimationClip(AIR_BALANG_POUR_CLIP, 2.25, [
    new QuaternionKeyframeTrack(lever.name + ".quaternion", [0, .35, 1.75, 2.25],
      [0, 0, 0, 1, .3826834324, 0, 0, .9238795325, .3826834324, 0, 0, .9238795325, 0, 0, 0, 1]),
    new VectorKeyframeTrack(stream.name + ".scale", [0, .35, .55, 1.75, 2.25],
      [1, .0078125, 1, 1, .0078125, 1, 1, 1, 1, 1, 1, 1, 1, .0078125, 1]),
    new VectorKeyframeTrack(fill.name + ".scale", [0, .55, 1.75, 2.25],
      [1, .125, 1, 1, .125, 1, 1, .75, 1, 1, .75, 1]),
    new VectorKeyframeTrack(fill.name + ".position", [0, .55, 1.75, 2.25],
      [0, .25, 0, 0, .25, 0, 0, .5, 0, 0, .5, 0]),
  ]);
  return { model, lever, stream, fill, stall, clip };
}

test("only the exact Air Balang catalog stall has pouring controls in three locales", () => {
  assert.equal(interactionKind({ id: "ramadan-bazaar-air-balang-stall" }), "air-balang");
  for (const id of ["air-balang-stall", "mall-coffee-counter", "hawker-stall-stainless-counter"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "mall-carpark-help-point" }), "carpark-help");
  assert.equal(interactionKind({ id: "malaysia-rail-reload-counter" }), "rail-reload");
  assert.equal(interactionKind({ id: "loh-hei-yee-sang-platter" }), "loh-hei");
  assert.equal(interactionKind({ id: "mall-ride-hail-pickup-bay" }), "pickup-bay");
  for (const strings of Object.values(messages)) {
    for (const key of ["title", "disclaimer", "ready", "pouring", "complete", "unavailable", "pour", "reset"])
      assert.ok(strings["airBalang." + key]);
  }
});

test("explicit pour moves the lever, runs the stream and fills the cup, then closes the tap", () => {
  const { model, lever, stream, fill, stall, clip } = fixture(), phases = [];
  const motion = createAirBalangPourMotion(model, [clip], phase => phases.push(phase));
  const rest = () => [lever.quaternion.x, stream.scale.y, fill.scale.y, fill.position.y];
  assert.equal(motion.phase, "ready");
  assert.equal(motion.update(.5, false), false);
  assert.deepEqual(rest(), [0, .0078125, .125, .25]);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(10, false), true, "background delta does not skip the clip");
  assert.ok(lever.quaternion.x > 0 && lever.quaternion.x < .3827);
  assert.equal(stream.scale.y, .0078125);
  for (let i = 0; i < 15; i++) motion.update(.05, false);
  assert.equal(motion.phase, "pouring");
  assert.ok(lever.quaternion.x > .38);
  assert.equal(stream.scale.y, 1);
  assert.ok(fill.scale.y > .125 && fill.scale.y < .75);
  for (let i = 0; i < 40; i++) motion.update(.05, false);
  assert.deepEqual(phases, ["pouring", "complete"]);
  assert.deepEqual(rest(), [0, .0078125, .75, .5], "lever shut, no stream, full cup");
  assert.deepEqual(stall.position.toArray(), [0, 0, 0]);
  assert.equal(motion.update(1, false), false);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.equal(motion.phase, "ready");
  assert.deepEqual(rest(), [0, .0078125, .125, .25]);
  assert.equal(motion.play(false), true);
  motion.update(.05, false);
  motion.reset();
  assert.deepEqual(rest(), [0, .0078125, .125, .25]);
  assert.equal(motion.update(.05, false), false);
  motion.dispose();
  motion.dispose();
  assert.equal(motion.play(false), false);
});

test("reduced motion at start or midway samples only the closed-tap, filled-cup final pose", () => {
  const { model, lever, stream, fill, clip } = fixture(), phases = [];
  const motion = createAirBalangPourMotion(model, [clip], phase => phases.push(phase));
  assert.equal(motion.play(true), true);
  assert.deepEqual(phases, ["complete"]);
  assert.equal(lever.quaternion.x, 0);
  assert.equal(stream.scale.y, .0078125);
  assert.equal(fill.scale.y, .75);
  motion.reset();
  motion.play(false);
  assert.equal(motion.update(.05, true), false);
  assert.deepEqual(phases, ["complete", "ready", "pouring", "complete"]);
  motion.dispose();
  assert.equal(fill.position.y, .25);
});

test("missing, unrelated or malformed named clip leaves a static fallback", () => {
  const { model, clip } = fixture();
  for (const clips of [[], [new AnimationClip("OTHER", 2.25, clip.tracks)],
    [new AnimationClip(AIR_BALANG_POUR_CLIP, 0, clip.tracks)], [new AnimationClip(AIR_BALANG_POUR_CLIP, 2.25, [])],
    [new AnimationClip(AIR_BALANG_POUR_CLIP, Infinity, clip.tracks)]])
    assert.equal(createAirBalangPourMotion(model, clips), null);
});
