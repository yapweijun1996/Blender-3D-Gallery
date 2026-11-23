import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Raycaster, Vector3 } from 'three';
import { BODY } from '../docs/verification/mall-corridor/collision.js';
import { assembleFloorTransition, floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { shellAssetPaths } from '../mall-modules-preview/shell-layout.js';
import { assembleWalledFloor, assembleWallRun, wallRunPath } from '../mall-modules-preview/wall-run.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

async function load(path) {
  return (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const sources = {};
for (const [id, path] of Object.entries(floorTransitionPaths)) sources[id] = await load(path);
const [wallSource, legacyWall, legacyCeiling] = await Promise.all(
  [wallRunPath, shellAssetPaths.wall, shellAssetPaths.ceiling].map(load));
const wallZ = -1.925;
const front = new Vector3(0, 0, -1), back = new Vector3(0, 0, 1);
const up = new Vector3(0, 1, 0), down = new Vector3(0, -1, 0);

function near(actual, expected, label) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < 1e-6, `${label}: ${actual}, expected ${expected}`);
}
function surface(root, x, y, z, direction) {
  const ray = new Raycaster(new Vector3(x, y, z), direction);
  const hit = ray.intersectObject(root, true)[0];
  assert.ok(hit, `missing surface in ${root.name} from (${x}, ${y}, ${z})`);
  return hit;
}
function run(source = wallSource) {
  const group = assembleWallRun(source);
  group.updateMatrixWorld(true);
  return group;
}

test('three native 2 m walls mate at the two connectors and stand on the real mixed-grid floor', t => {
  const walls = run().children;
  const floor = assembleFloorTransition(sources);
  floor.updateMatrixWorld(true);
  assert.equal(walls.length, 3);
  let floorSamples = 0;
  for (const [i, part] of walls.entries()) {
    const x = 2 * i - 2;
    const bounds = new Box3().setFromObject(part, true);
    assert.deepEqual(part.position.toArray(), [x, 0, wallZ]);
    assert.deepEqual(part.scale.toArray(), [1, 1, 1]);
    near(bounds.min.x, x - 1, 'left mating face');
    near(bounds.max.x, x + 1, 'right mating face');
    near(bounds.min.z, -2, 'wall back at floor edge');
    near(bounds.max.z, wallZ + .075, 'front extremity');
    near(bounds.min.y, 0, 'base');
    near(bounds.max.y, 2.8, 'top');
    for (const [side, sign] of [['Left', -1], ['Right', 1]]) {
      const connector = part.getObjectByName('CONNECTOR_' + side + '_LOD0');
      assert.ok(connector, side + ' connector');
      const p = connector.getWorldPosition(new Vector3());
      near(p.x, x + sign, 'seam X'); near(p.y, 0, 'connector Y'); near(p.z, wallZ, 'centreline');
    }
    for (let j = 0; j <= 40; j++) {
      const along = x - .99999 + (1.99998 * j / 40);
      // The plinth toe projects further above the base. Probe its actual bearing footprint.
      for (const across of [-.07499, -.04, 0, .05, .0689]) {
        const z = wallZ + across;
        const top = surface(floor, along, .2, z, down);
        const bottom = surface(part, along, -.2, z, up);
        near(top.point.y, 0, '2 m floor top');
        near(bottom.point.y - top.point.y, 0, 'wall base to floor contact');
        floorSamples++;
      }
    }
  }
  t.diagnostic(JSON.stringify({ matedConnectors: 2, floorToBasePairs: floorSamples }));
});

test('backing, limestone, shadow joint and metal trims meet their matching profiles at both seams', () => {
  const walls = run().children;
  for (const [i, seam] of [-1, 1].entries()) {
    for (const [part, sign] of [[walls[i], -1], [walls[i + 1], 1]]) {
      const inward = (offset, y) => surface(part, seam + sign * offset, y, -1, front);
      for (const y of [.5, 2]) {
        // Each panel stops 2 mm short of its module end. The mortar continues all the way.
        const joint = inward(.0019, y), stoneEdge = inward(.0021, y), stone = inward(.006, y);
        assert.match(joint.object.material.name, /mortar/i);
        assert.match(stoneEdge.object.material.name, /limestone/i);
        assert.match(stone.object.material.name, /limestone/i);
        near(joint.point.z, wallZ + .062, 'front of mortar');
        near(stone.point.z - joint.point.z, .01, '10 mm recessed joint');
        const rear = surface(part, seam + sign * .006, y, -2.4, back);
        assert.match(rear.object.material.name, /mortar/i);
        near(rear.point.z, -2, 'plain rear face');
      }
      for (const y of [.06, 2.78]) {
        const trim = inward(.00001, y);
        assert.match(trim.object.material.name, /bronze/i);
        near(trim.point.z, wallZ + .075, 'continuous trim front');
      }
      near(inward(.006, 1.43).point.z, wallZ + .062, 'horizontal panel joint');
    }
  }
});

test('a shared top edge is supported at the exact queried point and real holes and drops remain detectable', async t => {
  const floor = assembleFloorTransition(sources);
  floor.updateMatrixWorld(true);
  const scene = await measureWallContact(floor);
  t.after(() => scene.dispose());
  const z = -1.275;
  const samples = [-1e-6, -1e-8, -8.881784197001252e-16, 0, 1e-8, 1e-6].map(x => {
    const direct = surface(floor, x, .1, z, down);
    const measured = scene.surface(x, z);
    near(direct.point.y, 0, 'GLB top at shared edge');
    near(measured, direct.point.y, 'physical support at original coordinate');
    return { x, rawRayY: scene.rawSurface(x, z), supportedY: measured };
  });
  const misses = samples.filter(sample => sample.rawRayY < -.09);
  near(samples[2].rawRayY, -.1, 'locked Rapier point ray hits the underside at the known shared edge');
  const dropped = floor.children.find(p => p.userData.moduleId === 'floor2m' && p.position.x === 0);
  dropped.position.y -= .1;
  const lower = await measureWallContact(floor);
  t.after(() => lower.dispose());
  near(lower.surface(0, z), -.1, 'a real 100 mm drop survives the shared-edge check');
  assert.throws(() => checkFloor(lower, { x: 0, z }), /unsupported footprint/);
  floor.remove(dropped);
  const open = await measureWallContact(floor);
  t.after(() => open.dispose());
  assert.equal(open.surface(0, z), null, 'no neighbouring tile supplies a point inside a real gap');
  assert.throws(() => checkFloor(open, { x: 0, z }), /unsupported footprint/);
  t.diagnostic(JSON.stringify({ sharedEdge: samples, pointRayMisses: misses.length }));
});

test('visitor and swept capsule stop at both wall joins and slide across them in both directions', async t => {
  const group = assembleFloorTransition(sources);
  group.add(...run().children);
  const scene = await measureWallContact(group);
  t.after(() => scene.dispose());
  const capsule = new RAPIER.Capsule(BODY.height / 2 - BODY.radius, BODY.radius);
  const touches = [];
  function approach(x) {
    const start = { x, z: -.7 };
    assert.equal(scene.visitor.obstruction(start), null);
    const cylinderHit = scene.sweep(start, 0, -1);
    const capsuleHit = scene.sweep(start, 0, -1, capsule);
    assert.equal(cylinderHit?.module, 'wall2m');
    assert.equal(capsuleHit?.module, 'wall2m');
    const p = { ...start };
    const blocked = scene.visitor.move(p, 0, -1);
    assert.ok(blocked && blocked !== 'Floor edge');
    assert.equal(scene.visitor.obstruction(p), null);
    const advance = start.z - p.z;
    const gap = cylinderHit.fraction - advance;
    assert.ok(gap >= -.0001 && gap <= BODY.step + .0001, 'visitor stop vs cylinder');
    // The cylinder touches the protruding plinth. The rounded capsule reaches the panel above it.
    const delta = capsuleHit.fraction - cylinderHit.fraction;
    assert.ok(delta >= .0025 && delta <= .0035, 'capsule vs plinth contact: ' + delta);
    checkFloor(scene, p);
    touches.push({ x, stopGapMm: gap * 1000, capsuleDeltaMm: delta * 1000 });
    return p;
  }
  for (const seam of [-1, 1]) for (const offset of [-.04, 0, .04]) approach(seam + offset);

  const p = approach(-2.1);
  let slideSamples = 0;
  for (const target of [2.1, -2.1]) {
    const startX = p.x;
    const steps = Math.ceil(Math.abs(target - startX) / .02);
    for (let i = 0; i < steps; i++) {
      const before = { ...p };
      const dx = (target - startX) / steps;
      const blocked = scene.visitor.move(p, dx, -.035);
      assert.ok(blocked && blocked !== 'Floor edge', 'visitor slides along the wall itself');
      near(p.x - before.x, dx, 'tangential motion');
      const dz = p.z - before.z;
      for (const shape of [undefined, capsule]) {
        const hit = scene.sweep(before, dx, dz, shape);
        assert.ok(!hit || (1 - hit.fraction) * Math.hypot(dx, dz) < .0001, 'slide crosses a wall triangle');
        const contact = scene.sweep(p, 0, -.05, shape);
        assert.equal(contact?.module, 'wall2m', 'the wall stays next to the traveller');
      }
      checkFloor(scene, p);
      slideSamples++;
    }
    near(p.x, target, 'end of slide');
  }
  assert.equal(scene.visitor.move(p, 0, .3), null, 'visitor can move away from wall');
  checkFloor(scene, p);
  t.diagnostic(JSON.stringify({ touches, slideMetres: 8.4, slideSamples, correctedFootRays: scene.corrections }));
});

test('repeating old walls at 2 m leaves open gaps and the original ceiling sits 200 mm above the new wall', () => {
  const old = run(legacyWall);
  for (const [i, x] of [-1, 1].entries()) {
    const a = new Box3().setFromObject(old.children[i], true);
    const b = new Box3().setFromObject(old.children[i + 1], true);
    near(b.min.x - a.max.x, .8, 'unsupported width');
    const ray = new Raycaster(new Vector3(x, 1.3, -1), front);
    assert.equal(ray.intersectObject(old, true).length, 0, 'old wall leaves a real opening');
  }
  const walls = run();
  for (const x of [-2, 0, 2]) {
    const ceiling = legacyCeiling.clone(true);
    // Put the cassette grid directly over the centreline at its former underside height.
    ceiling.position.set(x, 3, wallZ);
    ceiling.updateMatrixWorld(true);
    const wallTop = surface(walls, x, 2.95, wallZ, down);
    const underside = surface(ceiling, x, 2.85, wallZ, up);
    assert.match(underside.object.name, /GRID/i);
    near(underside.point.y - wallTop.point.y, .2, 'existing ceiling-grid clearance');
  }
});
