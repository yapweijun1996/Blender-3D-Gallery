import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Group } from 'three';
import { checkFloor, measureCorridor, walk } from './helpers/mall-mesh.mjs';
import { BODY } from '../docs/verification/mall-corridor/collision.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { shellAssetPaths, shellLayout, placeShellModule } from '../mall-modules-preview/shell-layout.js';

const inputs = {};
const sources = {};
for (const id of new Set([...shellLayout.floor, ...shellLayout.walls].map(part => part.id))) {
  const path = shellAssetPaths[id];
  const { bytes, scene } = await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
  inputs[id] = { path, sha256: createHash('sha256').update(bytes).digest('hex') };
  sources[id] = scene;
}

async function install(floors, walls) {
  const root = new Group();
  for (const [parts, isFloor] of [[floors, true], [walls, false]]) {
    for (const [i, placement] of parts.entries()) {
      const object = placeShellModule(sources, placement);
      if (isFloor) object.name = 'Floor_' + i; // The mall visitor identifies installed floor cells by this name.
      root.add(object);
      object.userData.moduleId = placement.id;
    }
  }
  return measureCorridor(root);
}

function wallStop(scene, x, z, dx, dz, expectedModules) {
  const start = { x, z }, end = { ...start };
  assert.equal(scene.visitor.obstruction(start), null, 'wall approach must begin clear');
  const hit = scene.sweep(start, dx, dz);
  assert.ok(hit && hit.fraction > 0 && hit.fraction < 1 && expectedModules.includes(hit.module),
    'expected a swept cylinder contact with ' + expectedModules.join(' or '));
  const blocked = scene.visitor.move(end, dx, dz);
  assert.ok(blocked && blocked !== 'Floor edge', 'visitor must stop at the wall itself');
  assert.equal(scene.visitor.obstruction(end), null);
  checkFloor(scene, end);
  const distance = Math.hypot(dx, dz);
  const margin = hit.fraction * distance - Math.hypot(end.x - x, end.z - z);
  // A free final substep can leave a small gap; allowing it to cross the triangles
  // would mask a collision regression, even if the visitor eventually stops.
  assert.ok(margin >= -.0001 && margin <= BODY.step + .0001, 'visitor stop vs mesh, metres: ' + margin);
  return { x: end.x, z: end.z, hit: hit.module, gapMm: +(margin * 1000).toFixed(3) };
}

function slideAlongWall(scene, start, dx, dz, axis) {
  const end = { x: start.x, z: start.z };
  const count = Math.ceil(Math.hypot(dx, dz) / BODY.step);
  const normalAxis = axis === 'x' ? 'z' : 'x';
  let wallContacts = 0;
  for (let i = 0; i < count; i++) {
    const before = { ...end };
    const hit = scene.visitor.move(end, dx / count, dz / count);
    if (hit) {
      assert.notEqual(hit, 'Floor edge', 'wall sliding must keep the footprint on the floor');
      wallContacts++;
    }
    const mx = end.x - before.x, mz = end.z - before.z;
    const contact = scene.sweep(before, mx, mz);
    assert.ok(!contact || (1 - contact.fraction) * Math.hypot(mx, mz) <= .0001,
      'sliding path crosses an installed wall triangle');
    checkFloor(scene, end);
  }
  const progress = end[axis] - start[axis];
  assert.ok(Math.abs(progress - (axis === 'x' ? dx : dz)) < 1e-6, 'unimpeded tangential motion');
  assert.ok(Math.abs(end[normalAxis] - start[normalAxis]) <= BODY.step, 'wall holds the normal position');
  assert.ok(wallContacts >= count - 2, 'sustained wall contact across the join');
  return { progress, wallContacts };
}

const route = [{ x: 1.2, z: -2.12 }, { x: 3.42, z: -2.12 }, { x: 3.42, z: .84 }];
test('mall visitor walks the 1.2 m shell and slides across both inside wall joins', async t => {
  const scene = await install(shellLayout.floor, shellLayout.walls);
  t.after(() => scene.dispose());
  const walkResult = walk(scene, [...route, ...route.slice(0, -1).reverse()]);
  // Approach either side of each straight-to-corner join, as well as its exact mating plane.
  const rearJoin = [[2.4, ['wall']], [3, ['wall', 'wallCorner']], [3.5, ['wallCorner']]];
  const rightJoin = [[-2.04, ['wallCorner']], [-1.74, ['wall', 'wallCorner']], [-1.1, ['wall']]];
  const rear = rearJoin.map(([x, modules]) => wallStop(scene, x, -1.9, 0, -2, modules));
  const right = rightJoin.map(([z, modules]) => wallStop(scene, 3.2, z, 2, 0, modules));
  const slideRear = slideAlongWall(scene, rear[0], .95, -.95, 'x');
  const slideRight = slideAlongWall(scene, right[2], 1.02, -1.02, 'z');
  const slide = { x: 3.1, z: -1.9 };
  assert.equal(scene.visitor.obstruction(slide), null);
  const contact = scene.visitor.move(slide, 1.8, -1.8);
  assert.ok(contact && contact !== 'Floor edge', 'diagonal motion must hit the inside corner');
  assert.ok(Math.abs(slide.x - right[0].x) <= BODY.step && Math.abs(slide.z - rear[2].z) <= BODY.step,
    'diagonal traveler slides into both walls without crossing them');
  assert.equal(scene.visitor.obstruction(slide), null);
  checkFloor(scene, slide);
  walk(scene, [slide, { x: slide.x - .5, z: slide.z + .5 }]);
  t.diagnostic(JSON.stringify({ inputs, visitor: BODY, walk: walkResult, rear, right, slideRear, slideRight, diagonalStop: slide }));
});

// Removing the L-wall leaves the floor intact. The floor edge can still stop the
// projected visitor, but it cannot pass the independent triangle contact check.
test('an omitted L-wall exposes a floor-edge stop instead of a mesh contact', async t => {
  const missingCorner = await install(shellLayout.floor, shellLayout.walls.filter(part => part.id !== 'wallCorner'));
  t.after(() => missingCorner.dispose());
  assert.throws(() => wallStop(missingCorner, 3.5, -1.9, 0, -2, ['wallCorner']), /swept cylinder contact/);
  const p = { x: 3.5, z: -1.9 };
  assert.equal(missingCorner.visitor.move(p, 0, -2), 'Floor edge');
  t.diagnostic('Visitor reaches floor edge at Z = ' + p.z.toFixed(3));
});

// The visitor's flat X/Z chart still accepts a lowered tile. Floor triangle
// samples must independently detect the lost support along the actual walk.
test('triangle support catches a 300 mm dropped tile accepted by the flat visitor chart', async t => {
  const droppedFloor = shellLayout.floor.map(part =>
    part.x === 2.4 && part.z === -2.4 ? { ...part, y: part.y - .30 } : part);
  const dropped = await install(droppedFloor, shellLayout.walls);
  t.after(() => dropped.dispose());
  assert.equal(dropped.visitor.obstruction({ x: 2.4, z: -2.12 }), null);
  assert.ok(Math.abs(dropped.surface(2.4, -2.12) + .30) <= .001001, 'actual dropped floor elevation');
  assert.throws(() => walk(dropped, route), /unsupported footprint/);
});
