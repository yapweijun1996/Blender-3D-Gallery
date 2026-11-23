import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Vector3 } from 'three';
import { batchStaticMeshes } from '../mall-modules-preview/batch-static.js';
import { arrival, assembleCorridor, corridorAssetPaths, corridorLayout } from '../mall-modules-preview/corridor-layout.js';
import { BODY } from '../docs/verification/mall-corridor/collision.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { measureCorridor, walk } from './helpers/mall-mesh.mjs';

const sources = {};
for (const [id, path] of Object.entries(corridorAssetPaths)) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}

async function install(t, angle, placements = corridorLayout) {
  const { group, poseDoors } = assembleCorridor(sources, placements);
  poseDoors(angle);
  const scene = await measureCorridor(group);
  t.after(() => scene.dispose());
  return scene;
}

function approach(sign) {
  return [arrival, { x: sign * 1.98, z: arrival.z }, { x: sign * 1.98, z: -.09 },
    { x: sign * 1.76, z: -.31 }, { x: sign * 1.65, z: -.31 }];
}
const shop = sign => ({ x: sign * 1.65, z: -2.08 });

test('arrival reaches both closed shop doors in the furnished corridor', async t => {
  const scene = await install(t, 0);
  for (const sign of [-1, 1]) {
    walk(scene, approach(sign));
    const p = { ...approach(sign).at(-1) };
    const dz = shop(sign).z - p.z, start = p.z;
    const hit = scene.sweep(p, 0, dz);
    assert.equal(hit?.module, 'door', 'first mesh at the closed doorway');
    assert.ok(scene.visitor.move(p, 0, dz), 'the closed door stops the visitor');
    assert.ok(p.z > -1.2 && Math.abs(p.z - (start + hit.fraction * dz)) <= BODY.step, 'visitor and mesh stops agree');
  }
});

test('both open shop doors admit the whole furnished visitor and allow a return to arrival', async t => {
  const scene = await install(t, 90);
  for (const [id, side] of [['directory', -1], ['lightbox', 1], ['shelf', -1], ['shelf', 1]]) {
    assert.deepEqual(scene.overlaps(id, side), [], id + ' must clear the other furnishings and structure');
  }
  const left = shop(-1), right = shop(1);
  assert.ok(left.z + BODY.radius < -1.26 && right.z + BODY.radius < -1.26, 'whole visitor clears the rear of the frames');
  const route = [...approach(-1), left, right, ...approach(1).reverse()];
  const forward = walk(scene, route), reverse = walk(scene, [...route].reverse());
  t.diagnostic(JSON.stringify({ inputs: Object.keys(sources).length, forward, reverse }));
  const bench = scene.sweep(arrival, 0, -2);
  assert.equal(bench?.module, 'bench', 'a direct cut across the seating is blocked');
  const p = { ...arrival };
  assert.ok(scene.visitor.move(p, 0, -2));
  assert.ok(Math.abs(arrival.z - p.z - 2 * bench.fraction) <= BODY.step, 'visitor stops at the occupied seat');
});

test('old shelf and sign placements obstruct the routes and cross both column meshes', async t => {
  const former = corridorLayout.map(part => {
    const side = Math.sign(part.x);
    if (part.id === 'shelf') return { ...part, x: side * 1.65 };
    if (part.id === 'directory' || part.id === 'lightbox') return { ...part, x: side * 3, z: -.25 };
    return part;
  });
  const scene = await install(t, 90, former);
  for (const [sign, signId] of [[-1, 'directory'], [1, 'lightbox']]) {
    assert.ok(scene.overlaps(signId, sign).includes('column'), 'original sign triangles intersect their column');
    const path = approach(sign), entry = path.at(-1), inside = shop(sign);
    assert.equal(scene.sweep(path[1], 0, path[2].z - path[1].z)?.module, signId);
    assert.equal(scene.sweep(entry, 0, inside.z - entry.z)?.module, 'shelf');
    const p = { ...entry };
    assert.ok(scene.visitor.move(p, 0, inside.z - entry.z));
    assert.ok(p.z + BODY.radius > -1.26, 'old shelf stops the body before it clears the door frame');
  }
});

test('a visitor in the door swing restores all four hinges to their previous pose', async t => {
  const { group, poseDoors } = assembleCorridor(sources);
  const scene = await measureCorridor(group);
  t.after(() => scene.dispose());
  const visitor = scene.visitor;
  const position = { x: -1.65, z: -.31 };
  const doors = group.children.filter(part => part.userData.moduleId === 'door');
  const angles = () => doors.flatMap(door => ['HINGE_Left', 'HINGE_Right'].map(id => door.getObjectByName(id).rotation.y));
  assert.equal(visitor.obstruction(position), null, 'clear when closed');
  assert.equal(visitor.doorTransition(0, 90, arrival, poseDoors), true);
  assert.equal(visitor.obstruction(position), null, 'clear when open');
  const open = angles();
  assert.deepEqual(open, [-Math.PI / 2, Math.PI / 2, -Math.PI / 2, Math.PI / 2]);
  assert.equal(visitor.doorTransition(90, 0, position, poseDoors), false, 'an intermediate angle strikes the body');
  assert.deepEqual(angles(), open, 'both doors must roll back');
  assert.equal(visitor.obstruction(position), null, 'restored collider pose');
  assert.equal(visitor.doorTransition(90, 0, arrival, poseDoors), true);
  assert.ok(angles().every(angle => angle === 0));
});

test('assembly batching preserves transformed surfaces per material, glazing and moving door meshes', t => {
  const { group, poseDoors } = assembleCorridor(sources);
  group.position.set(-2, .3, 4);
  group.rotation.y = .42;
  poseDoors(90);
  function visibleGeometry() {
    group.updateMatrixWorld(true);
    const byMaterial = new Map(), bounds = new Map(), dynamic = new Set();
    const point = new Vector3();
    let meshes = 0;
    group.traverseVisible(mesh => {
      if (!mesh.isMesh) return;
      meshes++;
      const triangles = (mesh.geometry.index?.count ?? mesh.geometry.getAttribute('position').count) / 3;
      byMaterial.set(mesh.material, (byMaterial.get(mesh.material) ?? 0) + triangles);
      if (!bounds.has(mesh.material)) bounds.set(mesh.material, new Box3());
      const positions = mesh.geometry.getAttribute('position');
      for (let i = 0; i < positions.count; i++) {
        bounds.get(mesh.material).expandByPoint(point.fromBufferAttribute(positions, i).applyMatrix4(mesh.matrixWorld));
      }
      let root = mesh;
      while (root.parent && root.parent !== group) root = root.parent;
      if (mesh.material.transparent || root.userData.moduleId === 'door') dynamic.add(mesh);
    });
    return { meshes, byMaterial, bounds, dynamic };
  }
  const before = visibleGeometry();
  batchStaticMeshes(group);
  const after = visibleGeometry();
  assert.deepEqual(after.byMaterial, before.byMaterial);
  assert.deepEqual(after.dynamic, before.dynamic);
  for (const [material, box] of before.bounds) {
    const merged = after.bounds.get(material);
    assert.ok(box.min.distanceTo(merged.min) < 1e-5 && box.max.distanceTo(merged.max) < 1e-5,
      material.name + ' keeps its world-space bounds');
  }
  assert.ok(after.meshes < before.meshes / 2, 'fixed module repeats are actually batched');
  t.diagnostic('Visible meshes before/after batches: ' + before.meshes + '/' + after.meshes);
});
