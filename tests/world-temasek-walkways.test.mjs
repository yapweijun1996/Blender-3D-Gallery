import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';

import RAPIER from '@dimforge/rapier3d-compat';
import { applyTemasekWalkways } from '../scripts/world/temasek-walkways.mjs';
import { DoubleSide, Mesh, MeshBasicMaterial, Raycaster, Vector3 } from 'three';
import { cross, offsetPolyline } from '../src/world/network/geometry.js';
import { pedestrianPaths, samplePath } from '../src/world/paths.js';
import { PEDESTRIAN_TUNING } from '../src/world/physics/pedestrian.js';
import { VEHICLE_TYPES } from '../src/world/physics/vehicle.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildingMesh, buildTile, TILE_SIZE } from '../src/world/tile-mesh.js';
import { nearestTunnelSection } from '../src/world/tunnel-prototype/geometry.js';

const tile = JSON.parse(readFileSync(new URL('../models/world/tiles/-1_-6.json', import.meta.url)));
const world = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
const footway = id => tile.pedestrian.find(path => path.id === id);
const roofId = 393210509;
const upper = footway('460300678:6');
const radius = PEDESTRIAN_TUNING.radius;
const pathsBySide = [
  {
    walkways: ['1321783357:1', '1321783356:0'],
    support: ['1321783357:0', '1321783355:0', '1494547193:0'],
    road: ['21702431:4', '395443687:0', '750875319:0'],
    conflict: [35, 59],
  },
  {
    walkways: ['1321783027:0'],
    support: ['1321783025:0'],
    road: ['21701084:0', '395443688:0', '750875316:0'],
    conflict: [18, 53],
  },
];

test('malformed or unsupported canopy and walkway source inputs leave the tile unchanged', () => {
  const snapshot = JSON.parse(gunzipSync(readFileSync(new URL(
    '../scripts/world/fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
  const ways = new Map(snapshot.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
  const unprepared = structuredClone(tile);
  for (const path of unprepared.pedestrian.filter(path => path.deckGeometry || path.walkGeometry)) {
    for (const field of ['deckGeometry', 'walkGeometry', 'besideCarriageway', 'indoorLevel', 'floorHeight']) delete path[field];
  }
  const prepare = structuredClone(unprepared);
  assert.equal(applyTemasekWalkways(prepare, ways), true);
  const replaceTags = (sources, id, tags) => {
    const old = sources.get(id);
    sources.set(id, { ...old, tags: { ...old.tags, ...tags } });
  };
  const cases = [
    ['missing roof ring', candidate => { delete candidate.buildings.find(building => building.id === roofId).geometry; }],
    ['concave roof ring', candidate => {
      const ring = candidate.buildings.find(building => building.id === roofId).geometry;
      // Place the second corner inside the triangle formed by the other three corners.
      ring[1] = [0, 1].map(axis => (ring[0][axis] + ring[2][axis] + ring[3][axis]) / 3);
    }],
    ['missing a mapped sidewalk knot', candidate => { candidate.pedestrian.find(path => path.id === '1321783027:0').geometry[1] = null; }],
    ['unsupported roof height source', (_, source) => replaceTags(source, roofId, { min_height: '4.5' })],
    ['different raw indoor floor', (_, source) => replaceTags(source, 460300678, { level: '2' })],
    ['unexpected mapped sidewalk grade', (_, source) => replaceTags(source, 1321783027, { incline: '8%' })],
  ];
  for (const [name, change] of cases) {
    const candidate = structuredClone(unprepared);
    const mutableWays = new Map(ways);
    change(candidate, mutableWays);
    const before = structuredClone(candidate);
    assert.equal(applyTemasekWalkways(candidate, mutableWays), false, name);
    assert.deepEqual(candidate, before, name);
  }
});

const up = { x: 0, y: 1, z: 0 }, down = { x: 0, y: -1, z: 0 };
const clamp = value => Math.min(1, Math.max(0, value));
const pairs = points => points.slice(1).map((b, i) => [points[i], b]);
const closed = points => [...points, points[0]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1]];
const determinant = ([ax, az], [bx, bz]) => ax * bz - az * bx;
const norm = point => Math.hypot(...point);

function plan(pedestrian) {
  return pedestrianPaths([{ ...tile, pedestrian }]);
}

function pointGap(point, a, b) {
  const [dx, dz] = sub(b, a), [x, z] = sub(point, a);
  const t = clamp((x * dx + z * dz) / (dx * dx + dz * dz));
  return Math.hypot(x - t * dx, z - t * dz);
}

function segmentGap(a, b, c, d) {
  const bounds = [0, 1].every(i =>
    Math.max(a[i], b[i]) >= Math.min(c[i], d[i]) && Math.max(c[i], d[i]) >= Math.min(a[i], b[i]));
  if (bounds && cross(a, b, c) * cross(a, b, d) <= 0 && cross(c, d, a) * cross(c, d, b) <= 0) return 0;
  return Math.min(pointGap(a, c, d), pointGap(b, c, d), pointGap(c, a, b), pointGap(d, a, b));
}

function shiftedBusHulls(road) {
  const source = road.flatMap((id, i) => tile.roads.find(edge => edge.id === id).geometry.slice(i ? 1 : 0)).map(world);
  const lane = offsetPolyline(source, 1.7);
  const { x: width, z: length } = VEHICLE_TYPES.bus.chassisHalfExtents;
  const heading = (a, b) => Math.atan2(b[1] - a[1], b[0] - a[0]);
  const hull = (a, b, angle) => {
    const dx = Math.cos(angle), dz = Math.sin(angle);
    return [[a, -1, -1], [b, 1, -1], [b, 1, 1], [a, -1, 1]].map(([[x, z], along, side]) =>
      [x + along * dx * length + side * dz * width, z + along * dz * length - side * dx * width]);
  };
  const shapes = pairs(lane).map(([a, b]) => hull(a, b, heading(a, b)));
  for (let i = 1; i < lane.length - 1; i++) {
    const before = heading(lane[i - 1], lane[i]), after = heading(lane[i], lane[i + 1]);
    const delta = Math.atan2(Math.sin(after - before), Math.cos(after - before));
    const count = Math.ceil(Math.abs(delta) / .0035) || 1;
    for (let step = 0; step <= count; step++) shapes.push(hull(lane[i], lane[i], before + delta * step / count));
  }
  return shapes;
}

function clearance(walk, road) {
  let min = Infinity;
  const outlines = shiftedBusHulls(road).map(hull => pairs(closed(hull)));
  for (const [a, b] of pairs(walk.points)) {
    for (const hull of outlines) {
      if ([a, b].some(point => hull.every(([c, d]) => cross(c, d, point) >= 0) ||
          hull.every(([c, d]) => cross(c, d, point) <= 0))) return -radius;
      for (const [c, d] of hull) min = Math.min(min, segmentGap(a, b, c, d));
    }
  }
  return min - radius;
}

test('actual pedestrian plans keep joined and tapered routes within the painted sidewalk with bus clearance', t => {
  for (const { walkways, support, road, conflict } of pathsBySide) {
    const sources = walkways.map(footway);
    const [walk, extra] = plan(sources);
    assert.ok(walk && !extra, 'one linked actor route per side');
    assert.deepEqual(walk.points[0], world(sources[0].geometry[0]));
    assert.deepEqual(walk.points.at(-1), world(sources.at(-1).geometry.at(-1)));
    assert.ok(sources.every(path => path.besideCarriageway));

    const gap = clearance(walk, road);
    // The angular increment allows ~1 cm of unobserved swept extent between sampled yaws.
    assert.ok(gap >= .25, 'the complete shifted capsule stays clear of the bus hulls: ' + gap);
    t.diagnostic(walkways.join(' + ') + ' minimum bus clearance ' + gap.toFixed(3) + ' m');
    const material = new MeshBasicMaterial({ side: DoubleSide });
    const mesh = new Mesh(buildTile({ x: tile.x, z: tile.z, pedestrian: [...walkways, ...support].map(footway) }).ground, material);
    t.after(() => { mesh.geometry.dispose(); material.dispose(); });
    const ray = new Raycaster();
    const worldDown = new Vector3(0, -1, 0);
    const [start, end] = conflict;
    for (let s = start; s <= end; s += .1) {
      const { x, z } = samplePath(walk, s);
      for (let angle = 0; angle < 24; angle++) {
        const direction = angle * Math.PI / 12;
        const clearance = radius + .15;
        ray.set(new Vector3(x + Math.sin(direction) * clearance, 1, z + Math.cos(direction) * clearance), worldDown);
        assert.ok(ray.intersectObject(mesh).length, 'complete capsule is inset from the painted strip at ' + s.toFixed(2));
      }
    }
  }
});

async function physicsTile(t) {
  const physics = await createPhysicsWorld();
  const built = buildTile(tile);
  t.after(() => {
    for (const geom of [built.ground, built.buildings, built.towers]) geom?.dispose();
    physics.dispose();
  });
  physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  let roof;
  for (const solid of built.solids) {
    const handle = physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
    if (solid.id === roofId) roof = handle;
  }
  const support = built.walkwaySolids.map(panel => ({
    top: panel.position[1],
    handle: physics.addStaticConvexHull({ vertices: panel.position, friction: 1 }),
  }));
  for (const deck of built.bridgeSolids) physics.addStaticTrimesh(deck);
  physics.step(FIXED_DT);
  return { physics, roof, support };
}

function walkCapsule(physics, path, floor, t) {
  const sections = path.points.map(([x, z], i) => ({ x, z, y: floor, s: path.cumulative[i] }));
  const start = samplePath(path, .45);
  const walker = physics.addPedestrian({ position: { x: start.x, y: floor + 1.10, z: start.z } });
  let s = 0, grounded = 0, minFeet = Infinity, frames = 0;
  try {
    for (; frames < 60 * (path.length + 10) && s < path.length - .45; frames++) {
      const state = walker.getState();
      const nearest = nearestTunnelSection(sections, state.position);
      s = nearest.s;
      assert.ok(Math.abs(nearest.lateral) < .15, 'physical walker follows its modeled route');
      const next = samplePath(path, s + .5), dx = next.x - state.position.x, dz = next.z - state.position.z;
      const distance = Math.hypot(dx, dz) || 1;
      walker.setVelocity({ x: 1.45 * dx / distance, z: 1.45 * dz / distance });
      physics.step(FIXED_DT);
      grounded += Number(state.grounded);
      minFeet = Math.min(minFeet, state.position.y - PEDESTRIAN_TUNING.height / 2);
    }
    assert.ok(s >= path.length - .45 && grounded / frames > .98, 'the capsule walks the full supported route');
    assert.ok(minFeet >= floor - .012, 'feet stay at the modeled support level');
    t.diagnostic(path.length.toFixed(2) + ' m, minimum feet Y=' + minFeet.toFixed(3) + ' m');
  } finally {
    physics.removePedestrian(walker);
  }
}

test('both exterior walk routes have continuous physical support on the installed Y=0 panels', async t => {
  const { physics, support } = await physicsTile(t);
  assert.equal(support.filter(panel => panel.top === 0).length, 16);
  for (const { walkways } of pathsBySide) walkCapsule(physics, plan(walkways.map(footway))[0], 0, t);
});

function crossing(a, b, c, d) {
  const path = sub(b, a), edge = sub(d, c);
  const at = determinant(sub(c, a), edge) / determinant(path, edge);
  return [a[0] + path[0] * at, a[1] + path[1] * at];
}

test('the upper indoor crossing is clipped to Suntec at Y=5.3 and decoupled from the street graph', async t => {
  assert.equal(upper.indoorLevel, 1);
  assert.equal(upper.floorHeight, 5.3);
  assert.deepEqual(upper.geometry, [[192.52, 207.47], [178.55, 175.38], [44.22, 98.59]]);
  assert.deepEqual(plan([upper, { ...upper, class: 'footway' }]), []);
  const deckPaint = buildTile({ x: tile.x, z: tile.z, pedestrian: [upper] }).ground;
  t.after(() => deckPaint.dispose());
  const footprint = tile.buildings.find(building => building.id === roofId).geometry.map(world);
  const vertices = deckPaint.attributes.position.array;
  const orientation = Math.sign(cross(...footprint.slice(0, 3)));
  for (let i = 0; i < vertices.length; i += 3) {
    assert.ok(Math.abs(vertices[i + 1] - 5.3) < .001, 'the indoor path contributes no outdoor paint');
    const point = [vertices[i], vertices[i + 2]];
    assert.ok(pairs(footprint).every(([a, b]) => orientation * cross(a, b, point) / norm(sub(b, a)) >= radius));
  }

  const { physics, roof, support } = await physicsTile(t);
  const elevated = support.filter(panel => Math.abs(panel.top - 5.3) < .001);
  assert.equal(elevated.length, 2);
  const ray = (x, y, z, direction) => physics.world.castRay(new RAPIER.Ray({ x, y, z }, direction), 10, true,
    RAPIER.QueryFilterFlags.ONLY_FIXED);
  const [a, b] = upper.deckGeometry.map(world);
  for (const id of ['395443687:0', '395443688:0']) {
    const [c, d] = tile.roads.find(edge => edge.id === id).geometry.map(world);
    const [x, z] = crossing(a, b, c, d);
    const soffit = ray(x, 1, z, up);
    const walk = ray(x, 6.3, z, down);
    assert.equal(soffit.collider.handle, roof.handle);
    assert.ok(Math.abs(soffit.timeOfImpact - 4) < .002);
    assert.ok(elevated.some(panel => panel.handle.handle === walk.collider.handle));
    assert.ok(Math.abs(walk.timeOfImpact - 1) < .002);
  }
  const [path] = plan([{ class: 'footway', geometry: upper.deckGeometry }]);
  walkCapsule(physics, path, 5.3, t);
});
