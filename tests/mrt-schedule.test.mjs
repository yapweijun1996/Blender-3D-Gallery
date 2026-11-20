import assert from "node:assert/strict";
import test from "node:test";
import { CYCLE_SECONDS, trainState } from "../src/mrt/schedule.js";

test("the train stops exactly at the platform mark with the doors shut until it has stopped", () => {
  const before = trainState(13.999), stopped = trainState(14);
  assert.ok(Math.abs(stopped.x) < 1e-9 && stopped.speed < 1e-9);
  assert.ok(before.x < 0 && before.speed >= 0);
  for (let t = 0; t < CYCLE_SECONDS; t += 0.05) {
    const state = trainState(t);
    if (state.doors > 0) assert.equal(state.speed, 0, `doors open while moving at t=${t}`);
    assert.ok(state.doors >= 0 && state.doors <= 1);
  }
});

test("the train never runs backwards and the cycle repeats", () => {
  let last = -Infinity;
  for (let t = 0; t < CYCLE_SECONDS - 4; t += 0.05) {
    const x = trainState(t).x;
    assert.ok(x >= last - 1e-9, `t=${t}`);
    last = x;
  }
  assert.deepEqual(trainState(5), trainState(5 + CYCLE_SECONDS));
  assert.equal(trainState(-1).phase, trainState(CYCLE_SECONDS - 1).phase);
});

test("the phases come in order", () => {
  const order = [];
  for (let t = 0; t < CYCLE_SECONDS; t += 0.1) { const phase = trainState(t).phase; if (order.at(-1) !== phase) order.push(phase); }
  assert.deepEqual(order, ["arriving", "opening", "boarding", "closing", "departing", "waiting"]);
});
