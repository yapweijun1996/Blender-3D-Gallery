import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import RAPIER from '@dimforge/rapier3d-compat';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildTile, buildingMesh, TILE_SIZE } from '../src/world/tile-mesh.js';
import { buildTrafficGraph, createTraffic, sampleEdge, VEHICLE_TYPES } from '../src/world/traffic.js';

const loadTile = key => JSON.parse(readFileSync(new URL(`../models/world/tiles/${key}.json`, import.meta.url)));
const tile = loadTile('-3_-4');
const shellId = 620812487;
const tunnel = '532351088:0';
const routeIds = ['710062599:1', '684524081:0', tunnel, '159938518:0', '684524082:0'];
const localToWorld = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
const road = id => tile.roads.find(road => road.id === id);
const [[ax, az], [bx, bz]] = road(tunnel).geometry.map(localToWorld);
const entry = { x: ax, z: az };
const length = Math.hypot(bx - ax, bz - az);
const dx = (bx - ax) / length, dz = (bz - az) / length;
const mid = { x: (ax + bx) / 2, y: 1, z: (az + bz) / 2 };
const points = routeIds.flatMap((id, i) => road(id).geometry.slice(i ? 1 : 0)).map(localToWorld);
const edges = points.slice(1).map(([x, z], i) => {
  const [ax, az] = points[i];
  return { x: ax, z: az, dx: x - ax, dz: z - az, length: Math.hypot(x - ax, z - az) };
});
const cumulative = [0];
for (const edge of edges) cumulative.push(cumulative.at(-1) + edge.length);
const course = { points, cumulative, length: cumulative.at(-1) };

function station({ x, z }) {
  let best = { distance: Infinity, s: 0 };
  for (const [i, edge] of edges.entries()) {
    const px = x - edge.x, pz = z - edge.z;
    const t = Math.max(0, Math.min(1, (px * edge.dx + pz * edge.dz) / edge.length ** 2));
    const distance = Math.hypot(px - t * edge.dx, pz - t * edge.dz);
    if (distance < best.distance) best = { distance, s: cumulative[i] + t * edge.length };
  }
  return best;
}

async function buildPhysics(data, t) {
  const built = buildTile(data);
  const physics = await createPhysicsWorld();
  t.after(() => {
    for (const geometry of [built.ground, built.buildings, built.towers]) geometry?.dispose();
    physics.dispose();
  });
  physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  for (const solid of built.solids) physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
  for (const panel of built.walkwaySolids) physics.addStaticConvexHull({ vertices: panel.position });
  for (const bridge of built.bridgeSolids) physics.addStaticTrimesh(bridge);
  physics.step(FIXED_DT);
  return { built, physics };
}

test('the render mesh and Rapier open the same two mouths and preserve the adjoining facade', async t => {
  const original = structuredClone(tile);
  delete original.buildings.find(({ id }) => id === shellId).passages;
  const closed = await buildPhysics(original, t);
  const opened = await buildPhysics(tile, t);
  const material = new MeshBasicMaterial({ side: DoubleSide });
  t.after(() => material.dispose());

  function horizontal(scene, offset, y = 1.2) {
    const x = ax - 3 * dx - offset * dz, z = az - 3 * dz + offset * dx;
    const width = 12;
    const collider = scene.physics.world.castRay(new RAPIER.Ray({ x, y, z }, { x: dx, y: 0, z: dz }), width, true, RAPIER.QueryFilterFlags.ONLY_FIXED);
    const render = new Raycaster(new Vector3(x, y, z), new Vector3(dx, 0, dz), 0, width)
      .intersectObject(new Mesh(scene.built.buildings, material)).map(hit => hit.distance);
    return { collider: collider?.timeOfImpact ?? null, render };
  }

  const wall = horizontal(closed, 0);
  assert.equal(wall.render.length, 2, 'the original facade spans the roadway at both mouths');
  assert.ok(Math.abs(wall.collider - 3.148) < .002);
  assert.ok(Math.abs(wall.render[0] - wall.collider) < .002);
  for (const offset of [-1.24, 0, 1.24]) {
    const clear = horizontal(opened, offset);
    assert.equal(clear.collider, null);
    assert.deepEqual(clear.render, []);
  }
  assert.ok(horizontal(opened, 3).collider, 'the adjoining facade still collides');
  assert.ok(horizontal(opened, 0, 4.8).collider, 'the facade above the soffit still collides');
  assert.equal(opened.physics.supportHeight(mid), 0);
  assert.ok(Math.abs(opened.physics.overheadHeight(mid) - 4.5) < .001);

  const asphalt = new Mesh(opened.built.ground, material);
  const surface = (x, z) => new Raycaster(new Vector3(x, .3, z), new Vector3(0, -1, 0), 0, .3).intersectObject(asphalt)[0]?.point.y;
  for (const offset of [-1.2, 0, 1.2]) {
    assert.ok(Math.abs(surface(mid.x - offset * dz, mid.z + offset * dx) - .03) < .001, 'asphalt spans the lane under the shell');
  }
  const upstream = sampleEdge(course, 8);
  for (const offset of [-2.8, 2.8]) {
    assert.ok(Math.abs(surface(upstream.x - offset * upstream.dz, upstream.z + offset * upstream.dx) - .03) < .001,
      'both sides of the original 6.8 m approach remain asphalt');
  }
});

test('stock sedan, bus and lorry drive the modeled opening with four grounded wheels and no impacts', async t => {
  const { physics } = await buildPhysics(tile, t);
  const start = sampleEdge(course, 12);
  for (const type of ['sedan', 'bus', 'lorry']) {
    const car = physics.addVehicle({ type, topSpeed: 7, position: { x: start.x, y: 1.6, z: start.z },
      heading: Math.atan2(start.dx, start.dz) });
    car.setControls({ brake: 1 });
    for (let frame = 0; frame < 90; frame++) physics.step(FIXED_DT);

    let entered = 0, finish = false;
    for (let frame = 0; frame < 1200; frame++) {
      const state = car.getState();
      const here = station(state.position);
      assert.ok(here.distance < .15, `${type} follows the one-lane centerline`);
      assert.equal(state.damage, 0);
      assert.equal(state.flipped, false);
      const overhead = physics.overheadHeight(state.position);
      if (overhead !== null) {
        assert.ok(Math.abs(overhead - 4.5) < .001);
        assert.ok(state.wheels.every(wheel => wheel.grounded));
        entered++;
      }
      if (here.s > 55) {
        assert.equal(overhead, null);
        finish = true;
        break;
      }

      const ahead = sampleEdge(course, here.s + 7);
      const delta = Math.atan2(ahead.x - state.position.x, ahead.z - state.position.z) - state.heading;
      const steer = Math.atan2(Math.sin(delta), Math.cos(delta)) * 1.35;
      car.setControls({ steer, throttle: Math.max(0, Math.min(.8, (6 - state.speed) * .16)) });
      physics.step(FIXED_DT);
    }
    assert.ok(finish && entered >= 55, `${type} clears both mouths in the same grounded run`);
    physics.removeVehicle(car);
  }
});

test('ambient vehicles continue through the short exit with exact overshoot and bypass both covered driveways', () => {
  const graph = buildTrafficGraph([tile, loadTile('-2_-4'), loadTile('-2_-5')]);
  assert.equal(graph.edges.has('684523974:0'), false);
  assert.equal(graph.edges.has('1431080692:0'), false);
  const lane = graph.edges.get(tunnel);
  assert.ok(lane, 'the annotated tunnel is open to ambient traffic');
  assert.equal(lane.layer, 0);
  const exit = graph.edges.get('159938518:0');
  assert.ok(exit.retainShortTraffic);
  const traffic = createTraffic({ graph, maxVehicles: 0, random: () => 0 });
  const start = lane.length - .1;
  const vehicle = { id: 1, type: VEHICLE_TYPES.find(type => type.id === 'sedan'), edge: tunnel, direction: 1, s: start, lane: 0, speed: 11, wait: 0 };
  traffic.vehicles.push(vehicle);
  traffic.update(.35, entry);
  assert.equal(vehicle.edge, '684524082:0');
  assert.equal(vehicle.direction, 1);
  assert.equal(vehicle.lane, 0);
  assert.ok(Math.abs(vehicle.s - (.35 * vehicle.speed - .1 - exit.length)) < 1e-6);
  assert.equal(traffic.pose(vehicle).y, 0);

  const arriving = { ...vehicle, edge: '684524081:0', s: 2, speed: 8, lane: 0 };
  traffic.vehicles.splice(0, 1, arriving);
  const visited = new Set();
  for (let frame = 0; frame < 400 && traffic.vehicles.includes(arriving); frame++) {
    traffic.update(FIXED_DT, entry);
    visited.add(arriving.edge);
  }
  assert.deepEqual([...visited].slice(0, 4), routeIds.slice(1));
});
