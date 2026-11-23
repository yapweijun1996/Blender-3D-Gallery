import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { assembleFloorTransition, floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { measureCorridor, walk } from './helpers/mall-mesh.mjs';

const eps = 1e-6;
const down = new Vector3(0, -1, 0);
const sources = {};
for (const [id, path] of Object.entries(floorTransitionPaths)) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const pitch = { floor: 1.2, floor2m: 2 };
const thickness = { floor: .03, floor2m: .1 };

function near(actual, expected, label) {
  assert.ok(Math.abs(actual - expected) <= eps, `${label}: ${actual} m, expected ${expected} m`);
}
function installed() {
  const group = assembleFloorTransition(sources);
  group.updateMatrixWorld(true);
  return group;
}
function floorHit(root, x, z) {
  return new Raycaster(new Vector3(x, 1, z), down).intersectObject(root, true)[0];
}
function finishedHeight(root, x, z) {
  const hit = floorHit(root, x, z);
  assert.ok(hit, `no floor triangle at ${x}, ${z} in ${root.name}`);
  const y = hit.point.y;
  // The authored grout recess is 1 mm. Its T junctions can meet level stone across the seam.
  assert.ok(y >= -.001 - eps && y <= eps, `floor surface at ${x}, ${z} in ${root.name} is ${y} m`);
  return y;
}

test('mixed floor uses native 2 m and 1.2 m GLBs with coplanar tops and metric footprints', () => {
  const group = installed();
  assert.equal(group.children.length, 13);
  assert.equal(new Set(group.children.map(tile => tile.name)).size, 13);
  for (const id of Object.keys(pitch)) {
    const rotated = group.children.some(tile => tile.userData.moduleId === id &&
      Math.abs(Math.sin(tile.rotation.y)) > .99);
    assert.ok(rotated, id + ' must exercise a quarter-turned repeat in this sample');
  }
  const expected = [
    ...[.6, 1.8].flatMap(z => [-2.4, -1.2, 0, 1.2, 2.4].map(x => ['floor', x, z])),
    ...[-2, 0, 2].map(x => ['floor2m', x, -1]),
  ];
  for (const [id, x, z] of expected) {
    const tile = group.children.find(part => part.userData.moduleId === id &&
      Math.abs(part.position.x - x) <= eps && Math.abs(part.position.z - z) <= eps);
    assert.ok(tile, `${id} missing at ${x}, ${z}`);
    assert.match(tile.name, /^Floor_\d+$/, 'the mall visitor must recognize each placement');
    assert.deepEqual(tile.scale.toArray(), [1, 1, 1], 'use whole roots at authored scale');
    near(tile.rotation.x, 0, 'pitch');
    near(tile.rotation.z, 0, 'roll');
    near(Math.sin(2 * tile.rotation.y), 0, 'yaw must be a whole quarter turn');
    const bounds = new Box3().setFromObject(tile, true);
    near(bounds.min.y, -thickness[id], id + ' underside');
    near(bounds.max.y, 0, id + ' finished floor');
    for (const [axis, center] of [['x', x], ['z', z]]) {
      near(bounds.min[axis], center - pitch[id] / 2, id + ' lower ' + axis);
      near(bounds.max[axis], center + pitch[id] / 2, id + ' upper ' + axis);
    }
    near(finishedHeight(tile, x + .137, z + .173), 0, 'stone surface');
  }
});

test('actual faces meet across the full six-metre transition and all internal joins', t => {
  const tiles = installed().children.map(tile => ({ tile, box: new Box3().setFromObject(tile, true) }));
  let transition = 0, internal = 0, transitionLength = 0, rays = 0;
  for (const axis of ['x', 'z']) {
    const cross = axis === 'x' ? 'z' : 'x';
    for (const a of tiles) for (const b of tiles) {
      if (Math.abs(a.box.max[axis] - b.box.min[axis]) > eps) continue;
      const start = Math.max(a.box.min[cross], b.box.min[cross]);
      const end = Math.min(a.box.max[cross], b.box.max[cross]);
      if (end - start <= eps) continue; // A corner touching at one point is not an edge.
      const mixed = a.tile.userData.moduleId !== b.tile.userData.moduleId;
      if (mixed) {
        assert.equal(axis, 'z');
        near(a.box.max.z, 0, 'mixed joint plane');
        transitionLength += end - start;
        transition++;
      } else {
        internal++;
      }
      const seam = (a.box.max[axis] + b.box.min[axis]) / 2;
      // Probe each tile individually so a duplicate or neighbour cannot hide a hole.
      const intervals = Math.ceil((end - start) / .025);
      for (let i = 0; i <= intervals; i++) {
        const along = start + .0005 + (end - start - .001) * i / intervals;
        for (const offset of [.000003, .001, .003]) {
          for (const [part, coordinate] of [[a, seam - offset], [b, seam + offset]]) {
            const [x, z] = axis === 'x' ? [coordinate, along] : [along, coordinate];
            finishedHeight(part.tile, x, z);
            rays++;
          }
        }
      }
    }
  }
  assert.equal(transition, 7, 'overlap intervals from five legacy and three new tile edges');
  near(transitionLength, 6, 'mixed contact length');
  assert.equal(internal, 15, 'eight plus five legacy joins and two 2 m joins');
  t.diagnostic(JSON.stringify({ transition, internal, transitionLength, triangleRays: rays }));
});

test('visitor crosses the mixed seam both ways at staggered joints on real floor triangles', async t => {
  const scene = await measureCorridor(installed());
  t.after(() => scene.dispose());
  const route = [{ x: -1.8, z: 1.8 }, { x: -1.8, z: -1.24 }, { x: -1, z: -1.24 },
    { x: -1, z: 1.8 }, { x: 1, z: 1.8 }, { x: 1, z: -1.24 }, { x: 1.8, z: -1.24 },
    { x: 1.8, z: 1.8 }];
  const forward = walk(scene, route);
  const reverse = walk(scene, route.toReversed());
  assert.equal(forward.metres, reverse.metres);
  t.diagnostic(JSON.stringify({ forward, reverse }));
});

test('using the old tile at the new pitch leaves an 800 mm unsupported strip', () => {
  const group = installed();
  const wide = group.children.filter(part => part.userData.moduleId === 'floor2m');
  for (const tile of wide) {
    const copy = sources.floor.clone(true);
    copy.position.copy(tile.position);
    copy.position.y = -.03;
    copy.rotation.copy(tile.rotation);
    group.remove(tile);
    group.add(copy);
  }
  group.updateMatrixWorld(true);
  const row = group.children.filter(tile => tile.position.z === -1)
    .map(tile => new Box3().setFromObject(tile, true)).sort((a, b) => a.min.x - b.min.x);
  for (const [i, x] of [-1, 1].entries()) {
    near(row[i + 1].min.x - row[i].max.x, .8, 'bare strip width');
    assert.equal(floorHit(group, x, -.8), undefined, 'actual triangles leave the strip open');
    assert.throws(() => finishedHeight(group, x, -.8), /no floor triangle/);
  }
});

test('sharing the underside height lifts the 2 m wearing surface by 70 mm', () => {
  const group = installed();
  for (const tile of group.children) if (tile.userData.moduleId === 'floor2m') tile.position.y = -.03;
  group.updateMatrixWorld(true);
  const x = .137, top = floorHit(group, x, -.01);
  assert.ok(top);
  near(top.point.y - finishedHeight(group, x, .01), .07, 'step across the mixed joint');
  assert.throws(() => finishedHeight(group, x, -.01), /floor surface/);
});
