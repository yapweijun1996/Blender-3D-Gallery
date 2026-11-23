import assert from 'node:assert/strict';
import test from 'node:test';
import RAPIER from '@dimforge/rapier3d-compat';
import profile from '../scripts/world/fort-canning-integration.json' with { type: 'json' };
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { createFortCanningActivation } from '../src/world/tunnel-integration/activation.js';
import { createFortCanningMergeGeometry } from '../src/world/tunnel-integration/merge-geometry.js';
import { createWorldFortCanning } from '../src/world/tunnel-integration/session.js';

const geometry = createFortCanningMergeGeometry(profile);
const { minX, maxX, minZ, maxZ } = geometry.bounds;
const safetyBounds = { minX: minX - 20, maxX: maxX + 20, minZ: minZ - 20, maxZ: maxZ + 20 };
const requiredTileKeys = ['-7_-7', '-8_-7'];
const overlay = { version: 1 };
const route = { id: 'fort-canning' };
const centerZ = (minZ + maxZ) / 2;
const outside = { position: { x: minX - 50, z: centerZ }, radius: 2, speed: 0 };
const inside = { position: { x: (minX + maxX) / 2, z: centerZ }, radius: 2, speed: 0 };
const safeFrame = { player: outside, dt: FIXED_DT };

function prepared(visuals) {
  return { geometry, overlay, route, visuals, tiles: new Map(requiredTileKeys.map(key => [key, { key }])) };
}

function fallbackPhysics() {
  const installed = new Set();
  let meshesBeforeFailure = Infinity;
  function add(kind) {
    const collider = { kind };
    installed.add(collider);
    return collider;
  }
  function mesh() {
    if (meshesBeforeFailure-- === 0) throw new Error('tunnel collider install failed');
    return add('mesh');
  }
  return {
    installed,
    failMeshAfter: count => { meshesBeforeFailure = count; },
    addGround: () => add('ground'),
    addStaticTrimesh: mesh,
    addStaticConvexHull: mesh,
    removeStatic(collider) { assert.ok(installed.delete(collider), 'release each owned collider once'); },
  };
}

function visualPatch(events, publishError) {
  return {
    published: false,
    ordinaryVisible: true,
    publish() {
      events.push('publish');
      this.published = true;
      this.ordinaryVisible = false;
      if (publishError) throw publishError;
    },
    dispose() {
      events.push('dispose');
      this.published = false;
      this.ordinaryVisible = true;
    },
  };
}

function downwardHeight(physics, { x, z }) {
  const hit = physics.world.castRay(new RAPIER.Ray({ x, y: 3, z }, { x: 0, y: -1, z: 0 }), 12, true);
  return hit ? 3 - hit.timeOfImpact : null;
}

test('publishes the pinned bundle after a real Rapier step and removes the old plane over the cut', async () => {
  const physics = await createPhysicsWorld();
  const events = [];
  const controller = new AbortController();
  const source = prepared(visualPatch(events));
  const activation = createFortCanningActivation({ physics, signal: controller.signal, safetyBounds, requiredTileKeys, prepare: () => source });
  const ramp = geometry.alignment.link.find(point => point.s > 45);
  try {
    physics.step(FIXED_DT);
    assert.equal(downwardHeight(physics, ramp), 0);
    assert.equal(physics.world.colliders.len(), 1);
    assert.equal(await activation.preload(), true);
    assert.equal(activation.status, 'ready');
    assert.equal(activation.available, null);
    source.tiles.delete('-8_-7');
    activation.beginFrame(safeFrame);
    assert.equal(activation.status, 'staged');
    assert.equal(activation.afterPhysics(physics.step(0)), null);
    assert.equal(downwardHeight(physics, ramp), 0, 'old support remains while the candidate is unindexed');
    assert.deepEqual(events, []);

    activation.beginFrame(safeFrame);
    const active = activation.afterPhysics(physics.step(FIXED_DT));
    assert.equal(activation.status, 'active');
    assert.equal(active.geometry, geometry);
    assert.equal(active.overlay, overlay);
    assert.equal(active.route, route);
    assert.deepEqual([...active.tiles.keys()], requiredTileKeys, 'prepared tile ownership is pinned');
    assert.deepEqual(events, ['publish']);
    assert.ok(Math.abs(downwardHeight(physics, ramp) - ramp.y) < 0.002, 'the old plane no longer seals the tunnel ramp');
    assert.equal(downwardHeight(physics, outside.position), 0, 'indexed exterior support is already available');
    assert.equal(physics.world.colliders.len(), 4 + geometry.surfaces.length);

    activation.beginFrame({ player: inside });
    assert.equal(activation.afterPhysics(physics.step(0)), active, 'the active bundle survives proximity and zero-step frames');
    assert.equal(await activation.retry(safeFrame), false);
  } finally {
    controller.abort();
    activation.dispose();
    assert.equal(activation.status, 'disposed');
    assert.equal(activation.available, null);
    assert.deepEqual(events, ['publish', 'dispose']);
    assert.equal(physics.world.colliders.len(), 0);
    physics.dispose();
  }
});

test('parked or moving occupants block staging and can cancel a stage before its first substep', async () => {
  const physics = fallbackPhysics();
  const events = [];
  const activation = createFortCanningActivation({ physics, safetyBounds, requiredTileKeys, prepare: () => prepared(visualPatch(events)) });
  const original = [...physics.installed];
  await activation.preload();
  const nearEdge = { position: { x: minX - 3, z: centerZ }, radius: 2, speed: 15 };
  const overhanging = { ...nearEdge, position: { x: minX - 1, z: centerZ }, speed: 0 };
  for (const frame of [{ player: inside }, { player: overhanging }, { ...safeFrame, occupants: [inside] },
    { ...safeFrame, occupants: [nearEdge] }]) {
    activation.beginFrame(frame);
    assert.equal(activation.status, 'ready');
    assert.deepEqual([...physics.installed], original);
  }

  activation.beginFrame(safeFrame);
  assert.equal(activation.status, 'staged');
  assert.equal(activation.afterPhysics({ substeps: 0 }), null);
  activation.beginFrame({ ...safeFrame, occupants: [inside] });
  assert.equal(activation.status, 'ready');
  assert.equal(activation.afterPhysics({ substeps: 1 }), null, 'the previous stage no longer owns this substep');
  assert.deepEqual([...physics.installed], original);
  assert.deepEqual(events, []);

  activation.beginFrame(safeFrame);
  assert.equal(activation.afterPhysics({ substeps: 1 }).route, route);
  activation.dispose();
  assert.equal(physics.installed.size, 0);
});

test('incomplete dependencies fail closed and only a safe explicit retry can prepare them again', async () => {
  const physics = fallbackPhysics();
  const events = [];
  let attempts = 0;
  const activation = createFortCanningActivation({ physics, safetyBounds, requiredTileKeys, prepare() {
    const bundle = prepared(visualPatch(events));
    if (++attempts === 1) bundle.tiles.delete('-8_-7');
    return bundle;
  } });
  const ordinary = [...physics.installed];
  assert.equal(await activation.preload(), false);
  assert.match(activation.failure.message, /overlay dependencies/);
  assert.deepEqual(events, ['dispose']);
  assert.deepEqual([...physics.installed], ordinary);
  assert.equal(await activation.retry({ player: inside }), false);
  assert.equal(await activation.preload(), false, 'routine preloading does not spend the retry');
  assert.equal(attempts, 1);
  assert.equal(await activation.retry(safeFrame), true);
  assert.equal(attempts, 2);
  assert.equal(activation.failure, null);
  assert.equal(activation.status, 'ready');
  activation.dispose();
  assert.deepEqual(events, ['dispose', 'dispose']);
});

test('bad geometry and failed mesh installation leave the ordinary plane and dispose the never-published patch', async () => {
  const physics = fallbackPhysics();
  const events = [];
  let attempts = 0;
  const activation = createFortCanningActivation({ physics, safetyBounds, requiredTileKeys, prepare() {
    const bundle = prepared(visualPatch(events));
    if (++attempts === 1) bundle.geometry = { ...geometry, surfaces: geometry.surfaces.filter(surface => surface.id !== 'terrain') };
    return bundle;
  } });
  const ordinary = [...physics.installed];
  assert.equal(await activation.preload(), false);
  assert.match(activation.failure.message, /geometry is incomplete/);
  assert.equal(await activation.retry(safeFrame), true);
  physics.failMeshAfter(1);
  activation.beginFrame(safeFrame);
  assert.equal(activation.status, 'failed');
  assert.match(activation.failure.message, /collider install failed/);
  assert.deepEqual([...physics.installed], ordinary);
  assert.deepEqual(events, ['dispose', 'dispose']);
  assert.equal(activation.available, null);
  assert.equal(await activation.retry(safeFrame), false, 'a second failure exhausts the retry');
  activation.dispose();
  assert.equal(physics.installed.size, 0);
});

test('a partially published visual patch rolls back before exposing the route', async () => {
  const physics = fallbackPhysics();
  const events = [];
  const visuals = visualPatch(events, new Error('visual publish failed'));
  const activation = createFortCanningActivation({ physics, safetyBounds, requiredTileKeys, prepare: () => prepared(visuals) });
  const ordinary = [...physics.installed];
  await activation.preload();
  activation.beginFrame(safeFrame);
  assert.equal(activation.afterPhysics({ substeps: 1 }), null);
  assert.equal(activation.status, 'failed');
  assert.match(activation.failure.message, /visual publish failed/);
  assert.deepEqual(events, ['publish', 'dispose']);
  assert.equal(visuals.published, false);
  assert.equal(visuals.ordinaryVisible, true, 'the normal render remains available after partial publication');
  assert.deepEqual([...physics.installed], ordinary);
  activation.dispose();
});

test('abort releases in-flight and staged resources exactly once', async () => {
  const physics = fallbackPhysics();
  const events = [];
  const controller = new AbortController();
  let resolveLoad, prepSignal;
  const activation = createFortCanningActivation({ physics, signal: controller.signal, safetyBounds, requiredTileKeys, prepare(signal) {
    prepSignal = signal;
    return new Promise(resolve => { resolveLoad = resolve; });
  } });
  const loading = activation.preload();
  assert.equal(activation.preload(), loading, 'concurrent preloads share the same attempt');
  await Promise.resolve();
  controller.abort();
  assert.equal(prepSignal.aborted, true);
  assert.equal(activation.status, 'disposed');
  assert.equal(physics.installed.size, 0);
  resolveLoad(prepared(visualPatch(events)));
  assert.equal(await loading, false);
  assert.deepEqual(events, ['dispose']);
  assert.equal(activation.afterPhysics({ substeps: 1 }), null);
  activation.dispose();

  const stagingController = new AbortController();
  const staged = createFortCanningActivation({ physics, signal: stagingController.signal, safetyBounds, requiredTileKeys,
    prepare: () => prepared(visualPatch(events)) });
  await staged.preload();
  staged.beginFrame(safeFrame);
  assert.equal(staged.status, 'staged');
  stagingController.abort();
  assert.equal(staged.status, 'disposed');
  assert.equal(staged.afterPhysics({ substeps: 1 }), null);
  assert.equal(physics.installed.size, 0);
  assert.deepEqual(events, ['dispose', 'dispose']);
});

test('a failed tile can retry after driving clear of the apron while still inside the preload area', async () => {
  const physics = await createPhysicsWorld();
  const requested = [];
  const { activation, beforePhysics } = createWorldFortCanning({
    physics, signal: new AbortController().signal,
    fetchTile(key) { requested.push(key); throw new Error('unavailable'); },
  });
  const approach = { position: { x: -1080, z: -1450 }, speed: 0 };
  const onApron = { position: { x: -1500, z: -1450 }, speed: 0 };
  try {
    beforePhysics(approach, FIXED_DT, () => []);
    await activation.preload();
    assert.equal(activation.status, 'failed');
    const first = requested.slice();
    assert.equal(new Set(first).size, 6);

    beforePhysics(approach, FIXED_DT, () => []);
    beforePhysics(onApron, FIXED_DT, () => []);
    beforePhysics(approach, FIXED_DT, () => [inside]);
    assert.deepEqual(requested, first);
    beforePhysics(approach, FIXED_DT, () => []);
    await activation.preload();
    assert.deepEqual(requested, [...first, ...first]);
    assert.equal(activation.canRetry, false);
  } finally {
    activation.dispose();
    physics.dispose();
  }
});
