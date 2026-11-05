import test from "node:test";
import assert from "node:assert/strict";
import {
  TABLE,
  makeRack,
  legalPlacement,
  groupOf,
  POCKETS,
} from "../src/game/table.js";
import { createShot, stepPhysics } from "../src/game/physics.js";
import { adjudicate, RULES_VERSION } from "../src/game/rules.js";
import { validateMatch } from "../src/game/storage.js";
function match() {
  return {
    schema: 1,
    rulesVersion: RULES_VERSION,
    tableVersion: TABLE.version,
    matchId: "test",
    revision: 0,
    phase: "aiming",
    player: 0,
    groups: [null, null],
    break: false,
    ballInHand: false,
    winner: null,
    balls: makeRack(42),
  };
}
function result(m, { pots = [], contact = 1, invalid = null } = {}) {
  const balls = structuredClone(m.balls);
  for (const id of pots) balls[id].pocketed = true;
  return adjudicate(m, balls, {
    id: "shot-" + m.revision,
    firstContact: contact,
    pockets: pots.map((id) => ({ id })),
    invalid,
  });
}
function run(balls, direction = { x: 1, z: 0 }, power = 0.7) {
  const shot = createShot(balls, direction, power);
  shot.id = "test-shot";
  for (let i = 0; i < 3600 && !shot.done && !shot.invalid; i++)
    stepPhysics(balls, shot);
  return shot;
}

test("rack is seeded, complete, eight centered, opposite rear groups and non-overlapping", () => {
  const a = makeRack(1);
  assert.deepEqual(a, makeRack(1));
  assert.equal(a.length, 16);
  assert.equal(new Set(a.map((b) => b.id)).size, 16);
  assert.equal(a[8].z, 0);
  const rear = a.filter((b) => b.x > 0.74);
  assert.equal(rear.length, 5);
  rear.sort((a, b) => a.z - b.z);
  assert.notEqual(groupOf(rear[0].id), groupOf(rear[4].id));
  for (let i = 0; i < a.length; i++)
    for (let j = i + 1; j < a.length; j++)
      assert.ok(
        Math.hypot(a[i].x - a[j].x, a[i].z - a[j].z) >= TABLE.radius * 2,
      );
});
test("placement respects head string, overlaps, table and pocket limits", () => {
  const b = makeRack();
  assert.equal(legalPlacement(b, -0.7, 0, true), true);
  assert.equal(legalPlacement(b, 0, 0, true), false);
  assert.equal(legalPlacement(b, 0.552, 0), false);
  assert.equal(legalPlacement(b, 0, 0.56), false);
  assert.equal(legalPlacement(b, NaN, 0), false);
});
test("legal pot allocates group and continues; miss passes turn", () => {
  const m = match(),
    n = result(m, { pots: [2] });
  assert.deepEqual(n.groups, ["solids", "stripes"]);
  assert.equal(n.player, 0);
  assert.equal(result(m, { contact: 3 }).player, 1);
});
test("foul does not allocate group and pockets stay pocketed", () => {
  const m = match(),
    n = result(m, { pots: [0, 2] });
  assert.deepEqual(n.groups, [null, null]);
  assert.equal(n.phase, "placing");
  assert.equal(n.player, 1);
  assert.equal(n.balls[2].pocketed, true);
});
test("mixed pots sort by event time, with ball number breaking simultaneous ties", () => {
  const m = match(),
    balls = structuredClone(m.balls);
  balls[2].pocketed = balls[10].pocketed = true;
  const decide = (pockets) =>
    adjudicate(m, balls, {
      id: "mixed",
      firstContact: 2,
      pockets,
      invalid: null,
    });
  const a = { id: 10, tick: 7, sub: 2 },
    b = { id: 2, tick: 7, sub: 2 };
  assert.deepEqual(decide([a, b]).groups, ["solids", "stripes"]);
  assert.deepEqual(decide([b, a]).groups, ["solids", "stripes"]);
  assert.deepEqual(decide([{ ...a, tick: 6 }, b]).groups, [
    "stripes",
    "solids",
  ]);
  assert.deepEqual(decide([{ ...a, sub: 1 }, b]).groups, ["stripes", "solids"]);
  assert.deepEqual(decide([{ ...a, time: 0.1 }, { ...b, time: 0.9 }]).groups, ["stripes", "solids"]);
  assert.deepEqual(decide([{ ...a, time: 0.4 }, { ...b, time: 0.4 }]).groups, ["solids", "stripes"]);
});
test("open-table group follows the first actual pot within a substep", () => {
  const before = match();
  const balls = structuredClone(before.balls);
  for (const ball of balls) ball.pocketed = ![0, 1, 9].includes(ball.id);
  Object.assign(balls[1], { x: 0, z: 0.512, vx: 0, vz: 1, pocketed: false });
  Object.assign(balls[9], { x: 0, z: -0.511, vx: 0, vz: -2.8, pocketed: false });
  before.balls = structuredClone(balls);
  const shot = createShot(balls, { x: 1, z: 0 }, 0.05);
  shot.id = "same-substep-pots";
  stepPhysics(balls, shot);
  const solid = shot.pockets.find((event) => event.id === 1);
  const stripe = shot.pockets.find((event) => event.id === 9);
  assert.ok(solid && stripe, "both balls enter a pocket");
  assert.equal(stripe.tick, solid.tick);
  assert.equal(stripe.sub, solid.sub);
  assert.ok(stripe.time < solid.time, "stripe enters before solid");
  shot.firstContact = 1;
  assert.deepEqual(adjudicate(before, balls, shot).groups, ["stripes", "solids"]);
});
test("break never allocates groups, eight is re-spotted and scratch gives ball in hand", () => {
  const m = match();
  m.break = true;
  const n = result(m, { pots: [8, 0, 2] });
  assert.equal(n.winner, null);
  assert.equal(n.balls[8].pocketed, false);
  assert.equal(n.phase, "placing");
  assert.equal(n.player, 1);
  assert.deepEqual(n.groups, [null, null]);
});
test("break pot continues, miss changes turn, no contact is a foul", () => {
  const m = match();
  m.break = true;
  assert.equal(result(m, { pots: [3] }).player, 0);
  assert.equal(result(m).player, 1);
  assert.equal(result(m, { contact: null }).phase, "placing");
});
test("early eight and last own ball plus eight lose", () => {
  const m = match();
  m.groups = ["solids", "stripes"];
  assert.equal(result(m, { pots: [8], contact: 1 }).winner, 1);
  for (const b of m.balls) if (b.id >= 2 && b.id <= 7) b.pocketed = true;
  assert.equal(result(m, { pots: [1, 8], contact: 1 }).winner, 1);
});
test("eligible eight wins unless any foul occurs in the same shot", () => {
  const m = match();
  m.groups = ["solids", "stripes"];
  for (const b of m.balls) if (groupOf(b.id) === "solids") b.pocketed = true;
  assert.equal(result(m, { pots: [8], contact: 8 }).winner, 0);
  assert.equal(result(m, { pots: [8, 0], contact: 8 }).winner, 1);
  assert.equal(result(m, { pots: [8], contact: 10 }).winner, 1);
});
test("wrong first contact and open-table eight contact are fouls", () => {
  const m = match();
  assert.equal(result(m, { contact: 8 }).ballInHand, true);
  m.groups = ["solids", "stripes"];
  assert.equal(result(m, { contact: 9 }).phase, "placing");
});
test("an open table with all group balls gone can finish, but a partly cleared open table cannot play eight", () => {
  const m = match();
  for (const b of m.balls) if (groupOf(b.id) === "solids") b.pocketed = true;
  assert.equal(result(m, { pots: [8], contact: 8 }).winner, 1);
  assert.deepEqual(result(m, { pots: [9], contact: 9 }).groups, [
    "stripes",
    "solids",
  ]);
  for (const b of m.balls) if (groupOf(b.id)) b.pocketed = true;
  assert.equal(result(m, { pots: [8], contact: 8 }).winner, 0);
  assert.equal(result(m, { pots: [8, 0], contact: 8 }).winner, 1);
});
test("opponent-only pots pass turn and mixed own pots continue", () => {
  const m = match();
  m.groups = ["solids", "stripes"];
  assert.equal(result(m, { pots: [9] }).player, 1);
  assert.equal(result(m, { pots: [9, 1] }).player, 0);
});
test("duplicate and finished shot resolution is rejected", () => {
  const m = match();
  m.lastShotId = "shot-0";
  assert.throws(() => result(m));
  m.lastShotId = null;
  m.phase = "finished";
  assert.throws(() => result(m));
});
test("invalid physical outcome restores pre-shot state in recovery", () => {
  const m = match(),
    n = result(m, { invalid: "unsafe" });
  assert.equal(n.phase, "recovery");
  assert.deepEqual(n.balls, m.balls);
});
test("stable schema rejects corruption, motion, shuffled IDs and contradictory results", () => {
  const m = match();
  assert.equal(validateMatch(m), true);
  for (const mutate of [
    (m) => (m.balls[0].x = NaN),
    (m) => (m.balls[0].vx = 1),
    (m) => (m.balls[1].id = 0),
    (m) => (m.groups = ["solids", "solids"]),
    (m) => (m.winner = 1),
    (m) => (m.tableVersion = "old"),
    (m) => ([m.balls[0], m.balls[1]] = [m.balls[1], m.balls[0]]),
    (m) => (m.balls[0].pocketed = true),
    (m) => {
      m.phase = "finished";
      m.winner = 1;
    },
    (m) => (m.balls[8].pocketed = true),
    (m) => {
      m.break = true;
      m.groups = ["solids", "stripes"];
    },
  ]) {
    const n = structuredClone(m);
    mutate(n);
    assert.equal(validateMatch(n), false);
  }
});
test("fixed-step rack break settles without escape, preserves identity and repeats", () => {
  const a = makeRack(42),
    b = makeRack(42),
    s = run(a),
    t = run(b);
  assert.equal(s.invalid, null);
  assert.equal(s.done, true);
  assert.notEqual(s.firstContact, null);
  assert.deepEqual(a, b);
  assert.deepEqual(s, t);
  assert.equal(new Set(a.map((x) => x.id)).size, 16);
  for (const x of a) assert.ok([x.x, x.z, x.vx, x.vz].every(Number.isFinite));
});
test("malformed save entries are rejected without throwing", () => {
  for (const bad of [null, undefined, [], 0, "broken"]) {
    const m = match();
    m.balls[5] = bad;
    assert.equal(validateMatch(m), false);
  }
});
test("all six pocket approach fixtures capture exactly once", () => {
  for (const p of POCKETS) {
    const a = makeRack();
    a.forEach((b) => (b.pocketed = true));
    const b = a[0];
    b.pocketed = false;
    b.x = p.x === 0 ? 0 : p.x - Math.sign(p.x) * 0.12;
    b.z = p.z - Math.sign(p.z) * 0.12;
    const s = run(a, { x: p.x - b.x, z: p.z - b.z }, 0.35);
    assert.equal(s.invalid, null, p.id);
    assert.equal(s.pockets.filter((e) => e.id === 0).length, 1, p.id);
  }
});
test("cushion reflects, low power stops, and high power cannot tunnel", () => {
  for (const power of [0.05, 1]) {
    const a = makeRack();
    a.forEach((b) => (b.pocketed = true));
    Object.assign(a[0], { pocketed: false, x: -0.25, z: 0 });
    const s = run(a, { x: 0, z: 1 }, power);
    assert.equal(s.invalid, null);
    assert.equal(s.done, true);
    assert.equal(a[0].pocketed, false);
    assert.ok(Math.abs(a[0].z) <= TABLE.halfWidth - TABLE.radius + 0.0001);
  }
});
