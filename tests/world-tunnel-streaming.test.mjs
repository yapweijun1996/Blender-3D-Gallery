import assert from 'node:assert/strict';
import test from 'node:test';
import RAPIER from '@dimforge/rapier3d-compat';
import prototype from '../scripts/world/fort-canning-tunnel.json' with { type: 'json' };
import { createPhysicsWorld, FIXED_DT } from '../src/world/physics/world.js';
import { createStreamedTunnelGround } from '../src/world/tunnel-integration/colliders.js';
import { groundSurface, splitGroundBounds, surfaceBounds } from '../src/world/tunnel-integration/ground.js';
import { createTunnelGeometry } from '../src/world/tunnel-prototype/geometry.js';

const { sections, surfaces, clearance } = createTunnelGeometry(prototype);
const bounds = surfaceBounds(surfaces.find(surface => surface.id === 'terrain'));
const down = { x: 0, y: -1, z: 0 };
const up = { x: 0, y: 1, z: 0 };

function hitAt(physics, position, direction = down) {
  return physics.world.castRay(new RAPIER.Ray(position, direction), 16, true);
}

function heightAt(physics, x, z, y = 3) {
  const hit = hitAt(physics, { x, y, z });
  assert.ok(hit, `missing supporting surface at (${x}, ${y}, ${z})`);
  return y - hit.timeOfImpact;
}

function assertHeight(physics, { x, z }, expected, from = 3) {
  assert.ok(Math.abs(heightAt(physics, x, z, from) - expected) < 0.002, `wrong height at (${x}, ${z})`);
}

test('the visual rectangle cut retains the original plane footprint and upward faces', () => {
  const outer = { minX: -3000, maxX: 3000, minZ: -3000, maxZ: 3000 };
  const panels = splitGroundBounds(outer, bounds);
  const area = ({ minX, maxX, minZ, maxZ }) => (maxX - minX) * (maxZ - minZ);
  assert.equal(panels.length, 4);
  assert.ok(Math.abs(panels.reduce((sum, panel) => sum + area(panel), 0) - (area(outer) - area(bounds))) < 1e-6);
  for (const panel of panels) {
    assert.ok(panel.maxX <= bounds.minX || panel.minX >= bounds.maxX ||
      panel.maxZ <= bounds.minZ || panel.minZ >= bounds.maxZ, 'ordinary plane stays outside the patch');
  }

  const visualGround = groundSurface(panels, -0.3);
  assert.deepEqual(surfaceBounds(visualGround), outer);
  let coverage = 0;
  for (let index = 0; index < visualGround.indices.length; index += 3) {
    const [a, b, c] = visualGround.indices.subarray(index, index + 3).map(vertex => vertex * 3);
    const [x, y, z] = visualGround.position.subarray(a, a + 3);
    const [bx, by, bz] = visualGround.position.subarray(b, b + 3);
    const [cx, cy, cz] = visualGround.position.subarray(c, c + 3);
    assert.equal(y, Math.fround(-0.3));
    assert.equal(by, y);
    assert.equal(cy, y);
    const upward = (bz - z) * (cx - x) - (bx - x) * (cz - z);
    assert.ok(upward > 0, 'ground faces outward');
    coverage += upward / 2;
  }
  assert.ok(Math.abs(coverage - (area(outer) - area(bounds))) < 1e-6);
  assert.throws(() => splitGroundBounds(outer, { ...bounds, minX: outer.minX - 1 }), /inside the ground/);
});

test('a cut may share ground borders but cannot produce degenerate or nonfinite panel bounds', () => {
  const outer = { minX: 0, maxX: 12, minZ: 0, maxZ: 16 };
  assert.deepEqual(splitGroundBounds(outer, { minX: 0, maxX: 4, minZ: 0, maxZ: 5 }), [
    { minX: 4, maxX: 12, minZ: 0, maxZ: 16 },
    { minX: 0, maxX: 4, minZ: 5, maxZ: 16 },
  ]);
  assert.deepEqual(splitGroundBounds(outer, outer), []);
  assert.throws(() => splitGroundBounds(outer, { ...outer, maxX: 0 }), /nonempty rectangle/);
  assert.throws(() => splitGroundBounds({ ...outer, minZ: -Infinity }, outer), /inside the ground/);
});

test('streaming keeps outside support while swapping the tunnel patch without residual colliders', async () => {
  const physics = await createPhysicsWorld();
  try {
    const sentinel = physics.addGround({ x: 100, z: 100, height: 1, halfWidth: 1, halfDepth: 1 });
    const tunnelGround = createStreamedTunnelGround(physics, { bounds, surfaces });
    const ramp = sections.find(section => section.s >= 46);
    const bore = sections.find(section => section.s >= 170);
    const surrounding = [
      { x: -59990, z: -59990 }, { x: 59990, z: 59990 }, { x: 500, z: 500 },
      { x: bounds.minX - 10, z: ramp.z }, { x: bounds.maxX + 10, z: ramp.z },
      { x: ramp.x, z: bounds.minZ - 10 }, { x: ramp.x, z: bounds.maxZ + 10 },
    ];
    const border = [
      { x: bounds.minX, z: ramp.z }, { x: bounds.maxX, z: ramp.z },
      { x: ramp.x, z: bounds.minZ }, { x: ramp.x, z: bounds.maxZ },
      { x: bounds.minX, z: bounds.minZ }, { x: bounds.maxX, z: bounds.maxZ },
    ];

    physics.step(FIXED_DT);
    assert.equal(tunnelGround.active, false);
    assert.equal(physics.world.colliders.len(), 6);
    assertHeight(physics, ramp, 0);
    for (const p of surrounding) assertHeight(physics, p, 0);

    for (let visit = 0; visit < 2; visit++) {
      tunnelGround.setActive(true);
      tunnelGround.setActive(true);
      for (const p of surrounding) assertHeight(physics, p, 0);
      physics.step(FIXED_DT);
      assert.equal(tunnelGround.active, true);
      assert.equal(physics.world.colliders.len(), 5 + surfaces.length);
      for (const p of [...surrounding, ...border]) assertHeight(physics, p, 0);
      assertHeight(physics, ramp, ramp.y);
      assertHeight(physics, bore, 0);
      assertHeight(physics, bore, bore.y, bore.y + 1);
      const roof = hitAt(physics, { x: bore.x, y: bore.y + 1, z: bore.z }, up);
      assert.ok(roof && Math.abs(roof.timeOfImpact - (clearance - 1)) < 0.002);

      tunnelGround.setActive(false);
      tunnelGround.setActive(false);
      for (const p of surrounding) assertHeight(physics, p, 0);
      physics.step(FIXED_DT);
      assert.equal(tunnelGround.active, false);
      assert.equal(physics.world.colliders.len(), 6);
      assertHeight(physics, ramp, 0);
      assert.equal(hitAt(physics, { x: bore.x, y: bore.y + 1, z: bore.z }), null, 'unloaded tunnel floor is gone');
    }

    tunnelGround.dispose();
    tunnelGround.dispose();
    tunnelGround.setActive(true);
    assert.equal(physics.world.colliders.len(), 1);
    assert.equal(physics.world.getCollider(sentinel.handle), sentinel);
  } finally {
    physics.dispose();
  }
});

test('a failed patch swap leaves the previous surface collision intact', () => {
  const installed = new Set();
  const add = () => { const collider = {}; installed.add(collider); return collider; };
  let meshAttempts = 0, failGrid = false, failMesh = true;
  const physics = {
    addGround() {
      if (failGrid) throw new Error('base ground install failed');
      return add();
    },
    addStaticTrimesh() {
      if (++meshAttempts === 2 && failMesh) throw new Error('tunnel mesh install failed');
      return add();
    },
    removeStatic(collider) { assert.equal(installed.delete(collider), true); },
  };
  const tunnel = createStreamedTunnelGround(physics, { bounds, surfaces });
  const base = [...installed];
  assert.throws(() => tunnel.setActive(true), /tunnel mesh install failed/);
  assert.deepEqual([...installed], base);
  assert.equal(tunnel.active, false);

  failMesh = false;
  tunnel.setActive(true);
  const opened = [...installed];
  assert.equal(opened.length, 4 + surfaces.length);
  failGrid = true;
  assert.throws(() => tunnel.setActive(false), /base ground install failed/);
  assert.deepEqual([...installed], opened);
  assert.equal(tunnel.active, true);

  tunnel.dispose();
  assert.equal(installed.size, 0);
});

test('failure to initialize the fallback removes the preinstalled exterior panels', () => {
  const installed = new Set();
  const physics = {
    addGround() {
      if (installed.size === 4) throw new Error('fallback ground install failed');
      const collider = {};
      installed.add(collider);
      return collider;
    },
    removeStatic(collider) { assert.equal(installed.delete(collider), true); },
  };
  assert.throws(() => createStreamedTunnelGround(physics, { bounds, surfaces }), /fallback ground install failed/);
  assert.equal(installed.size, 0);
});
