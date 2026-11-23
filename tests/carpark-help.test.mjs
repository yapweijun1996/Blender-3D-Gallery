import assert from "node:assert/strict";
import test from "node:test";
import { AnimationClip, Group, VectorKeyframeTrack } from "three";
import { messages } from "../src/i18n/index.js";
import { interactionKind } from "../src/model-interaction.js";
import { HELP_PRESS_CLIP, createHelpPressMotion } from "../src/carpark-help/demo.js";

function fixture() {
  const model = new Group(), button = new Group(), indicator = new Group(), shell = new Group();
  button.name = "CARPARK_HELP_BUTTON";
  indicator.name = "CARPARK_HELP_INDICATOR";
  button.position.z = .125;
  indicator.position.z = .0625;
  model.add(button, indicator, shell);
  const clip = new AnimationClip(HELP_PRESS_CLIP, 1.5, [
    new VectorKeyframeTrack(button.name + ".position", [0, .25, .75, 1.5],
      [0, 0, .125, 0, 0, .1171875, 0, 0, .125, 0, 0, .125]),
    new VectorKeyframeTrack(indicator.name + ".position", [0, .75, 1, 1.5],
      [0, 0, .0625, 0, 0, .0625, 0, 0, .09375, 0, 0, .09375]),
  ]);
  return { model, button, indicator, shell, clip };
}

test("only the exact help-point pedestal gets this simulation in three locales", () => {
  assert.equal(interactionKind({ id: "mall-carpark-help-point" }), "carpark-help");
  for (const id of ["carpark-help-point", "car-park-ticket-machine", "singapore-traffic-signal-pole", "parking-barrier"])
    assert.equal(interactionKind({ id }), null);
  assert.equal(interactionKind({ id: "malaysia-rail-reload-counter" }), "rail-reload");
  assert.equal(interactionKind({ id: "loh-hei-yee-sang-platter" }), "loh-hei");
  assert.equal(interactionKind({ id: "mall-ride-hail-pickup-bay" }), "pickup-bay");
  for (const strings of Object.values(messages)) {
    for (const key of ["title", "disclaimer", "ready", "pressing", "complete", "unavailable", "press", "reset"])
      assert.ok(strings["carparkHelp." + key]);
  }
});

test("only an explicit press depresses and releases the button, leaving the indicator acknowledged", () => {
  const { model, button, indicator, shell, clip } = fixture(), phases = [];
  const motion = createHelpPressMotion(model, [clip], phase => phases.push(phase));
  assert.equal(motion.phase, "ready");
  assert.equal(motion.update(.5, false), false);
  assert.equal(button.position.z, .125);
  assert.equal(indicator.position.z, .0625);
  assert.equal(motion.play(false), true);
  assert.equal(motion.play(false), false);
  assert.equal(motion.update(10, false), true, "elapsed gap is capped so the button visibly moves");
  assert.ok(button.position.z < .125 && button.position.z > .1171875);
  assert.equal(indicator.position.z, .0625);
  for (let i = 0; i < 40; i++) motion.update(.05, false);
  assert.deepEqual(phases, ["pressing", "complete"]);
  assert.equal(button.position.z, .125, "button physically returns");
  assert.equal(indicator.position.z, .09375, "indicator holds the final acknowledgement");
  assert.deepEqual(shell.position.toArray(), [0, 0, 0]);
  assert.equal(motion.update(1, false), false);
  assert.equal(motion.play(false), false);
  motion.reset();
  assert.equal(motion.phase, "ready");
  assert.equal(indicator.position.z, .0625);
  assert.equal(motion.play(false), true);
  motion.update(.05, false);
  motion.reset();
  assert.equal(button.position.z, .125);
  assert.equal(motion.update(.05, false), false);
  motion.dispose();
  motion.dispose();
  assert.equal(motion.play(false), false);
});

test("reduced motion at start or during playback samples only the acknowledged final pose", () => {
  const { model, button, indicator, clip } = fixture(), phases = [];
  const motion = createHelpPressMotion(model, [clip], phase => phases.push(phase));
  assert.equal(motion.play(true), true);
  assert.deepEqual(phases, ["complete"]);
  assert.equal(button.position.z, .125);
  assert.equal(indicator.position.z, .09375);
  motion.reset();
  motion.play(false);
  assert.equal(motion.update(.05, true), false);
  assert.deepEqual(phases, ["complete", "ready", "pressing", "complete"]);
  motion.dispose();
  assert.equal(indicator.position.z, .0625);
});

test("missing, unrelated or malformed named clip leaves a static fallback", () => {
  const { model, clip } = fixture();
  for (const clips of [[], [new AnimationClip("OTHER", 1.5, clip.tracks)],
    [new AnimationClip(HELP_PRESS_CLIP, 0, clip.tracks)], [new AnimationClip(HELP_PRESS_CLIP, 1.5, [])],
    [new AnimationClip(HELP_PRESS_CLIP, Infinity, clip.tracks)]])
    assert.equal(createHelpPressMotion(model, clips), null);
});
