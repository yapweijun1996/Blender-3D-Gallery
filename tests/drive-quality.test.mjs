import assert from "node:assert/strict";
import test from "node:test";
import { createQualityGovernor } from "../src/drive/quality.js";

function run(governor, fps, seconds, start = 0) {
  const step = 1000 / fps;
  for (let t = start; t <= start + seconds * 1000; t += step) governor.update(t);
  return start + seconds * 1000;
}

test("slow frames lower the pixel ratio in steps and never below the floor", () => {
  const changes = [];
  const governor = createQualityGovernor({ initial: 2, min: 0.6, onChange: value => changes.push(value) });
  run(governor, 12, 40);
  assert.ok(changes.length >= 3 && changes.every((value, i) => i === 0 || value < changes[i - 1]));
  assert.equal(governor.ratio, 0.6);
});

test("good frame rates leave the ratio alone and a recovery raises it again", () => {
  const governor = createQualityGovernor({ initial: 1.5, min: 0.6 });
  let t = run(governor, 60, 20);
  assert.equal(governor.ratio, 1.5);
  t = run(governor, 10, 15, t);
  const low = governor.ratio;
  assert.ok(low < 1.5);
  run(governor, 70, 30, t);
  assert.ok(governor.ratio > low);
});

test("a long pause is not counted as slow frames", () => {
  const governor = createQualityGovernor({ initial: 1.5, min: 0.6 });
  let t = run(governor, 60, 5);
  governor.update(t + 20000);
  run(governor, 60, 5, t + 20000);
  assert.equal(governor.ratio, 1.5);
});
