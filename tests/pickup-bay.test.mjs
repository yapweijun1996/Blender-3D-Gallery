import test from "node:test";
import assert from "node:assert/strict";
import { interactionKind } from "../src/model-interaction.js";
import { APPROACH_METRES, APPROACH_SECONDS, pickupOffset, pickupPhase } from "../src/pickup-bay/state.js";

test("only the exact pickup bay asset can mount this simulation", () => {
  assert.equal(interactionKind({ id: "mall-ride-hail-pickup-bay" }), "pickup-bay");
  for (const id of ["hatchback-car", "hdb-drop-off-porch", "mall-pickup-bay", "taxi-stand-sign"])
    assert.equal(interactionKind({ id }), null);
});

test("select, approach, stop and board require the proper order", () => {
  let phase = "ready";
  for (const [action, expected] of [
    ["board", "ready"], ["select", "loading"], ["board", "loading"],
    ["loaded", "approaching"], ["select", "approaching"], ["board", "approaching"],
    ["arrive", "stopped"], ["board", "boarded"], ["board", "boarded"],
    ["reset", "ready"], ["arrive", "ready"],
  ]) {
    phase = pickupPhase(phase, action);
    assert.equal(phase, expected);
  }
});

test("reduced motion can arrive directly after loading, failure and reset allow retry", () => {
  assert.equal(pickupPhase("loading", "arrive"), "stopped");
  assert.equal(pickupPhase("loading", "fail"), "failed");
  assert.equal(pickupPhase("failed", "select"), "loading");
  for (const phase of ["ready", "loading", "approaching", "stopped", "boarded", "failed"])
    assert.equal(pickupPhase(phase, "reset"), "ready");
});

test("approach easing remains monotone, ends exactly on the stop anchor and clamps", () => {
  assert.equal(pickupOffset(-1), -APPROACH_METRES);
  assert.equal(pickupOffset(0), -APPROACH_METRES);
  assert.equal(pickupOffset(APPROACH_SECONDS), 0);
  assert.equal(pickupOffset(APPROACH_SECONDS + 1), 0);
  for (let i = 1; i <= 30; i++) {
    const offset = pickupOffset(i * APPROACH_SECONDS / 30);
    assert.ok(offset >= pickupOffset((i - 1) * APPROACH_SECONDS / 30) && offset <= 0);
  }
});
