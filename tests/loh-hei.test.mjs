import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, BoxGeometry, Group, Mesh, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { createTossMotion, TOSS_CLIP } from "../src/loh-hei/demo.js";
import { interactionKind } from "../src/model-interaction.js";

const fixture = () => {
  const model = new Group();
  const pile = new Mesh(new BoxGeometry(.2, .1, .2));
  const plate = new Mesh(new BoxGeometry(1, .2, 1));
  pile.name = "pile";
  model.add(plate, pile);
  const clip = new AnimationClip(TOSS_CLIP, 2, [
    new VectorKeyframeTrack("pile.position", [0, 1, 2], [0,0,0, .4,.5,0, .7,0,0]),
  ]);
  return { model, pile, plate, clip };
};

test("the exact Lo Hei platter alone gets a toss control in all three locales", () => {
  assert.equal(interactionKind({ id: "loh-hei-yee-sang-platter" }), "loh-hei");
  for (const id of ["yee-sang", "loh-hei", "hatchback-car", "dining-table"])
    assert.equal(interactionKind({ id }), null);
  for (const strings of Object.values(messages)) {
    for (const key of ["title", "ready", "tossing", "mixed", "unavailable", "toss", "reset"])
      assert.ok(strings["lohHei." + key]);
  }
});

test("plays once only on explicit toss, holds mixed pose, and resets to authored rest", () => {
  const { model, pile, plate, clip } = fixture(), states = [];
  const motion = createTossMotion(model, [clip], value => states.push(value));
  assert.equal(motion.phase, "ready");
  assert.deepEqual(pile.position.toArray(), [0, 0, 0]);
  assert.equal(motion.update(.1, false), false);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  assert.equal(motion.phase, "tossing");
  assert.ok(motion.bounds.max.y >= .54, "viewer will frame the high sample");
  assert.ok(motion.update(10, false), "large hidden-tab elapsed value does not skip playback");
  assert.ok(pile.position.y > 0 && pile.position.y < .05);
  for (let i=0; i<60; i++) motion.update(.05, false);
  assert.equal(motion.phase, "mixed");
  assert.equal(motion.update(.05, false), false);
  assert.ok(Math.abs(pile.position.x-.7)<.00001);
  assert.deepEqual(plate.position.toArray(), [0,0,0]);
  assert.deepEqual(states, ["tossing", "mixed"]);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.equal(motion.phase, "ready");
  assert.equal(motion.bounds, undefined);
  assert.deepEqual(pile.position.toArray(), [0,0,0]);
  assert.equal(motion.play(false), true);
  motion.update(.05,false);
  motion.reset();
  assert.deepEqual(pile.position.toArray(), [0,0,0]);
  assert.equal(motion.update(.25,false), false);
  motion.dispose();
  assert.equal(motion.play(false), false);
});

test("reduced motion samples the mixed pose at once and remains resettable", () => {
  const { model, pile, clip } = fixture(), states = [];
  const motion = createTossMotion(model, [clip], value => states.push(value));
  assert.equal(motion.play(true), true);
  assert.deepEqual(states, ["mixed"], "no animated state");
  assert.ok(Math.abs(pile.position.x-.7)<.00001);
  motion.reset();
  assert.deepEqual(pile.position.toArray(), [0,0,0]);
  motion.play(false);
  assert.equal(motion.update(.05, true), false, "preference change immediately settles the pose");
  assert.equal(motion.phase, "mixed");
  motion.dispose();
});

test("no valid authored toss clip leaves the interaction unavailable", () => {
  const { model, clip } = fixture();
  assert.equal(createTossMotion(model, []), null);
  assert.equal(createTossMotion(model, [new AnimationClip("other", 2, clip.tracks)]), null);
  assert.equal(createTossMotion(model, [new AnimationClip(TOSS_CLIP, 0, clip.tracks)]), null);
});
