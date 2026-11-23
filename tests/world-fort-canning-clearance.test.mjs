import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import RAPIER from "@dimforge/rapier3d-compat";
import profile from "../scripts/world/fort-canning-integration.json" with { type: "json" };
import { createPhysicsWorld, FIXED_DT } from "../src/world/physics/world.js";
import { PEDESTRIAN_TUNING } from "../src/world/physics/pedestrian.js";
import { buildingMesh, buildTile } from "../src/world/tile-mesh.js";
import { createStreamedTunnelGround } from "../src/world/tunnel-integration/colliders.js";
import { createFortCanningMergeGeometry } from "../src/world/tunnel-integration/merge-geometry.js";
import { nearestTunnelSection, pointOffset } from "../src/world/tunnel-prototype/geometry.js";

const geometry = createFortCanningMergeGeometry(profile);
const up = { x: 0, y: 1, z: 0 }, down = { x: 0, y: -1, z: 0 };
const crossing = id => profile.crossings.find(feature => feature.edgeId === id);

function at(sections, station) {
  const s = Math.max(sections[0].s, Math.min(sections.at(-1).s, station));
  const next = sections.findIndex(point => point.s > s);
  const i = next < 0 ? sections.length - 1 : next;
  const a = sections[i - 1], b = sections[i], fraction = (s - a.s) / (b.s - a.s);
  return { x: a.x + (b.x - a.x) * fraction, y: a.y + (b.y - a.y) * fraction, z: a.z + (b.z - a.z) * fraction,
    heading: Math.atan2(b.x - a.x, b.z - a.z) };
}

function pathOf(points) {
  let s = 0;
  return points.map(([x, z], index) => {
    if (index) s += Math.hypot(x - points[index - 1][0], z - points[index - 1][1]);
    return { x, y: 0, z, s };
  });
}

function cast(physics, position, direction, maxTime = 8) {
  return physics.world.castRay(new RAPIER.Ray(position, direction), maxTime, true);
}

async function withCut(run, activeGeometry = geometry) {
  const physics = await createPhysicsWorld();
  const ground = createStreamedTunnelGround(physics, activeGeometry);
  try {
    ground.setActive(true);
    physics.step(FIXED_DT);
    await run(physics);
  } finally {
    ground.dispose();
    physics.dispose();
  }
}

for (const id of ["774912614:0", "1552288080:0"]) {
  test(`footway ${id} keeps continuous cross-width support and can be walked`, async t => {
    const { points, at: center } = crossing(id);
    const footprint = buildTile({ x: 0, z: 0, pedestrian: [{ geometry: points }] }).ground;
    const triangles = footprint.attributes.position.array;
    const bounds = footprint.index?.array;
    const baseGeometry = { ...geometry, surfaces: geometry.surfaces.filter(surface => surface.id !== "footway") };
    let probes = 0;
    await withCut(physics => {
      // Sample the actual 2.2 m renderer ribbon, including every edge of every triangle.
      const stop = bounds?.length ?? triangles.length / 3;
      const vertex = i => triangles.subarray(3 * (bounds?.[i] ?? i), 3 * (bounds?.[i] ?? i) + 3);
      for (let i = 0; i < stop; i += 3) {
        const a = vertex(i), b = vertex(i + 1), c = vertex(i + 2);
        const edges = [[b, c], [c, a], [a, b]];
        const [shortA, shortB] = edges.reduce((shortest, pair) =>
          Math.hypot(pair[1][0] - pair[0][0], pair[1][2] - pair[0][2])
          < Math.hypot(shortest[1][0] - shortest[0][0], shortest[1][2] - shortest[0][2]) ? pair : shortest);
        const opposite = [a, b, c].find(point => point !== shortA && point !== shortB);
        const rows = Math.ceil(Math.hypot(opposite[0] - shortA[0], opposite[2] - shortA[2]) / .28);
        for (let row = 0; row <= rows; row++) for (let col = 0; col <= 8; col++) {
          const u = row / rows, v = (1 - u) * col / 8;
          const x = shortA[0] + u * (opposite[0] - shortA[0]) + v * (shortB[0] - shortA[0]);
          const z = shortA[2] + u * (opposite[2] - shortA[2]) + v * (shortB[2] - shortA[2]);
          const hit = cast(physics, { x, y: 1, z }, down, 2);
          assert.ok(hit && Math.abs(1 - hit.timeOfImpact) < .025, `walkway support at ${x.toFixed(2)}, ${z.toFixed(2)}`);
          probes++;
        }
      }
      if (center) {
        const road = nearestTunnelSection(geometry.alignment.link, center);
        const hit = cast(physics, { ...center, y: road.y + 1.2 }, up);
        assert.ok(hit && Math.abs(hit.timeOfImpact - (geometry.clearance - 1.2)) < .025,
          "the pedestrian deck has a separate tunnel underside below it");
      }
    }, baseGeometry);
    await withCut(physics => {
      const walk = pathOf(points), end = walk.at(-1).s;
      const first = at(walk, Math.min(1, end / 5));
      const surfaceHeight = triangles[1];
      const top = cast(physics, { ...first, y: 1.7 }, down);
      assert.ok(top && Math.abs(1.7 - top.timeOfImpact - surfaceHeight) < .005, "volume meets the drawn footway");
      const pedestrian = physics.addPedestrian({ position: { x: first.x, y: 1, z: first.z } });
      let s = 0;
      let minFeetY = Infinity;
      let grounded = 0, frames = 0;
      for (; frames < 60 * (end + 8) && s < end - .35; frames++) {
        const state = pedestrian.getState();
        const closest = nearestTunnelSection(walk, state.position);
        s = closest.s;
        const target = at(walk, s + .6);
        const dx = target.x - state.position.x, dz = target.z - state.position.z;
        const length = Math.hypot(dx, dz) || 1;
        pedestrian.setVelocity({ x: 1.45 * dx / length, z: 1.45 * dz / length });
        physics.step(FIXED_DT);
        grounded += Number(state.grounded);
        minFeetY = Math.min(minFeetY, state.position.y - PEDESTRIAN_TUNING.height / 2);
        assert.ok(Math.abs(closest.lateral) < .7 && minFeetY >= surfaceHeight - .03,
          `pedestrian at ${s.toFixed(3)} m and Y=${state.position.y.toFixed(3)}, lateral ${closest.lateral.toFixed(3)} m`);
      }
      assert.ok(s >= end - .35 && grounded / frames > .98, "the pedestrian traversed the entire surface path");
      t.diagnostic(`${probes} surface probes, ${end.toFixed(2)} m walked, minimum capsule feet Y=${minFeetY.toFixed(3)} m`);
    });
    footprint.dispose();
  });
}

test("a sedan passes below the mapped Innovation Bridge on the merged tunnel floor", async t => {
  const bridge = crossing("719635727");
  const tile = JSON.parse(readFileSync(new URL("../models/world/tiles/-6_-6.json", import.meta.url), "utf8"));
  const sourceBuilding = tile.buildings.find(building => building.id === 719635727);
  const base = 3; // Modeled underside in world metres. The source supplies the footprint only.
  const meshes = buildTile({ x: tile.x, z: tile.z, buildings: [sourceBuilding] }, { buildingBase: () => base });
  const [solid] = meshes.solids;
  const link = geometry.alignment.link;
  await withCut(physics => {
    const collider = physics.addStaticTrimesh(buildingMesh(solid.ring, solid.height, solid.base));
    physics.step(FIXED_DT);
    const highest = Math.max(at(link, bridge.start).y, at(link, bridge.end).y,
      ...link.filter(row => row.s > bridge.start && row.s < bridge.end).map(row => row.y));
    const available = base - highest;
    assert.ok(available >= 4.9, `full swept envelope has ${available.toFixed(3)} m clearance`);
    let probes = 0;
    for (const row of link.filter(point => point.s >= bridge.start && point.s <= bridge.end)) {
      for (const offset of [-4.8, -2.4, 0, 2.4, 4.8]) {
        const [x, y, z] = pointOffset(row, offset, row.y + 1);
        const hit = cast(physics, { x, y, z }, up);
        if (hit?.collider.handle !== collider.handle) continue;
        probes++;
        assert.ok(Math.abs(hit.timeOfImpact - (base - y)) < .012, "ray hits the declared underside");
      }
    }
    assert.ok(probes >= 30, "rays reached the actual footprint across the lower carriageway");
    const spawn = at(link, bridge.start - 14);
    const vehicle = physics.addVehicle({ type: "sedan", topSpeed: 8, position: { x: spawn.x, y: spawn.y + 1, z: spawn.z }, heading: spawn.heading });
    vehicle.setControls({ brake: 1 });
    for (let step = 0; step < 90; step++) physics.step(FIXED_DT);
    let passed = false, wheelsUnder = 0;
    for (let step = 0; step < 60 * 14; step++) {
      const state = vehicle.getState();
      const road = nearestTunnelSection(link, state.position);
      const target = at(link, road.s + 7);
      const error = Math.atan2(target.x - state.position.x, target.z - state.position.z) - state.heading;
      vehicle.setControls({ throttle: 1, steer: Math.max(-1, Math.min(1, 2 * Math.atan2(Math.sin(error), Math.cos(error)))) });
      physics.step(FIXED_DT);
      if (road.s >= bridge.start && road.s <= bridge.end && state.wheels.every(wheel => wheel.grounded)) wheelsUnder++;
      assert.ok(state.position.y > road.y + .25 && state.position.y < road.y + 1.1 && !state.flipped);
      if (road.s > bridge.end + 7) { passed = true; break; }
    }
    assert.ok(passed && wheelsUnder > 60 && vehicle.getState().damage < .05, "the sedan drove underneath with supported wheels");
    t.diagnostic(`${available.toFixed(3)} m minimum simulated clearance with ${probes} underside hits`);
  });
  meshes.buildings?.dispose();
});
