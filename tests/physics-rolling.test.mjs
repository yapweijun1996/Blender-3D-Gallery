import test from 'node:test';
import assert from 'node:assert/strict';
import { TABLE, makeRack } from '../src/game/table.js';
import { createShot, stepPhysics } from '../src/game/physics.js';

function rollAgainstRail(direction, dt, start = { x: -0.4, z: 0.46 }) {
  const balls = makeRack();
  for (const ball of balls) ball.pocketed = ball.id !== 0;
  Object.assign(balls[0], { ...start, vx: 0, vz: 0, pocketed: false });
  const shot = createShot(balls, direction, 1);
  for (let t = 0; t < 0.025 - dt / 2; t += dt) stepPhysics(balls, shot, dt);
  assert.equal(shot.invalid, null);
  return balls[0];
}

for (const [start, direction] of [
  [{ x: -0.07, z: 0.46 }, { x: 0, z: 1 }], // Rounded side-pocket jaw.
  [{ x: 0.4, z: -0.46 }, { x: 0, z: -1 }],
  [{ x: 1.04, z: 0.2 }, { x: 1, z: 0 }],
  [{ x: -1.04, z: 0.2 }, { x: -1, z: 0 }],
]) {
  test(`rolling agrees with fine stepping near cushion ${JSON.stringify(start)}`, () => {
    const normal = rollAgainstRail(direction, TABLE.step, start);
    const reference = rollAgainstRail(direction, TABLE.step / 200, start);
    assert.equal(normal.pocketed, false);
    assert.ok(Math.hypot(normal.x - reference.x, normal.z - reference.z) < 0.00025);
    assert.ok(angleBetween(normal.q, reference.q) < 0.02);
  });
}
function angleBetween(a, b) {
  const dot = Math.abs(a.reduce((sum, value, i) => sum + value * b[i], 0));
  return 2 * Math.acos(Math.min(1, dot));
}
for (const direction of [{ x: 0, z: 1 }, { x: 1, z: 1 }]) {
  test(`rolling through a cushion bounce follows the contact path (${direction.x}, ${direction.z})`, () => {
    const normal = rollAgainstRail(direction, TABLE.step);
    const reference = rollAgainstRail(direction, TABLE.step / 200);
    const distance = Math.hypot(normal.x - reference.x, normal.z - reference.z);
    const angle = angleBetween(normal.q, reference.q);
    assert.ok(distance < 0.00025, `position differs by ${distance} m`);
    assert.ok(angle < 0.02, `orientation differs by ${angle} rad`);
    assert.ok(normal.vz < 0, 'ball rebounds away from cushion');
    assert.ok(Math.abs(Math.hypot(...normal.q) - 1) < 1e-9, 'orientation remains normalized');
  });
}

for (const direction of [{ x: 1, z: 0 }, { x: -1, z: 0 }, { x: 0, z: 1 }, { x: 0, z: -1 }, { x: 1, z: 1 }]) test(`free rolling follows travel without slipping (${direction.x}, ${direction.z})`, () => {
  const balls = makeRack();
  for (const ball of balls) ball.pocketed = ball.id !== 0;
  const ball = balls[0];
  Object.assign(ball, { x: 0, z: 0, vx: 0, vz: 0, q: [0, 0, 0, 1], pocketed: false });
  const shot = createShot(balls, direction, 0.1);
  stepPhysics(balls, shot);
  const distance = Math.hypot(ball.x, ball.z);
  const half = distance / (2 * TABLE.radius), scale = Math.sin(half) / distance;
  assert.ok(Math.abs(ball.q[0] + ball.z * scale) < 1e-10);
  assert.ok(Math.abs(ball.q[1]) < 1e-10);
  assert.ok(Math.abs(ball.q[2] - ball.x * scale) < 1e-10);
  assert.ok(Math.abs(ball.q[3] - Math.cos(half)) < 1e-10);
});
