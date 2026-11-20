import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { LAYER_HEIGHT, bridgeHeight, fragmentHeights, isBridge } from "../src/world/bridges.js";

test("a bridge starts and ends on the ground and is level in the middle", () => {
  assert.equal(bridgeHeight(1, 0, 300), 0);
  assert.equal(bridgeHeight(1, 300, 300), 0);
  assert.equal(bridgeHeight(1, 150, 300), LAYER_HEIGHT);
  assert.equal(bridgeHeight(2, 400, 800), 2 * LAYER_HEIGHT);
  assert.ok(bridgeHeight(1, 30, 60) < 2, "a short bridge is only a gentle hump");
  assert.equal(bridgeHeight(0, 150, 300), 0, "layer 0 is ground");
  assert.equal(bridgeHeight(1, 10, 0), 0, "no length, no lift");
});

test("the ramp is symmetric, smooth and never decreases towards the middle", () => {
  let last = -1;
  for (let s = 0; s <= 150; s += 2) {
    const h = bridgeHeight(1, s, 300);
    assert.ok(h >= last - 1e-9);
    assert.ok(Math.abs(h - bridgeHeight(1, 300 - s, 300)) < 1e-9);
    last = h;
  }
  // Gentle: the steepest step over 2 m stays under the 8 percent grade (plus a little for the 2 m step).
  for (let s = 0; s < 300; s += 2) assert.ok(Math.abs(bridgeHeight(1, s + 2, 300) - bridgeHeight(1, s, 300)) / 2 < 0.085);
});

test("every bridge fragment in the tiles can be lifted", () => {
  let count = 0;
  for (const file of fs.readdirSync("models/world/tiles").filter(name => name !== "index.json")) {
    const tile = JSON.parse(fs.readFileSync(`models/world/tiles/${file}`, "utf8"));
    for (const road of tile.roads) {
      if (!isBridge(road)) continue;
      count++;
      assert.ok(road.edgeStart >= 0 && road.edgeLength > 0, `${road.id} has its place on the edge`);
      const heights = fragmentHeights(road);
      assert.equal(heights.length, road.geometry.length);
      assert.ok(heights.every(h => Number.isFinite(h) && h >= 0 && h <= road.layer * LAYER_HEIGHT + 1e-9));
    }
  }
  assert.ok(count >= 70, `${count} bridge fragments`);
});

test("a car can drive up the ramp onto a raised deck (real tile geometry, Rapier physics)", async () => {
  const { createPhysicsWorld } = await import("../src/world/physics/world.js");
  const { buildTile } = await import("../src/world/tile-mesh.js");
  let found = null;
  for (const file of fs.readdirSync("models/world/tiles").filter(name => name !== "index.json")) {
    const tile = JSON.parse(fs.readFileSync(`models/world/tiles/${file}`, "utf8"));
    for (const road of tile.roads) {
      if (!isBridge(road) || road.edgeStart > 1 || road.edgeLength < 200 || road.geometry.length < 3) continue;
      const fragmentLength = road.geometry.slice(1).reduce((sum, p, i) => sum + Math.hypot(p[0] - road.geometry[i][0], p[1] - road.geometry[i][1]), 0);
      if (fragmentLength > 120 && !found) found = { tile, road };
    }
  }
  assert.ok(found, "a long bridge starting inside a tile exists");
  const { tile, road } = found;
  const built = buildTile(tile);
  const physics = await createPhysicsWorld();
  physics.addGround({ halfWidth: 3000, halfDepth: 3000 });
  for (const deck of built.bridgeSolids) physics.addStaticTrimesh({ vertices: deck.vertices, indices: deck.indices, friction: 1 });
  const [first, second] = road.geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]);
  const heading = Math.atan2(second[0] - first[0], second[1] - first[1]);
  const car = physics.addVehicle({ type: "sedan", position: { x: first[0] + Math.sin(heading) * 3, y: 1.2, z: first[1] + Math.cos(heading) * 3 }, heading });
  let top = 0;
  for (let i = 0; i < 60 * 25; i++) {
    car.setControls({ throttle: 1 });
    physics.step(1 / 60);
    top = Math.max(top, car.getState().position.y);
  }
  physics.dispose();
  assert.ok(top > 2.5, `the car climbed to ${top.toFixed(2)} m`);
});
