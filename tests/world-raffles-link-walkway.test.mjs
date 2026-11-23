import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';

import RAPIER from '@dimforge/rapier3d-compat';
import { applyRafflesLinkWalkway } from '../scripts/world/raffles-link-walkway.mjs';
import { between, splitByRing } from '../src/world/network/polygon.js';
import { pedestrianPaths } from '../src/world/paths.js';
import { PEDESTRIAN_TUNING } from '../src/world/physics/pedestrian.js';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { buildingMesh, buildTile, TILE_SIZE } from '../src/world/tile-mesh.js';

const BRIDGE = 460302684;
const SHELL = 620812487;
const WEST = 46594821;
const EAST = 303311927;
const FLOOR = 4.8;
const PATHS = [460302683, BRIDGE, 460300683];
const readTile = key => JSON.parse(readFileSync(new URL(`../models/world/tiles/${key}.json`, import.meta.url)));
const tile = readTile('-3_-4');
const neighbors = [readTile('-2_-4')];
const snapshot = JSON.parse(gunzipSync(readFileSync(new URL(
  '../scripts/world/fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
const ways = new Map(snapshot.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
const path = (id, candidate = tile) => candidate.pedestrian.find(path => path.id === id + ':0');
const shell = candidate => candidate.buildings.find(building => building.id === SHELL);
const world = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
const length = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const near = (actual, expected, tolerance = .002) =>
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < tolerance, `${actual} ≈ ${expected}`);

function unannotatedStaging() {
  const staged = structuredClone(tile);
  for (const id of PATHS) {
    const original = path(id, staged);
    for (const field of ['indoorLevel', 'floorHeight', 'deckGeometry']) delete original[field];
  }
  return staged;
}

test('pinned bridge endpoints attach to named level-one corridors and existing building facades', () => {
  const bridge = ways.get(BRIDGE);
  const [westNode, eastNode] = bridge.nodes;
  assert.deepEqual([westNode, eastNode], [4559764872, 4559780649]);
  assert.deepEqual(bridge.tags, { bridge: 'yes', highway: 'corridor', indoor: 'yes', layer: '1', level: '1' });
  for (const [wayId, buildingId, node, name] of [
    [PATHS[0], WEST, westNode, 'One Raffles Link'],
    [PATHS[2], EAST, eastNode, 'Marina Square'],
  ]) {
    const source = ways.get(wayId), building = ways.get(buildingId);
    assert.equal(building.tags.name, name);
    assert.ok(building.nodes.includes(node));
    assert.ok(source.nodes.includes(node));
    assert.deepEqual([source.tags.highway, source.tags.indoor, source.tags.level], ['corridor', 'yes', '1']);
  }

  const candidate = unannotatedStaging();
  assert.equal(applyRafflesLinkWalkway(candidate, ways), true);
  assert.deepEqual(candidate, tile, 'generated walkway metadata matches the tracked shard');
  const [a, b] = path(BRIDGE).geometry;
  assert.deepEqual(a, path(PATHS[0]).geometry.at(-1));
  assert.deepEqual(b, path(PATHS[2]).geometry[0]);
  near(length(a, b), 17.409);
  const [start, end] = path(BRIDGE).deckGeometry;
  near(length(a, start), 1.6);
  near(length(end, b), 1.6);
  for (const id of [PATHS[0], PATHS[2]]) {
    assert.equal(path(id).indoorLevel, 1);
    assert.equal(path(id).floorHeight, undefined, 'mapping the endpoint does not establish a walkable floor in the adjacent building');
  }
});

test('missing facade, mixed floor tags or invalid opening leave the entire staging tile unchanged', () => {
  for (const kind of ['west facade', 'east corridor level', 'opening', 'height']) {
    const candidate = unannotatedStaging(), sources = new Map(ways);
    if (kind === 'west facade') candidate.buildings = candidate.buildings.filter(item => item.id !== WEST);
    if (kind === 'east corridor level') {
      const original = sources.get(PATHS[2]);
      sources.set(original.id, { ...original, tags: { ...original.tags, level: '2' } });
    }
    if (kind === 'opening') shell(candidate).passages[0].geometry[0] = [NaN, 43.8];
    if (kind === 'height') shell(candidate).height = NaN;
    const before = structuredClone(candidate);
    assert.equal(applyRafflesLinkWalkway(candidate, sources), false, kind);
    assert.deepEqual(candidate, before, kind);
  }
});

test('only the modeled indoor deck renders and none of its three source corridors becomes street routing', t => {
  const selected = PATHS.map(id => path(id));
  assert.deepEqual(pedestrianPaths([{ ...tile, pedestrian: selected }]), []);
  assert.deepEqual(pedestrianPaths([{ ...tile, pedestrian: selected.map(p => ({ ...p, class: 'footway' })) }]), []);
  const built = buildTile({ x: tile.x, z: tile.z, pedestrian: selected });
  t.after(() => built.ground.dispose());
  const position = built.ground.getAttribute('position');
  assert.equal(position.count, 6);
  for (let i = 0; i < position.count; i++) near(position.getY(i), FLOOR);
  assert.equal(built.walkwaySolids.length, 2);
});

async function loadWorld(t) {
  const physics = await createPhysicsWorld();
  t.after(() => physics.dispose());
  physics.addGround({ halfWidth: 60000, halfDepth: 60000 });
  const facades = new Map();
  for (const part of [tile, ...neighbors]) {
    const built = buildTile(part);
    t.after(() => [built.ground, built.buildings, built.towers].forEach(mesh => mesh?.dispose()));
    for (const solid of built.solids) {
      const collider = physics.addStaticTrimesh(solid.mesh ?? buildingMesh(solid.ring, solid.height, solid.base));
      if (!facades.has(solid.id)) facades.set(solid.id, []);
      facades.get(solid.id).push(collider.handle);
    }
    for (const panel of built.walkwaySolids) physics.addStaticConvexHull({ vertices: panel.position, friction: 1 });
    for (const deck of built.bridgeSolids) physics.addStaticTrimesh(deck);
  }
  physics.step(FIXED_DT);
  return { physics, facades };
}

function walkDeck(physics, a, b) {
  const span = length(a, b), dx = (b[0] - a[0]) / span, dz = (b[1] - a[1]) / span;
  const [x, z] = between(a, b, .45 / span);
  const pedestrian = physics.addPedestrian({ position: { x, y: FLOOR + 1, z } });
  const steps = Math.ceil(span / 1.45 / FIXED_DT) + 180;
  let reached = 0, grounded = 0, count = 0;
  try {
    pedestrian.setVelocity({ x: 1.45 * dx, z: 1.45 * dz });
    for (; count < steps && reached < span - .45; count++) {
      physics.step(FIXED_DT);
      const { position, grounded: supported } = pedestrian.getState();
      const [px, pz] = [position.x - a[0], position.z - a[1]];
      reached = px * dx + pz * dz;
      assert.ok(Math.abs(px * dz - pz * dx) < .1, 'the capsule remains on the bridge centerline');
      const feet = position.y - PEDESTRIAN_TUNING.height / 2;
      assert.ok(feet >= FLOOR - .012, 'the capsule stays above the modeled support plane');
      grounded += Number(supported);
    }
    assert.ok(reached >= span - .45 && grounded / count > .97, 'the capsule walks across the supported deck');
  } finally {
    physics.removePedestrian(pedestrian);
  }
}

test('Rapier supports the full modeled deck, preserves 4.5 m clearance and keeps both approach walls solid', async t => {
  const { physics, facades } = await loadWorld(t);
  const deck = path(BRIDGE).deckGeometry;
  const [start, end] = deck.map(world);
  for (let i = 0; i <= 20; i++) {
    const [x, z] = between(start, end, .02 + .96 * i / 20);
    near(physics.supportHeight({ x, y: 5.5, z }), FLOOR);
  }
  const [, crossing] = splitByRing(...deck, shell(tile).passages[0].geometry.slice(0, -1));
  for (const ratio of [.1, .5, .9]) {
    const [x, z] = world(between(...deck, crossing.start + (crossing.end - crossing.start) * ratio));
    near(physics.supportHeight({ x, y: 1, z }), 0);
    near(physics.overheadHeight({ x, y: 1, z }), 4.5);
  }
  for (const [a, b, id] of [[start, end, WEST], [end, start, EAST]]) {
    const span = length(a, b);
    const ray = new RAPIER.Ray({ x: a[0], y: FLOOR + .8, z: a[1] },
      { x: (a[0] - b[0]) / span, y: 0, z: (a[1] - b[1]) / span });
    const hit = physics.world.castRay(ray, 2, true, RAPIER.QueryFilterFlags.ONLY_FIXED,
      undefined, undefined, undefined, collider => facades.get(id).includes(collider.handle));
    assert.ok(hit && hit.timeOfImpact > 1 && hit.timeOfImpact < 2, `the existing building ${id} blocks this endpoint`);
  }
  walkDeck(physics, start, end);
  walkDeck(physics, end, start);
});
