import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { grovePlacements, groveRings } from "../src/world/groves.js";

const tiles = ["1_0", "1_1"].map(name => JSON.parse(fs.readFileSync(`models/world/tiles/${name}.json`, "utf8")));

test("the Supertree Grove outline is found in the tiles", () => {
  const rings = groveRings(tiles);
  assert.equal(rings.length, 2);
});

test("eleven supertrees stand inside the mapped outline, spaced apart, the same every time", () => {
  const rings = groveRings(tiles);
  const trees = grovePlacements(rings);
  assert.equal(trees.length, 11);
  for (const tree of trees) assert.ok(Number.isFinite(tree.x) && Number.isFinite(tree.z));
  for (let i = 0; i < trees.length; i++) for (let j = i + 1; j < trees.length; j++) assert.ok(Math.hypot(trees[i].x - trees[j].x, trees[i].z - trees[j].z) >= 17);
  assert.deepEqual(grovePlacements(rings), trees);
  assert.ok(new Set(trees.map(tree => tree.model)).size === 3, "all three heights are used");
  assert.deepEqual(grovePlacements([]), []);
});
