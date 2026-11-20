import assert from "node:assert/strict";
import test from "node:test";
import { Scene } from "three";
import { STALL_AT, createSmoke, damageEffects } from "../src/world/damage.js";

test("no smoke until the car is hurt, full smoke when wrecked, engine dies near the end", () => {
  assert.deepEqual(damageEffects(0), { smoke: 0, stalled: false });
  assert.deepEqual(damageEffects(0.39), { smoke: 0, stalled: false });
  const half = damageEffects(0.7);
  assert.ok(half.smoke > 0 && half.smoke < 1 && !half.stalled);
  assert.deepEqual(damageEffects(1), { smoke: 1, stalled: true });
  assert.equal(damageEffects(STALL_AT).stalled, true);
  assert.equal(damageEffects(STALL_AT - 0.01).stalled, false);
  assert.deepEqual(damageEffects(NaN), { smoke: 0, stalled: false });
  assert.equal(damageEffects(5).smoke, 1);
});

test("smoke puffs appear while the car smokes and die away afterwards", () => {
  const scene = new Scene();
  const smoke = createSmoke(scene, 20);
  assert.equal(smoke.points.visible, false);
  let alive = 0;
  for (let i = 0; i < 60; i++) alive = smoke.update(1 / 30, { x: 0, y: 1, z: 0 }, 0.8);
  assert.ok(alive > 5 && smoke.points.visible, `${alive} puffs alive`);
  for (let i = 0; i < 120; i++) alive = smoke.update(1 / 30, { x: 0, y: 1, z: 0 }, 0);
  assert.equal(alive, 0);
  assert.equal(smoke.points.visible, false);
  smoke.dispose();
});
