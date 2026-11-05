import test from "node:test";
import assert from "node:assert/strict";
import { TABLE, makeRack } from "../src/game/table.js";
import { createShot, stepPhysics } from "../src/game/physics.js";
const DIAMETER_FOR_TEST = TABLE.radius * 2;

function contestedContact(
  firstX,
  secondX,
  secondVelocity = 0,
  reverse = false,
) {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: 0, z: 0 });
  Object.assign(balls[1], { pocketed: false, x: firstX, z: -0.03 });
  Object.assign(balls[2], {
    pocketed: false,
    x: secondX,
    z: 0.03,
    vx: secondVelocity,
  });
  assert.ok(Math.hypot(firstX - secondX, 0.06) > 2 * TABLE.radius);
  if (reverse) balls.reverse();
  const shot = createShot(balls, { x: 1, z: 0 }, 1);
  stepPhysics(balls, shot);
  return { balls: balls.toSorted((a, b) => a.id - b.id), shot };
}

test("earliest geometric cue contact receives the first impulse within a substep", () => {
  const { balls, shot } = contestedContact(0.06, 0.057);
  const reach = Math.sqrt((2 * TABLE.radius) ** 2 - 0.03 ** 2);
  assert.ok(0.057 - reach < 0.06 - reach, "ball 2 is hit first geometrically");
  assert.equal(shot.firstContact, 2);
  assert.ok(
    balls[2].vx > balls[1].vx,
    "the first impact receives the leading impulse",
  );
});

test("moving-target encounter time determines first contact, not array or ID order", () => {
  const a = contestedContact(0.06, 0.061, -0.9);
  const b = contestedContact(0.06, 0.061, -0.9, true);
  assert.equal(a.shot.firstContact, 2);
  assert.equal(b.shot.firstContact, 2);
  assert.deepEqual(a, b);
});

test("simultaneous cue contacts use deterministic ball-number tie breaks", () => {
  const a = contestedContact(0.06, 0.06);
  const b = contestedContact(0.06, 0.06, 0, true);
  assert.equal(a.shot.firstContact, 1);
  assert.deepEqual(a, b);
});

test("ordered contacts do not create kinetic energy", () => {
  const { balls } = contestedContact(0.06, 0.061, -0.9);
  const energy = balls.reduce(
    (sum, ball) => sum + ball.vx ** 2 + ball.vz ** 2,
    0,
  );
  const initial = (0.18 + TABLE.maxSpeed) ** 2 + 0.9 ** 2;
  assert.ok(energy <= initial + 1e-9, `energy ${energy} exceeds ${initial}`);
});

test("a cue/object collision near a side-pocket jaw settles safely", () => {
  const balls = makeRack();
  for (const ball of balls) ball.pocketed = true;
  Object.assign(balls[0], { pocketed: false, x: 0.18, z: 0.4, vx: 0, vz: 0 });
  Object.assign(balls[1], { pocketed: false, x: 0.08, z: 0.48, vx: 0, vz: 0 });
  const shot = createShot(balls, { x: -0.1, z: 0.08 }, 0.5);
  for (let i = 0; i < 3600 && !shot.done && !shot.invalid; i++)
    stepPhysics(balls, shot);
  assert.equal(shot.firstContact, 1);
  assert.equal(shot.invalid, null);
  assert.equal(shot.done, true);
  assert.equal(
    new Set(shot.pockets.map((event) => event.id)).size,
    shot.pockets.length,
  );
});

function grazingContact({
  distance = 2 * TABLE.radius - 0.0001,
  targetVz = 0,
  z = 0,
  x = 0,
} = {}) {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x, z });
  Object.assign(balls[1], {
    pocketed: false,
    x: x + 0.0062,
    z: z + distance,
    vz: targetVz,
  });
  const shot = createShot(balls, { x: 1, z: 0 }, 1);
  stepPhysics(balls, shot);
  return { balls, shot };
}

test("a shallow high-speed graze produces an actual impulse instead of tunneling", () => {
  const { balls, shot } = grazingContact();
  assert.equal(shot.firstContact, 1);
  assert.ok(Math.hypot(balls[1].vx, balls[1].vz) > 0.01);
  const energy = balls.reduce(
    (sum, ball) => sum + ball.vx ** 2 + ball.vz ** 2,
    0,
  );
  assert.ok(energy <= (0.18 + TABLE.maxSpeed) ** 2 + 1e-9);
});

test("a near miss is not converted into a phantom collision", () => {
  const { balls, shot } = grazingContact({
    distance: 2 * TABLE.radius + 0.0001,
  });
  assert.equal(shot.firstContact, null);
  assert.equal(balls[1].vx, 0);
  assert.equal(balls[1].vz, 0);
});

test("swept contact accounts for moving targets", () => {
  const { balls, shot } = grazingContact({
    distance: 2 * TABLE.radius + 0.00005,
    targetVz: -0.06,
  });
  assert.equal(shot.firstContact, 1);
  assert.notEqual(balls[1].vx, 0);
});

test("a grazing hit parallel to a cushion is not discarded", () => {
  const { shot } = grazingContact({
    x: -0.4,
    z: 0.49,
    distance: -(2 * TABLE.radius - 0.0001),
  });
  assert.equal(shot.firstContact, 1);
  assert.equal(shot.invalid, null);
});

test("a pocket capture before a predicted graze takes precedence", () => {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: 0.0124, z: 0.5135 });
  Object.assign(balls[1], { pocketed: false, x: 0.0014, z: 0.45645 });
  const shot = createShot(balls, { x: -1, z: 0 }, 1);
  stepPhysics(balls, shot);
  assert.equal(balls[0].pocketed, true);
  assert.equal(shot.firstContact, null);
  assert.equal(balls[1].vx, 0);
});

test("a graze before pocket entry records the hit and applies its impulse", () => {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: 0.0124, z: 0.5135 });
  Object.assign(balls[1], { pocketed: false, x: 0.0062, z: 0.45645 });
  const shot = createShot(balls, { x: -1, z: 0 }, 1);
  stepPhysics(balls, shot);
  assert.equal(shot.firstContact, 1);
  assert.ok(Math.hypot(balls[1].vx, balls[1].vz) > 0.01);
  assert.equal(balls[0].pocketed, true);
});

test("an earlier head-on impact stops the cue before the pocket sensor", () => {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: 0.035, z: 0.52 });
  Object.assign(balls[1], { pocketed: false, x: -0.025, z: 0.52 });
  const shot = createShot(balls, { x: -1, z: 0 }, 1);
  stepPhysics(balls, shot);
  assert.equal(shot.firstContact, 1);
  assert.equal(balls[0].pocketed, false);
  assert.ok(Math.abs(balls[0].vx) < 0.1);
  assert.equal(
    shot.pockets.some((event) => event.id === 0),
    false,
  );
});

test("a fast path crossing the pocket sensor cannot tunnel through it", () => {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: -0.0062, z: 0.5131 });
  const shot = createShot(balls, { x: 1, z: 0 }, 1);
  stepPhysics(balls, shot);
  assert.equal(balls[0].pocketed, true);
  assert.equal(shot.pockets.filter((event) => event.id === 0).length, 1);
});

test("a fast path outside the pocket sensor is not a phantom pot", () => {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  Object.assign(balls[0], { pocketed: false, x: -0.0062, z: 0.5129 });
  const shot = createShot(balls, { x: 1, z: 0 }, 1);
  stepPhysics(balls, shot);
  assert.equal(balls[0].pocketed, false);
  assert.equal(shot.pockets.length, 0);
});

function railAndContact(projection, fine) {
  const balls = makeRack();
  for (const ball of balls) {
    ball.pocketed = true;
    ball.vx = ball.vz = 0;
  }
  const d = DIAMETER_FOR_TEST - 0.0001,
    diagonal = Math.SQRT1_2;
  Object.assign(balls[0], { pocketed: false, x: -0.4, z: 0.49 });
  Object.assign(balls[1], {
    pocketed: false,
    x: -0.4 + (projection + d) * diagonal,
    z: 0.49 + (projection - d) * diagonal,
  });
  assert.ok(Math.hypot(balls[1].x - balls[0].x, balls[1].z - balls[0].z) > DIAMETER_FOR_TEST);
  assert.ok(balls[0].z <= TABLE.halfWidth - TABLE.radius && balls[1].z <= TABLE.halfWidth - TABLE.radius);
  const shot = createShot(balls, { x: 1, z: 1 }, 1);
  let first = null,
    rail = null;
  for (let i = 0; i < (fine ? 200 : 1); i++) {
    stepPhysics(balls, shot, fine ? TABLE.step / 800 : TABLE.step / 4);
    if (shot.firstContact !== null && first === null) first = i;
    if (balls[0].vz < 0 && rail === null) rail = i;
  }
  return { balls, shot, first, rail };
}
for (const [projection, contactFirst] of [
  [0.005, true],
  [0.007, false],
]) {
  test(`a ${contactFirst ? "ball-before-rail" : "rail-before-ball"} path remains bounded and comparable to fine stepping`, () => {
    const fine = railAndContact(projection, true),
      coarse = railAndContact(projection, false);
    assert.ok(fine.first !== null && fine.rail !== null);
    assert.equal(fine.first < fine.rail, contactFirst);
    assert.equal(coarse.shot.firstContact, 1);
    assert.equal(coarse.shot.invalid, null);
    for (const axis of ["vx", "vz"])
      assert.ok(Math.abs(coarse.balls[1][axis] - fine.balls[1][axis]) < 0.15);
    const energy = coarse.balls.reduce(
      (sum, ball) => sum + ball.vx ** 2 + ball.vz ** 2,
      0,
    );
    assert.ok(energy <= (0.18 + TABLE.maxSpeed) ** 2 + 1e-9);
  });
}

test("a centered equal-mass impact transfers speed without creating energy", () => {
  const balls = makeRack();
  for (const ball of balls) { ball.pocketed = true; ball.vx = ball.vz = 0; }
  Object.assign(balls[0], { pocketed: false, x: -0.1, z: 0 });
  Object.assign(balls[1], { pocketed: false, x: 0, z: 0 });
  const shot = createShot(balls, { x: 1, z: 0 }, 0.5);
  const initial = balls[0].vx ** 2;
  while (shot.firstContact === null && !shot.invalid) stepPhysics(balls, shot);
  assert.equal(shot.firstContact, 1);
  assert.ok(balls[1].vx > 0.9);
  assert.ok(balls[0].vx >= 0 && balls[0].vx < balls[1].vx * 0.05);
  assert.ok(balls[0].vx ** 2 + balls[1].vx ** 2 <= initial + 1e-9);
});
