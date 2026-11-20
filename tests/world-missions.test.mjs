import assert from "node:assert/strict";
import test from "node:test";
import { MISSIONS, arrived, distanceTo, nextMission, relativeBearing } from "../src/world/missions.js";

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
