import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, Quaternion, QuaternionKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import { KELAPA_CRANK_TURN_CLIP, createCoconutCrankMotion } from "../src/coconut-scraper/demo.js";

const radians = angle => angle * Math.PI / 180;
const crankQuaternion = angle => new Quaternion(Math.sin(radians(angle) / 2), 0, 0, Math.cos(radians(angle) / 2));
const assertPose = (node, angle) => assert.ok(
  Math.abs(Math.abs(node.quaternion.dot(crankQuaternion(angle))) - 1) < 1e-6,
  node.name + " must have the expected rotation",
);

function fixture() {
  const model = new Group(), crank = new Group(), rotor = new Group(), bowl = new Group(), base = new Group();
  crank.name = "KELAPA_CRANK_HANDLE";
  rotor.name = "KELAPA_SCRAPER_ROTOR";
  bowl.position.set(-.25, 0, .5);
  model.add(crank, rotor, bowl, base);
  const ts = [0, .5, 1, 1.5, 2];
  const samples = turns => ts.flatMap(t => crankQuaternion(turns * t / 2).toArray());
  const clip = new AnimationClip(KELAPA_CRANK_TURN_CLIP, 2, [
    new QuaternionKeyframeTrack(crank.name + ".quaternion", ts, samples(270)),
    new QuaternionKeyframeTrack(rotor.name + ".quaternion", ts, samples(-540)),
  ]);
  return { model, crank, rotor, bowl, base, clip };
}

test("only the exact coconut scraper gets the crank demo in three locales", () => {
  assert.equal(interactionKind({ id: "wet-market-coconut-scraper" }), "coconut-scraper");
  for (const id of ["coconut-scraper", "coconut", "wet-market-fish-counter", "local-wet-market-weighing-scale"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "ramadan-bazaar-air-balang-stall" }), "air-balang");
  assert.equal(interactionKind({ id: "mall-carpark-help-point" }), "carpark-help");
  assert.equal(interactionKind({ id: "malaysia-rail-reload-counter" }), "rail-reload");
  assert.equal(interactionKind({ id: "loh-hei-yee-sang-platter" }), "loh-hei");
  assert.equal(interactionKind({ id: "mall-ride-hail-pickup-bay" }), "pickup-bay");
  for (const strings of Object.values(messages)) {
    for (const key of ["title", "disclaimer", "ready", "turning", "complete", "unavailable", "turn", "reset"])
      assert.ok(strings["coconutScraper." + key]);
  }
});

test("explicit turn plays both opposing rotations, leaves a distinct final pose, and resets", () => {
  const { model, crank, rotor, bowl, base, clip } = fixture(), phases = [];
  const motion = createCoconutCrankMotion(model, [clip], phase => phases.push(phase));
  assert.equal(motion.phase, "ready");
  assert.equal(motion.update(.5, false), false);
  assertPose(crank, 0); assertPose(rotor, 0);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(10, false), true, "background delta capped at .05s");
  assertPose(crank, 6.75); assertPose(rotor, -13.5);
  for (let i = 0; i < 19; i++) motion.update(.05, false);
  assert.equal(motion.phase, "turning");
  assertPose(crank, 135); assertPose(rotor, -270);
  for (let i = 0; i < 30; i++) motion.update(.05, false);
  assert.deepEqual(phases, ["turning", "complete"]);
  assertPose(crank, 270); assertPose(rotor, -540);
  assert.deepEqual(bowl.position.toArray(), [-.25, 0, .5]);
  assertPose(bowl, 0); assertPose(base, 0);
  assert.equal(motion.update(.5, false), false);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.equal(motion.phase, "ready");
  assertPose(crank, 0); assertPose(rotor, 0);
  assert.equal(motion.play(false), true);
  motion.update(.05, false);
  motion.reset();
  assertPose(crank, 0); assertPose(rotor, 0);
  assert.equal(motion.update(.05, false), false);
  motion.dispose();
  motion.dispose();
  assert.equal(motion.play(false), false);
});

test("reduced motion at start or during play samples the distinct final orientations only", () => {
  const { model, crank, rotor, clip } = fixture(), phases = [];
  const motion = createCoconutCrankMotion(model, [clip], phase => phases.push(phase));
  assert.equal(motion.play(true), true);
  assert.deepEqual(phases, ["complete"]);
  assertPose(crank, 270); assertPose(rotor, -540);
  motion.reset();
  motion.play(false);
  assert.equal(motion.update(.05, true), false);
  assert.deepEqual(phases, ["complete", "ready", "turning", "complete"]);
  motion.dispose();
  assertPose(crank, 0); assertPose(rotor, 0);
});

test("missing, unrelated or malformed named clip leaves a static fallback", () => {
  const { model, clip } = fixture();
  for (const clips of [[], [new AnimationClip("OTHER", 2, clip.tracks)],
    [new AnimationClip(KELAPA_CRANK_TURN_CLIP, 0, clip.tracks)], [new AnimationClip(KELAPA_CRANK_TURN_CLIP, 2, [])],
    [new AnimationClip(KELAPA_CRANK_TURN_CLIP, Infinity, clip.tracks)]])
    assert.equal(createCoconutCrankMotion(model, clips), null);
});
