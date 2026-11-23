import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';

import { offsetPolyline } from '../src/world/network/geometry.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildTile, buildingMesh, TILE_SIZE } from '../src/world/tile-mesh.js';
import { sampleEdge } from '../src/world/traffic.js';
import { nearestTunnelSection } from '../src/world/tunnel-prototype/geometry.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-1_-6.json', import.meta.url)));
const roads = new Map(tile.roads.map(road => [road.id, road]));
const routes = [
  ['21702431:4', '395443687:0', '750875319:0'],
  ['21701084:0', '395443688:0', '750875316:0'],
];

function laneCourse(ids, offset) {
  const [approach, covered, departure] = ids.map(id => roads.get(id).geometry);
  const road = [...approach, ...covered.slice(1), ...departure.slice(1)]
    .map(([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE]);
  const points = offsetPolyline(road, offset);
  const cumulative = [0];
  for (let i = 1; i < points.length; i++) {
    cumulative.push(cumulative[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
  }
  const stations = points.map(([x, z], i) => ({ x, z, y: 0, s: cumulative[i] }));
  return { points, cumulative, stations, length: cumulative.at(-1),
    entry: cumulative[approach.length - 1], exit: cumulative[approach.length + covered.length - 2] };
}

async function loadScene(t) {
  const physics = await createPhysicsWorld();
  physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  const built = buildTile(tile);
  for (const solid of built.solids) physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
  for (const deck of built.bridgeSolids) physics.addStaticTrimesh(deck);
  for (const panel of built.walkwaySolids) physics.addStaticConvexHull({ vertices: panel.position, friction: 1 });
  physics.step(FIXED_DT);
  t.after(() => {
    physics.dispose();
    for (const geometry of [built.ground, built.buildings, built.towers]) geometry?.dispose();
  });
  return { physics, built };
}

test('both Temasek carriageways have uninterrupted asphalt, floor and a five-metre canopy between the staggered portals', async t => {
  const { physics, built } = await loadScene(t);
  const material = new MeshBasicMaterial({ side: DoubleSide });
  t.after(() => material.dispose());
  const ground = new Mesh(built.ground, material), mall = new Mesh(built.buildings, material);
  const down = new Vector3(0, -1, 0), up = new Vector3(0, 1, 0);
  for (const ids of routes) {
    let hits = 0;
    for (const offset of [-3.15, -1.7, 0, 1.7, 3.15]) {
      const lane = laneCourse(ids, offset);
      for (let s = lane.entry - 2; s < lane.exit + 2; s += .20) {
        const point = sampleEdge(lane, s);
        const at = new Vector3(point.x, 1, point.z);
        const top = new Raycaster(at, down, 0, 1).intersectObject(ground)[0]?.point.y;
        assert.ok(Math.abs(top - .03) < .003, 'visible asphalt at ' + [ids[1], offset, s.toFixed(2), top]);
        const floor = physics.supportHeight(at);
        assert.ok(Number.isFinite(floor) && Math.abs(floor) < .002);
        const soffit = physics.overheadHeight(at);
        if (s < lane.entry - 1 || s > lane.exit + 1) assert.equal(soffit, null);
        if (s > lane.entry + 1 && s < lane.exit - 1) assert.ok(soffit !== null);
        if (soffit !== null) {
          assert.ok(Math.abs(soffit - 5) < .002);
          const underside = new Raycaster(at, up, 0, 6).intersectObject(mall)[0];
          assert.ok(underside && Math.abs(underside.point.y - soffit) < .002 && underside.face.normal.y < -.99);
          hits++;
        }
      }
    }
    assert.ok(hits > 900);
    t.diagnostic(ids[1] + ': ' + hits + ' supported road and matching soffit samples');
  }
});

test('two buses and two sedans pass in opposite directions under the Suntec roof', async t => {
  const { physics } = await loadScene(t);
  const drivers = routes.flatMap(ids => [1.7, -1.7].map(offset => {
    const lane = laneCourse(ids, offset);
    const at = sampleEdge(lane, lane.entry - 12);
    const type = offset > 0 ? 'bus' : 'sedan';
    const car = physics.addVehicle({ type, topSpeed: 8, position: { x: at.x, y: 1.6, z: at.z },
      heading: Math.atan2(at.dx, at.dz) });
    car.setControls({ brake: 1 });
    return { car, lane, finished: false, covered: 0 };
  }));
  for (let i = 0; i < 90; i++) physics.step(FIXED_DT);
  let allCovered = 0;
  for (let frame = 0; frame < 1200 && drivers.some(driver => !driver.finished); frame++) {
    let under = 0;
    for (const driver of drivers) {
      if (driver.finished) continue;
      const { car, lane } = driver, state = car.getState();
      const { s, lateral } = nearestTunnelSection(lane.stations, state.position);
      assert.ok(Math.abs(lateral) < .8, 'vehicle centre stays in its own lane');
      assert.equal(state.damage, 0);
      assert.equal(state.flipped, false);
      if (s > lane.entry + 2 && s < lane.exit - 2) {
        const y = physics.overheadHeight(state.position);
        assert.ok(y !== null && Math.abs(y - 5) < .002);
        assert.ok(state.wheels.every(wheel => wheel.grounded));
        driver.covered++;
        under++;
      }
      if (s > lane.exit + 9) {
        driver.finished = true;
        car.setControls({ brake: 1 });
        assert.equal(physics.overheadHeight(state.position), null);
      } else {
        const aim = sampleEdge(lane, s + 4);
        const yaw = Math.atan2(aim.x - state.position.x, aim.z - state.position.z) - state.heading;
        car.setControls({ steer: 1.35 * Math.atan2(Math.sin(yaw), Math.cos(yaw)),
          throttle: Math.max(0, Math.min(.8, (7 - state.speed) * .16)) });
      }
    }
    if (under === drivers.length) allCovered++;
    physics.step(FIXED_DT);
  }
  assert.ok(drivers.every(driver => driver.finished && driver.covered > 200));
  assert.ok(allCovered > 150);
  t.diagnostic(allCovered + ' simultaneous four-vehicle, four-wheel frames inside the canopy');
});
