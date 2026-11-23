import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import RAPIER from "@dimforge/rapier3d-compat";
import { createPhysicsWorld, FIXED_DT } from "../src/world/physics/world.js";
import { buildingMesh, buildTile, TILE_SIZE } from "../src/world/tile-mesh.js";

const tile = JSON.parse(readFileSync(new URL("../models/world/tiles/-6_-6.json", import.meta.url), "utf8"));
const bridge = tile.buildings.find(building => building.id === 719635727);
const bridgeTile = { x: tile.x, z: tile.z, buildings: [bridge] };
const underside = 4.9; // An illustrative simulation input, independent of the mapped footprint.
const baseForBridge = building => building.id === bridge.id ? underside : undefined;

test("ground-level buildings keep their existing solid metadata and open bottoms", () => {
  const { buildings, solids: [solid] } = buildTile(bridgeTile, { buildingBase: () => undefined });
  assert.equal(Object.hasOwn(solid, "base"), false);
  assert.equal(solid.height, bridge.height);
  const position = buildings.attributes.position.array;
  for (let i = 0; i < position.length; i += 9) {
    assert.notDeepEqual([position[i + 1], position[i + 4], position[i + 7]], [0, 0, 0]);
  }
  const collider = buildingMesh(solid.ring, solid.height);
  assert.equal(collider.indices.length / 3, 3 * (solid.ring.length - 1) - 2);
});

test("a raised Innovation Bridge shares the mapped footprint and closed oriented mesh with physics", () => {
  const baseline = buildTile(bridgeTile).solids[0];
  const { buildings, solids: [solid] } = buildTile(bridgeTile, { buildingBase: baseForBridge });
  assert.deepEqual(solid.ring, baseline.ring);
  assert.equal(solid.height, baseline.height);
  assert.equal(solid.base, underside);

  const { vertices, indices } = buildingMesh(solid.ring, solid.height, solid.base);
  const position = buildings.attributes.position.array;
  const normal = buildings.attributes.normal.array;
  assert.deepEqual(position, Float32Array.from(indices.flatMap(index => vertices.slice(3 * index, 3 * index + 3))));
  const footprint = solid.ring.slice(0, -1);
  const center = footprint.reduce(([sx, sz], [x, z]) => [sx + x / footprint.length, sz + z / footprint.length], [0, 0]);
  let undersideTriangles = 0, topTriangles = 0;
  for (let i = 0; i < position.length; i += 9) {
    const y = position[i + 1];
    if (y === position[i + 4] && y === position[i + 7]) {
      if (y === Math.fround(underside)) {
        assert.ok(normal[i + 1] < -0.99, "the visible underside faces the carriageway");
        undersideTriangles++;
      } else {
        assert.ok(normal[i + 1] > 0.99, "the visible roof faces up");
        topTriangles++;
      }
    } else {
      assert.ok((position[i] - center[0]) * normal[i] + (position[i + 2] - center[1]) * normal[i + 2] > 0, "wall normals face out");
    }
  }
  assert.equal(undersideTriangles, 2);
  assert.equal(topTriangles, 2);
});

test("Rapier sees the declared underside over the mapped road and a sedan can pass below", async () => {
  const { solids: [solid] } = buildTile(bridgeTile, { buildingBase: baseForBridge });
  const road = tile.roads.find(way => way.id === "719635729:0");
  const [[x0, z0], [x1, z1]] = road.geometry.map(([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE]);
  const length = Math.hypot(x1 - x0, z1 - z0);
  const dx = (x1 - x0) / length, dz = (z1 - z0) / length;
  const middle = { x: (x0 + x1) / 2, y: 1.4, z: (z0 + z1) / 2 };
  const physics = await createPhysicsWorld();
  try {
    physics.addGround({ x: middle.x, z: middle.z, halfWidth: 40, halfDepth: 40 });
    physics.addStaticTrimesh(buildingMesh(solid.ring, solid.height, solid.base));
    physics.step(FIXED_DT);

    const hit = physics.world.castRay(new RAPIER.Ray(middle, { x: 0, y: 1, z: 0 }), 20, true);
    assert.ok(hit && Math.abs(hit.timeOfImpact - (underside - middle.y)) < 0.001);
    const vehicle = physics.addVehicle({
      type: "sedan", topSpeed: 12, position: { x: x0 - 5 * dx, y: 1.4, z: z0 - 5 * dz }, heading: Math.atan2(dx, dz),
    });
    for (let i = 0; i < 90; i++) physics.step(FIXED_DT);
    vehicle.setControls({ throttle: 1 });
    let passed = false;
    for (let i = 0; i < 360; i++) {
      physics.step(FIXED_DT);
      const { position } = vehicle.getState();
      if ((position.x - x0) * dx + (position.z - z0) * dz > length + 3) {
        passed = true;
        break;
      }
    }
    assert.ok(passed, "the sedan crosses the full overhead footprint on ground support");
  } finally {
    physics.dispose();
  }
});
