import assert from "node:assert/strict";
import test from "node:test";
import { ROAD_DISTANCES } from "../src/world/mission-distances.js";
import { MISSIONS, arrived, cleanRecord, recordScore, distanceTo, missionScore, nextMission, parSeconds, relativeBearing, roadDistance } from "../src/world/missions.js";

const origin = { x: 0, z: 0 };

test("a mission is done only within its radius", () => {
  const mission = MISSIONS[0];
  assert.equal(arrived({ x: mission.x + mission.radius - 1, z: mission.z }, mission), true);
  assert.equal(arrived({ x: mission.x + mission.radius + 1, z: mission.z }, mission), false);
  assert.ok(Math.abs(distanceTo({ x: mission.x + 3, z: mission.z + 4 }, mission) - 5) < 1e-9);
});

test("the target bearing is relative to the car: ahead is 0, to the left is positive", () => {
  const ahead = { x: 0, z: 100 }, left = { x: 100, z: 0 }, right = { x: -100, z: 0 }, behind = { x: 0, z: -100 };
  const bearing = target => relativeBearing(origin, 0, { ...target });
  assert.ok(Math.abs(bearing(ahead)) < 1e-9);
  assert.ok(bearing(left) > 1.5 && bearing(left) < 1.6);
  assert.ok(bearing(right) < -1.5 && bearing(right) > -1.6);
  assert.ok(Math.abs(Math.abs(bearing(behind)) - Math.PI) < 1e-9);
  // Facing east (heading +90 degrees) the target to the east is straight ahead.
  assert.ok(Math.abs(relativeBearing(origin, Math.PI / 2, { x: 100, z: 0 })) < 1e-9);
});

test("the next mission cycles and skips the one the car is standing in", () => {
  const far = { x: 5000, z: 5000 };
  assert.equal(nextMission(0, far), 1);
  assert.equal(nextMission(MISSIONS.length - 1, far), 0);
  const inSecond = { x: MISSIONS[1].x, z: MISSIONS[1].z };
  assert.equal(nextMission(0, inSecond), 2);
  assert.ok(new Set(MISSIONS.map(mission => mission.id)).size === MISSIONS.length);
});

test("faster and cleaner runs score more, within bounds", () => {
  const distance = 800, par = parSeconds(distance);
  const onPar = missionScore({ distance, seconds: par });
  assert.equal(onPar, 1000);
  assert.ok(missionScore({ distance, seconds: par / 2 }) > onPar, "faster scores more");
  assert.equal(missionScore({ distance, seconds: par / 10 }), 1500, "capped at 1.5 times");
  assert.ok(missionScore({ distance, seconds: par * 2 }) < onPar, "slower scores less");
  assert.equal(missionScore({ distance, seconds: par * 1000 }), 100, "never below the floor");
  assert.equal(missionScore({ distance, seconds: par, damage: 1 }), 500, "full damage halves it");
  assert.ok(missionScore({ distance, seconds: par, damage: 0.2 }) < onPar);
  assert.equal(missionScore({ distance, seconds: par, damage: -3 }), onPar, "damage below zero is ignored");
});

test("the best score per mission is kept and only improves", () => {
  let { record, improved } = recordScore({ best: {} }, "merlion", 900);
  assert.equal(improved, true);
  assert.equal(record.best.merlion, 900);
  ({ record, improved } = recordScore(record, "merlion", 700));
  assert.equal(improved, false);
  assert.equal(record.best.merlion, 900);
  ({ record, improved } = recordScore(record, "merlion", 1100));
  assert.equal(improved, true);
  assert.equal(recordScore(undefined, "gardens", 300).record.best.gardens, 300);
});

test("a damaged or foreign saved record is cleaned", () => {
  assert.deepEqual(cleanRecord(null), { best: {} });
  assert.deepEqual(cleanRecord({ best: { merlion: 1200.4, gardens: -5, bayfront: "x", unknown: 9 } }), { best: { merlion: 1200 } });
  assert.deepEqual(cleanRecord("garbage"), { best: {} });
});

test("the generated road distances cover every pair and are at least the straight line", () => {
  const places = [{ id: "start", x: -61, z: -12 }, ...MISSIONS];
  for (const from of places) for (const to of MISSIONS) {
    if (from.id === to.id) continue;
    const road = ROAD_DISTANCES[from.id]?.[to.id];
    assert.ok(Number.isFinite(road), `${from.id} to ${to.id}`);
    assert.ok(road >= Math.hypot(from.x - to.x, from.z - to.z) - 1, `${from.id} to ${to.id}: road ${road} shorter than the straight line`);
  }
});

test("road distance falls back to a detour factor when the table does not know the pair", () => {
  assert.equal(roadDistance(ROAD_DISTANCES, "start", "artscience", 315), ROAD_DISTANCES.start.artscience);
  assert.equal(roadDistance(ROAD_DISTANCES, "nowhere", "artscience", 100), 130);
  assert.equal(roadDistance(undefined, "start", "artscience", 100), 130);
});
