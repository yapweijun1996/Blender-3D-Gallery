import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';

import { offsetPolyline } from '../src/world/network/geometry.js';
import { pedestrianPaths } from '../src/world/paths.js';
import { PEDESTRIAN_TUNING } from '../src/world/physics/pedestrian.js';
import { VEHICLE_TYPES } from '../src/world/physics/vehicle.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildTile, buildingMesh, TILE_SIZE } from '../src/world/tile-mesh.js';
import { sampleEdge } from '../src/world/traffic.js';
import { nearestTunnelSection } from '../src/world/tunnel-prototype/geometry.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-2_-4.json', import.meta.url)));
const roadIds = ['173791997:0', '723073393:0', '545362402:0', '545362402:1', '545362402:2',
  '545362403:0', '635373148:0', '635373148:1'];
const road = roadIds.flatMap((id, i) => tile.roads.find(item => item.id === id).geometry.slice(i ? 1 : 0))
  .map(([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE]);

function laneCourse(offset) {
  const points = offsetPolyline(road, offset);
  const cumulative = [0];
  for (let i = 1; i < points.length; i++) {
    cumulative.push(cumulative[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
  }
  const stations = points.map(([x, z], i) => ({ x, z, y: 0, s: cumulative[i] }));
  return { points, cumulative, stations, length: cumulative.at(-1) };
}

test('the rendered through road clears buried kerbs and branch stubs while the adjoining streets keep their kerbs', t => {
  const { ground, towers, buildings } = buildTile(tile);
  const material = new MeshBasicMaterial({ side: DoubleSide });
  t.after(() => {
    for (const geometry of [ground, towers, buildings]) geometry?.dispose();
    material.dispose();
  });
  const mesh = new Mesh(ground, material);
  function visibleHeight(x, z) {
    const hits = new Raycaster(new Vector3(x, 1, z), new Vector3(0, -1, 0), 0, 1).intersectObject(mesh);
    return hits[0]?.point.y;
  }
  // Six underground kerbs overlap the asphalt. Three surface branch stubs reach past the two junction mouths.
  for (const [x, z] of [[-286.142, -933.696], [-288.640, -940.993], [-302.741, -943.207],
    [-294.617, -944.432], [-305.512, -938.396], [-288.754, -929.042], [-314.5893, -945.4191],
    [-317.5593, -947.0691], [-262.6763, -926.23]]) {
    assert.ok(Math.abs(visibleHeight(x, z) - .03) < .003, 'foreground road height at ' + [x, z]);
  }
  for (const [x, z] of [[-317.582121, -940.036899], [-320.531726, -941.723576], [-257.018582, -930.780443]]) {
    assert.ok(Math.abs(visibleHeight(x, z) - .12) < .003, 'adjoining street kerb at ' + [x, z]);
  }
});

test('both halves of the level-one customer corridor draw on their modeled floor and exclude street walkers', () => {
  const paths = tile.pedestrian.filter(path => path.wayId === 474174793);
  assert.deepEqual(paths.map(path => [path.id, path.indoorLevel, path.floorHeight]),
    [['474174793:0', 1, 4.8], ['474174793:2', 1, 4.8]]);
  const upper = { x: tile.x, z: tile.z, pedestrian: paths };
  assert.deepEqual(pedestrianPaths([upper]), []);
  const corridor = buildTile(upper);
  const position = corridor.ground.getAttribute('position');
  for (let i = 0; i < position.count; i++) assert.ok(Math.abs(position.getY(i) - 4.8) < .001);
  assert.equal(corridor.walkwaySolids.length, 4);
  corridor.ground.dispose();
  const outdoor = tile.pedestrian.find(path => path.class === 'footway' && path.geometry.length > 1);
  const { ground } = buildTile({ x: tile.x, z: tile.z, pedestrian: [outdoor] });
  assert.ok(ground.getAttribute('position').count > 0);
  ground.dispose();
});

test('a bus and four sedans clear both Marina Square portals in their mapped lanes', async t => {
  const physics = await createPhysicsWorld();
  t.after(() => physics.dispose());
  physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  const scene = buildTile(tile);
  for (const solid of scene.solids) physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
  for (const bridge of scene.bridgeSolids) physics.addStaticTrimesh(bridge);
  for (const panel of scene.walkwaySolids) physics.addStaticConvexHull({ vertices: panel.position });
  for (const geometry of [scene.ground, scene.buildings, scene.towers]) geometry?.dispose();

  const [a, b] = tile.pedestrian.find(path => path.id === '474174793:0').geometry;
  const span = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const vx = (b[0] - a[0]) / span, vz = (b[1] - a[1]) / span;
  const startX = a[0] + tile.x * TILE_SIZE + 6 * vx, startZ = a[1] + tile.z * TILE_SIZE + 6 * vz;
  const walker = physics.addPedestrian({ position: { x: startX, z: startZ, y: 4.8 + PEDESTRIAN_TUNING.height / 2 + .08 } });
  const drivers = [6.8, 3.4, 0, -3.4, -6.8].map((offset, index) => {
    const type = index === 0 ? 'bus' : 'sedan';
    const lane = laneCourse(offset);
    const start = sampleEdge(lane, 6);
    const car = physics.addVehicle({ type, topSpeed: 8, position: { x: start.x, z: start.z, y: 1.6 },
      heading: Math.atan2(start.dx, start.dz) });
    car.setControls({ brake: 1 });
    return { type, car, lane, samples: 0, finished: false };
  });
  for (let i = 0; i < 90; i++) physics.step(FIXED_DT);
  walker.setVelocity({ x: 1.5 * vx, z: 1.5 * vz });
  let closestWalk = Infinity;
  for (let i = 0; i < 1200 && drivers.some(driver => !driver.finished); i++) {
    const pedestrian = walker.getState();
    assert.ok(Math.abs(pedestrian.position.y - PEDESTRIAN_TUNING.height / 2 - 4.8) < .04);
    for (const driver of drivers) {
      if (driver.finished) continue;
      const { car, lane, type } = driver;
      const state = car.getState();
      const { s, lateral } = nearestTunnelSection(lane.stations, state.position);
      const tangent = sampleEdge(lane, s);
      const yaw = state.heading - Math.atan2(tangent.dx, tangent.dz);
      const half = VEHICLE_TYPES[type].chassisHalfExtents;
      const envelope = Math.abs(lateral) + half.x * Math.abs(Math.cos(yaw)) + half.z * Math.abs(Math.sin(yaw));
      assert.ok(envelope < 1.7, type + ' stays inside its 3.4 m lane at ' + s.toFixed(2));
      assert.equal(state.damage, 0);
      assert.equal(state.flipped, false);
      const overhead = physics.overheadHeight(state.position);
      closestWalk = Math.min(closestWalk, Math.hypot(state.position.x - pedestrian.position.x, state.position.z - pedestrian.position.z));
      if (overhead !== null) {
        assert.ok(Math.abs(overhead - 4.5) < .002);
        assert.ok(state.wheels.every(wheel => wheel.grounded));
        driver.samples++;
      }
      if (s >= lane.length - 10) {
        driver.finished = true;
        car.setControls({ brake: 1 });
        assert.equal(overhead, null, type + ' clears the roof on the downstream approach');
      } else {
        const target = sampleEdge(lane, s + 4);
        const delta = Math.atan2(target.x - state.position.x, target.z - state.position.z) - state.heading;
        const steer = Math.atan2(Math.sin(delta), Math.cos(delta)) * 1.35;
        car.setControls({ throttle: Math.max(0, Math.min(.8, (7 - state.speed) * .16)), steer });
      }
    }
    physics.step(FIXED_DT);
  }
  for (const driver of drivers) assert.ok(driver.finished && driver.samples > 150, driver.type + ' made a full covered run');
  assert.ok(Math.hypot(walker.getState().position.x - startX, walker.getState().position.z - startZ) > 16);
  assert.ok(closestWalk < 2, 'an upper walker passes above a moving vehicle, with planar distance ' + closestWalk);
  t.diagnostic('four-wheel samples under the soffit in each lane: ' + drivers.map(driver => driver.samples).join(', '));
});
