import assert from "node:assert/strict";
import test from "node:test";
import { clampToMap, toMinimap } from "../src/world/minimap.js";

const size = { width: 160, height: 200 }, car = { x: 100, z: 50 };

test("the car's own position maps to the car marker, and ahead is up", () => {
  const here = toMinimap(car, car, 0, size);
  assert.deepEqual([here.x, here.y], [80, 120]);
  const ahead = toMinimap({ x: 100, z: 150 }, car, 0, size);
  assert.ok(ahead.y < here.y && Math.abs(ahead.x - here.x) < 1e-9, "100 m ahead is straight up");
  const turned = toMinimap({ x: 200, z: 50 }, car, Math.PI / 2, size);
  assert.ok(turned.y < here.y && Math.abs(turned.x - here.x) < 1e-9, "facing east, a point to the east is up");
});

test("left of the car is the left of the map", () => {
  // Facing south (heading 0), left of travel is +x.
  const left = toMinimap({ x: 140, z: 50 }, car, 0, size), right = toMinimap({ x: 60, z: 50 }, car, 0, size);
  assert.ok(left.x < 80 && right.x > 80);
});

test("a point off the map is pulled to the border along the line from the car", () => {
  const far = toMinimap({ x: 100, z: 5000 }, car, 0, size);
  const edge = clampToMap(far, size);
  assert.equal(edge.clamped, true);
  assert.ok(edge.y >= 0 && edge.y <= size.height && edge.x >= 0 && edge.x <= size.width);
  assert.ok(Math.abs(edge.x - 80) < 1e-6, "still straight ahead");
  const inside = clampToMap({ x: 70, y: 90 }, size);
  assert.deepEqual([inside.x, inside.y, inside.clamped], [70, 90, false]);
});
