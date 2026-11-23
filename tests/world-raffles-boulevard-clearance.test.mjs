import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

import RAPIER from '@dimforge/rapier3d-compat';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { cross, offsetPolyline } from '../src/world/network/geometry.js';
import { pedestrianPaths } from '../src/world/paths.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { PEDESTRIAN_TUNING } from '../src/world/physics/pedestrian.js';
import { VEHICLE_TYPES } from '../src/world/physics/vehicle.js';
import { buildTile, buildingMesh, TILE_SIZE } from '../src/world/tile-mesh.js';
import { nearestTunnelSection } from '../src/world/tunnel-prototype/geometry.js';

const roofId = 393090492;
const readTile = key => JSON.parse(readFileSync(new URL('../models/world/tiles/' + key + '.json', import.meta.url)));
const tiles = [readTile('-1_-4'), readTile('-1_-5')];
const tile = tiles[0];
const edgeIds = ['649944021:0', '479745478:0', '479745478:1', '479745479:0'];
const roads = edgeIds.map(id => tile.roads.find(road => road.id === id));
const toWorld = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
const points = roads.flatMap((road, index) => road.geometry.slice(index === 0 ? 0 : 1)).map(toWorld);
const footways = tile.pedestrian.filter(({ id }) => ['749001558:4', '749001558:7'].includes(id))
  .map(({ id, geometry }) => ({ id, points: geometry.map(toWorld) }));
const up = { x: 0, y: 1, z: 0 }, down = { x: 0, y: -1, z: 0 };
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

function pathOf(line) {
  let s = 0;
  return line.map(([x, z], i) => {
    if (i > 0) s += Math.hypot(x - line[i - 1][0], z - line[i - 1][1]);
    return { x, z, y: 0, s };
  });
}

const center = pathOf(points);
const entry = center[1].s, exit = center[3].s;

function at(path, station, reference = path) {
  const s = clamp(station, 0, reference.at(-1).s);
  const next = reference.findIndex(row => row.s > s);
  const i = next < 0 ? reference.length - 1 : next;
  const a = path[i - 1], b = path[i];
  const fraction = (s - reference[i - 1].s) / (reference[i].s - reference[i - 1].s);
  return { x: a.x + (b.x - a.x) * fraction, z: a.z + (b.z - a.z) * fraction,
    heading: Math.atan2(b.x - a.x, b.z - a.z) };
}

function insideRing(ring, x, z) {
  let inside = false;
  for (let i = 0, last = ring.length - 1; i < ring.length; last = i++) {
    const [ax, az] = ring[last], [bx, bz] = ring[i];
    if ((az > z) !== (bz > z) && x < ax + (bx - ax) * (z - az) / (bz - az)) inside = !inside;
  }
  return inside;
}

function ray(physics, position, direction, distance = 12) {
  return physics.world.castRay(new RAPIER.Ray(position, direction), distance, true, RAPIER.QueryFilterFlags.ONLY_FIXED);
}

function visibleHits(meshes, position, direction, distance = 12) {
  return new Raycaster(new Vector3(position.x, position.y, position.z),
    new Vector3(direction.x, direction.y, direction.z), 0, distance).intersectObjects(meshes);
}

async function buildWorld(t, data = tiles) {
  const physics = await createPhysicsWorld();
  const material = new MeshBasicMaterial({ side: DoubleSide });
  const ground = [], buildings = [], roofs = [], roofSolids = [], walkways = [], buildingIds = new Map();
  t.after(() => {
    for (const mesh of [...ground, ...buildings]) mesh.geometry.dispose();
    material.dispose();
    physics.dispose();
  });
  const floor = physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  for (const source of data) {
    const built = buildTile(source);
    if (built.ground) ground.push(new Mesh(built.ground, material));
    for (const geometry of [built.buildings, built.towers]) {
      if (geometry) buildings.push(new Mesh(geometry, material));
    }
    for (const solid of built.solids) {
      const collider = physics.addStaticTrimesh(buildingMesh(solid.ring, solid.height, solid.base));
      buildingIds.set(collider.handle, solid.id);
      if (solid.id === roofId) {
        roofs.push(collider.handle);
        roofSolids.push(solid);
      }
    }
    for (const solid of built.bridgeSolids) physics.addStaticTrimesh(solid);
    for (const panel of built.walkwaySolids ?? []) {
      assert.equal(panel.convex, true);
      const collider = physics.addStaticConvexHull({ vertices: panel.position, friction: 1 });
      walkways.push(collider.handle);
    }
  }
  physics.step(FIXED_DT);
  return { physics, floor, ground, buildings, roofs, roofSolids, walkways, buildingIds };
}

test('unannotated tiles diagnose the old road gap and obstruction at the entrance', async t => {
  const unannotated = tiles.map(({ roadSurfaces, ...source }) => ({
    ...source,
    roads: source.roads.map(({ passageRoof, ...road }) => road),
    buildings: source.buildings.map(({ minHeight, ...building }) => building),
    pedestrian: source.pedestrian.map(({ walkFrom, besideCarriageway, ...path }) => path),
  }));
  const { physics, ground, roofs, roofSolids } = await buildWorld(t, unannotated);
  assert.equal(roofSolids.length, 2);
  assert.ok(roofSolids.every(solid => solid.base === undefined && solid.height === 6));
  const start = at(center, 6);
  const obstruction = ray(physics, { ...start, y: 1.4 },
    { x: Math.sin(start.heading), y: 0, z: Math.cos(start.heading) }, 16);
  assert.ok(roofs.includes(obstruction?.collider.handle), 'the default ground-level canopy wall blocked the aisle');
  const middleOfMissingRoad = at(center, entry + 3);
  assert.ok(!visibleHits(ground, { ...middleOfMissingRoad, y: .08 }, down, .1)
    .some(hit => Math.abs(hit.point.y - .03) < .003));
});

test('all five portal envelopes have continuous rendered asphalt and modeled Y=0 to Y=4.5 clearance where covered', async t => {
  assert.deepEqual(roads.map(road => road.passageRoof ?? null), [null, roofId, roofId, null]);
  assert.ok(roads.every(road => road.oneway && road.lanes === 5 && road.width === 17));
  assert.ok(roads.slice(1, 3).every(road => road.tunnel && road.layer === -1));
  const { physics, floor, ground, buildings, roofs, roofSolids, walkways } = await buildWorld(t);
  assert.equal(roofSolids.length, 2);
  for (const solid of roofSolids) {
    assert.equal(solid.base, 4.5);
    assert.equal(solid.height, 1.5);
  }
  const ring = tile.buildings.find(building => building.id === roofId).geometry.map(toWorld);
  // Tight sampling across the mitered joints catches gaps hidden by testing road center points alone.
  const stations = new Set(Array.from({ length: 141 }, (_, i) => entry - 2.5 + i * .2));
  for (const { s } of center.slice(1, -1)) {
    for (const offset of [-.06, -.025, 0, .025, .06]) stations.add(s + offset);
  }
  const covered = [], firstLast = [];
  let shoulderProbes = 0;
  for (const offset of [-8.45, -6.8, -5.1, -3.4, -1.7, 0, 1.7, 3.4, 5.1, 6.8, 8.45]) {
    const rail = pathOf(offsetPolyline(points, offset));
    let first = Infinity, last = -Infinity, count = 0;
    for (const station of [...stations].sort((a, b) => a - b)) {
      const point = at(rail, station, center);
      const line = station.toFixed(3) + ' m / ' + offset + ' m';
      const visible = visibleHits(ground, { ...point, y: .08 }, down, .1)[0];
      assert.ok(visible && visible.point.y >= .029 && visible.point.y <= .033, 'continuous lane paint at ' + line);
      const support = ray(physics, { ...point, y: 2 }, down);
      assert.ok(support && (support.collider.handle === floor.handle || walkways.includes(support.collider.handle)),
        'stock collision floor or mapped shoulder panel at ' + line);
      const floorY = 2 - support.timeOfImpact;
      assert.ok(Math.abs(floorY) < .002, 'physical floor stays at Y=0 at ' + line);
      if (walkways.includes(support.collider.handle)) shoulderProbes++;

      const soffit = ray(physics, { ...point, y: .1 }, up);
      if (insideRing(ring, point.x, point.z)) {
        count++;
        first = Math.min(first, station);
        last = Math.max(last, station);
        assert.ok(roofs.includes(soffit?.collider.handle), 'the actual canopy is overhead at ' + line);
        assert.ok(Math.abs(soffit.timeOfImpact + .1 - floorY - 4.5) < .002,
          'clearance is measured from the actual colliding support at ' + line);
        const renderedSoffit = visibleHits(buildings, { ...point, y: .1 }, up)[0];
        assert.ok(renderedSoffit && Math.abs(renderedSoffit.point.y - 4.5) < .002, 'rendered soffit matches collision');
        assert.ok(renderedSoffit.face.normal.y < -.99, 'roof underside faces the passage');
        const renderedTop = visibleHits(buildings, { ...point, y: 8 }, down)[0];
        assert.ok(renderedTop && Math.abs(renderedTop.point.y - 6) < .002, 'source top height is maintained');
      } else {
        assert.equal(soffit, null, 'no other mapped building obstructs the open portal at ' + line);
      }
    }
    assert.ok(count > 80 && first < entry + 1 && last > exit - 1);
    covered.push(count);
    firstLast.push([first, last]);
  }
  assert.ok(Math.min(...firstLast.map(span => span[0])) < entry - .3, 'the canopy starts before the western tagged line');
  assert.ok(Math.max(...firstLast.map(span => span[1])) > exit + .09, 'the canopy extends past the eastern tagged line');
  t.diagnostic(covered.reduce((sum, count) => sum + count, 0) +
    ' matching roof/pavement probes across staggered portal edges, ' + shoulderProbes + ' on the level shoulder panels');
});

function pointDistance(point, a, b) {
  const dx = b[0] - a[0], dz = b[1] - a[1];
  const t = clamp(((point[0] - a[0]) * dx + (point[1] - a[1]) * dz) / (dx * dx + dz * dz), 0, 1);
  return Math.hypot(point[0] - a[0] - dx * t, point[1] - a[1] - dz * t);
}

function segmentGap(a, b, c, d) {
  const overlappingBounds = [0, 1].every(i =>
    Math.max(a[i], b[i]) >= Math.min(c[i], d[i]) && Math.max(c[i], d[i]) >= Math.min(a[i], b[i]));
  if (overlappingBounds && cross(a, b, c) * cross(a, b, d) <= 0 && cross(c, d, a) * cross(c, d, b) <= 0) return 0;
  return Math.min(pointDistance(a, c, d), pointDistance(b, c, d), pointDistance(c, a, b), pointDistance(d, a, b));
}

function busToFootways(state) {
  const { x, z } = state.position, { x: width, z: length } = VEHICLE_TYPES.bus.chassisHalfExtents;
  const dx = Math.sin(state.heading), dz = Math.cos(state.heading);
  const corners = [[-1, -1], [-1, 1], [1, 1], [1, -1]].map(([side, front]) =>
    [x + side * dz * width + front * dx * length, z - side * dx * width + front * dz * length]);
  let gap = Infinity;
  for (const { points: path } of footways) {
    for (let j = 1; j < path.length; j++) {
      if (insideRing(corners, ...path[j - 1]) || insideRing(corners, ...path[j])) return -PEDESTRIAN_TUNING.radius;
      for (let i = 0; i < corners.length; i++) {
        gap = Math.min(gap, segmentGap(path[j - 1], path[j], corners[i], corners[(i + 1) % corners.length]));
      }
    }
  }
  return gap - PEDESTRIAN_TUNING.radius;
}

test('a bus and four sedans drive their own lanes through both portals in one physics world', async t => {
  const { physics, roofs } = await buildWorld(t);
  const drivers = [6.8, 3.4, 0, -3.4, -6.8].map((offset, index) => {
    const type = index === 0 ? 'bus' : 'sedan';
    const path = pathOf(offsetPolyline(points, offset));
    const start = at(path, 4);
    const car = physics.addVehicle({ type, topSpeed: 8, position: { ...start, y: 1.6 }, heading: start.heading });
    car.setControls({ brake: 1 });
    return { car, type, path, coveredFrames: 0, finished: false };
  });
  for (let i = 0; i < 90; i++) physics.step(FIXED_DT);
  let closestPedestrian = Infinity;
  for (let frame = 0; frame < 60 * 21 && drivers.some(driver => !driver.finished); frame++) {
    for (const driver of drivers) {
      if (driver.finished) continue;
      const { car, path, type } = driver;
      const state = car.getState();
      const { s, lateral } = nearestTunnelSection(path, state.position);
      const target = at(path, s + 4.0);
      const difference = Math.atan2(target.x - state.position.x, target.z - state.position.z) - state.heading;
      const angle = Math.atan2(Math.sin(difference), Math.cos(difference));
      const deviation = state.heading - at(path, s).heading;
      const { x, z } = VEHICLE_TYPES[type].chassisHalfExtents;
      const sweptWidth = x * Math.abs(Math.cos(deviation)) + z * Math.abs(Math.sin(deviation));
      assert.ok(Math.abs(lateral) + sweptWidth < 1.7, type + ' remains in its own lane');
      assert.ok(state.damage < .01 && !state.flipped);
      if (type === 'bus') closestPedestrian = Math.min(closestPedestrian, busToFootways(state));
      if (s > entry + 3 && s < exit - 3) {
        driver.coveredFrames++;
        assert.ok(state.wheels.every(wheel => wheel.grounded), type + ' has four-wheel support under the canopy');
        assert.ok(roofs.includes(ray(physics, state.position, up)?.collider.handle));
      }
      if (s > exit + 8) {
        driver.finished = true;
        car.setControls({ brake: 1 });
      } else {
        car.setControls({ throttle: clamp((7 - state.speed) * .16, 0, .8), steer: clamp(angle * 1.35, -.55, .55) });
      }
    }
    physics.step(FIXED_DT);
  }
  for (const driver of drivers) assert.ok(driver.finished && driver.coveredFrames > 55, driver.type + ' crosses both portals');
  assert.ok(closestPedestrian > .25, 'the actual outer-lane bus clears both original walker paths: ' + closestPedestrian);
  t.diagnostic('least bus-to-walker capsule margin ' + closestPedestrian.toFixed(3) + ' m');
});

test('roadside paths keep simulated ground support and the separate Millenia Walk obstruction stays identified', async t => {
  const { physics, buildingIds, walkways } = await buildWorld(t);
  assert.equal(walkways.length, 8, 'the real tile builder installs paired panels for each verified segment');
  const adjacent = pathOf(footways.find(({ id }) => id === '749001558:4').points);
  const access = at(adjacent, 8.9);
  const obstruction = ray(physics, { ...access, y: .9 },
    { x: -Math.sin(access.heading), y: 0, z: -Math.cos(access.heading) }, 4);
  assert.equal(buildingIds.get(obstruction?.collider.handle), 747734200,
    'the first portion of the eastern footpath still meets the mapped Millenia Walk wall');
  assert.equal(footways.length, 2);
  for (const footway of footways) {
    const source = tile.pedestrian.find(({ id }) => id === footway.id);
    const [route] = pedestrianPaths([{ ...tile, pedestrian: [source] }]);
    const from = footway.id === '749001558:4' ? 1 : 0;
    assert.deepEqual(route.points, footway.points.slice(from));
    const path = pathOf(route.points), end = path.at(-1).s;
    const start = at(path, .3);
    const walker = physics.addPedestrian({ position: { ...start, y: 1.1 } });
    let s = 0, frames = 0, grounded = 0, minFeet = Infinity;
    for (; frames < 60 * (end + 8) && s < end - .4; frames++) {
      const state = walker.getState();
      const nearest = nearestTunnelSection(path, state.position);
      s = nearest.s;
      const ahead = at(path, s + .6), dx = ahead.x - state.position.x, dz = ahead.z - state.position.z;
      const distance = Math.hypot(dx, dz) || 1;
      walker.setVelocity({ x: 1.45 * dx / distance, z: 1.45 * dz / distance });
      physics.step(FIXED_DT);
      grounded += Number(state.grounded);
      minFeet = Math.min(minFeet, state.position.y - PEDESTRIAN_TUNING.height / 2);
      assert.ok(Math.abs(nearest.lateral) < .65, footway.id + ' remains on the mapped strip');
      assert.ok(state.position.y >= PEDESTRIAN_TUNING.height / 2 - .025, footway.id + ' feet Y=' +
        (state.position.y - PEDESTRIAN_TUNING.height / 2) + ' at s=' + s + ' frame=' + frames + ' grounded=' + state.grounded);
    }
    assert.ok(s > end - .45 && grounded / frames > .98,
      footway.id + ' reaches its resolved end (' + s.toFixed(2) + ' m, ' + (grounded / frames).toFixed(3) + ' grounded)');
    t.diagnostic(footway.id + ' walks ' + end.toFixed(2) + ' m, minimum feet Y=' + minFeet.toFixed(3) + ' m');
    physics.removePedestrian(walker);
  }
});
