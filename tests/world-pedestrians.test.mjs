import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { pedestrianPaths, samplePath } from "../src/world/paths.js";

const tiles = [];
for (let z = -2; z <= 2; z++) for (let x = -2; x <= 2; x++) {
  const file = `models/world/tiles/${x}_${z}.json`;
  if (fs.existsSync(file)) tiles.push(JSON.parse(fs.readFileSync(file, "utf8")));
}

test("footways become walkable world-space paths", () => {
  const paths = pedestrianPaths(tiles);
  assert.ok(paths.length > 100, `${paths.length} paths`);
  for (const path of paths.slice(0, 300)) {
    assert.ok(path.length >= 12);
    const start = samplePath(path, 0), end = samplePath(path, path.length), middle = samplePath(path, path.length / 2);
    for (const point of [start, middle, end]) assert.ok(Number.isFinite(point.x) && Math.abs(Math.hypot(point.dx, point.dz) - 1) < 1e-6);
    assert.ok(Math.hypot(start.x - path.points[0][0], start.z - path.points[0][1]) < 1e-6);
  }
});

test("indoor corridors and steps are not walked", () => {
  const classes = new Set(tiles.flatMap(tile => tile.pedestrian.map(way => way.class)));
  assert.ok(classes.has("corridor") && classes.has("steps"));
  const walked = pedestrianPaths(tiles).length;
  const all = tiles.reduce((sum, tile) => sum + tile.pedestrian.length, 0);
  assert.ok(walked < all);
});
