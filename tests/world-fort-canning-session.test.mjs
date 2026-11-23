import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';

import { Group, MeshLambertMaterial } from 'three';
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { createWorldFortCanning } from '../src/world/tunnel-integration/session.js';

const firstKey = '-5_-6', secondKey = '-6_-6';
const player = { position: { x: -1050, y: 1, z: -1100 }, speed: 0 };

async function session(t, { failToPublish, failToRetire } = {}) {
  const physics = await createPhysicsWorld();
  const scene = new Group();
  const flatGround = { visible: true, material: new MeshLambertMaterial() };
  const make = (key, old = false) => ({ key, old, group: new Group(), colliders: false, disposals: 0 });
  const prior = new Map([firstKey, secondKey, '0_0'].map(key => [key, make(key, true)]));
  const tiles = new Map(prior), prepared = new Map(), retired = [];
  for (const entry of prior.values()) scene.add(entry.group);
  prior.get(secondKey).group.visible = false;

  const { activation, beforePhysics } = createWorldFortCanning({
    physics, scene, flatGround, tiles,
    async fetchTile(key) {
      return JSON.parse(await readFile(new URL('../models/world/tiles/' + key + '.json', import.meta.url)));
    },
    makeEntry(data) {
      const key = data.x + '_' + data.z;
      const entry = make(key);
      prepared.set(key, entry);
      if (key === failToPublish) entry.group.addEventListener('added', () => {
        assert.equal(tiles.get(firstKey), prepared.get(firstKey), 'the earlier tile has already been swapped');
        assert.equal(prior.get(firstKey).group.visible, false);
        assert.equal(prior.get(firstKey).disposals, 0);
        throw new Error('scene attach failed');
      });
      return entry;
    },
    setColliders(entry, wanted) { entry.colliders = wanted; },
    disposeEntry(entry) {
      entry.disposals++;
      entry.colliders = false;
      entry.group.removeFromParent();
      if (entry.old) retired.push({ key: entry.key, phase: activation.status, hasBundle: Boolean(activation.available) });
      if (entry.old && entry.key === failToRetire) throw new Error('old GPU resource disposal failed');
    },
  });
  t.after(() => {
    try { activation.dispose(); }
    finally { physics.dispose(); flatGround.material.dispose(); }
  });

  assert.equal(await activation.preload(), true);
  beforePhysics(player, FIXED_DT, () => []);
  assert.equal(activation.status, 'staged');
  assert.deepEqual(tiles, prior);
  assert.equal(prior.get(firstKey).disposals, 0);
  return { physics, activation, scene, flatGround, tiles, prior, prepared, retired };
}

test('the committed route retires prior tiles once, and teardown releases the replacements', async t => {
  const { physics, activation, scene, flatGround, tiles, prior, prepared, retired } = await session(t);
  assert.ok(activation.afterPhysics(physics.step(FIXED_DT)));
  assert.equal(activation.status, 'active');
  assert.equal(flatGround.visible, false);
  for (const [key, entry] of prepared) {
    assert.equal(tiles.get(key), entry);
    assert.equal(entry.group.parent, scene);
    assert.equal(entry.colliders, true);
  }
  assert.deepEqual(retired, [firstKey, secondKey].map(key => ({ key, phase: 'active', hasBundle: true })));
  for (const key of [firstKey, secondKey]) {
    assert.equal(prior.get(key).group.parent, null);
    assert.equal(prior.get(key).disposals, 1);
  }

  activation.dispose();
  activation.dispose();
  assert.deepEqual([...tiles.keys()], ['0_0']);
  assert.deepEqual(scene.children, [prior.get('0_0').group]);
  assert.equal(flatGround.visible, true);
  assert.ok([...prepared.values()].every(entry => entry.disposals === 1 && !entry.colliders));
  assert.equal(retired.length, 2);
});

test('a later scene attach failure restores old tile entries, visibility and the ordinary ground', async t => {
  const check = await session(t, { failToPublish: secondKey });
  const { physics, activation, scene, flatGround, tiles, prior, prepared, retired } = check;
  assert.equal(activation.afterPhysics(physics.step(FIXED_DT)), null);
  assert.equal(activation.status, 'failed');
  assert.match(activation.failure.message, /scene attach failed/);
  assert.deepEqual(tiles, prior);
  assert.deepEqual(scene.children, [...prior.values()].map(entry => entry.group));
  assert.equal(prior.get(firstKey).group.visible, true);
  assert.equal(prior.get(secondKey).group.visible, false);
  assert.equal(flatGround.visible, true);
  assert.equal(physics.supportHeight({ x: -1200, y: 2, z: -1300 }), 0);
  assert.ok([...prepared.values()].every(entry => entry.disposals === 1 && !entry.colliders));
  assert.deepEqual(retired, []);
  activation.dispose();
  assert.ok([...prior.values()].every(entry => entry.disposals === 0));
});

test('a retirement error leaves the already-committed route and finishes the other old entries', async t => {
  const { physics, activation, flatGround, tiles, prior, prepared, retired } = await session(t, { failToRetire: firstKey });
  assert.ok(activation.afterPhysics(physics.step(FIXED_DT)));
  assert.equal(activation.status, 'active');
  assert.equal(activation.failure.errors[0].message, 'old GPU resource disposal failed');
  assert.equal(flatGround.visible, false);
  assert.equal(tiles.get(firstKey), prepared.get(firstKey));
  assert.equal(tiles.get(secondKey), prepared.get(secondKey));
  assert.deepEqual(retired.map(({ key }) => key), [firstKey, secondKey]);
  assert.equal(prior.get(firstKey).disposals, 1);
  assert.equal(prior.get(secondKey).disposals, 1);
});
