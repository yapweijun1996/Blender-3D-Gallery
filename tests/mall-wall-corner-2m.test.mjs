import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Matrix4, Mesh, Raycaster, Vector3 } from 'three';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { BODY } from '../docs/verification/mall-corridor/collision.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { assembleCornerFloor, wallCornerPath, wallRunPath } from '../mall-modules-preview/wall-run.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
for (const [id, path] of Object.entries({ ...floorTransitionPaths, wall2m: wallRunPath, wallCorner2m: wallCornerPath })) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const px = 2.925, pz = -1.925;
const up = new Vector3(0, 1, 0), down = new Vector3(0, -1, 0);
const rearFacing = new Vector3(0, 0, -1), rightFacing = new Vector3(1, 0, 0);
function near(actual, expected, label) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < .000001, `${label}: ${actual}, expected ${expected}`);
}
function parts() {
  const group = assembleCornerFloor(sources);
  group.updateMatrixWorld(true);
  const corner = group.children.find(p => p.userData.moduleId === 'wallCorner2m');
  const straights = group.children.filter(p => p.userData.moduleId === 'wall2m');
  const rear = straights.find(p => p.position.x < 0), right = straights.find(p => p !== rear);
  const floors = group.children.filter(p => p.userData.moduleId.startsWith('floor'));
  return { group, corner, rear, right, floors };
}
function hit(objects, x, y, z, dir) {
  const target = new Raycaster(new Vector3(x, y, z), dir).intersectObjects(objects, true)[0];
  assert.ok(target, `no triangle at ${x}, ${y}, ${z} along ${dir.toArray()}`);
  return target;
}
function profile(part, isRear, along, y) {
  const h = isRear ? hit([part], along, y, pz + 1, rearFacing) : hit([part], px - 1, y, along, rightFacing);
  return { depth: isRear ? h.point.z - pz : px - h.point.x, material: h.object.material.name };
}

test('both native corner connector pairs and the two finished profiles meet their straight runs', () => {
  const { corner, rear, right } = parts();
  assert.deepEqual(corner.position.toArray(), [px, 0, pz]);
  for (const wall of [corner, rear, right]) assert.deepEqual(wall.scale.toArray(), [1, 1, 1]);
  const b = new Box3().setFromObject(corner, true);
  near(b.min.x, px - 2, 'rear arm end'); near(b.max.z, pz + 2, 'return arm end');
  near(b.max.x, 3, 'outside edge X'); near(b.min.z, -2, 'outside edge Z');
  for (const [isRear, first, second, a, b] of [
    [true, rear, corner, 'CONNECTOR_Right_LOD0', 'CONNECTOR_Left_LOD0'],
    [false, corner, right, 'CONNECTOR_Return_LOD0', 'CONNECTOR_Left_LOD0'],
  ]) {
    const p = first.getObjectByName(a).getWorldPosition(new Vector3());
    const q = second.getObjectByName(b).getWorldPosition(new Vector3());
    near(p.distanceTo(q), 0, 'connector contact');
    near(p.x, isRear ? px - 2 : px, 'connector X');
    near(p.y, 0, 'connector altitude');
    near(p.z, isRear ? pz : pz + 2, 'connector Z');
    const join = isRear ? p.x : p.z;
    for (const [part, sign] of [[first, -1], [second, 1]]) {
      for (const [y, offset, depth, material] of [[.06, .00001, .075, /bronze/i], [2.78, .00001, .075, /bronze/i],
        [.5, .0019, .062, /mortar/i], [.5, .006, .072, /limestone/i],
        [2, .0019, .062, /mortar/i], [2, .006, .072, /limestone/i], [1.43, .006, .062, /mortar/i]]) {
        const finish = profile(part, isRear, join + sign * offset, y);
        assert.match(finish.material, material);
        near(finish.depth, depth, 'interior finish offset');
      }
    }
  }
});

test('both physical faces continue through the mitre and the two arms bear on the finished floor', t => {
  const { corner, rear, right, floors } = parts();
  let bearing = 0, recessed = 0;
  function support(part, x, z) {
    const bottom = hit([part], x, -.25, z, up).point.y;
    const top = hit(floors, x, .2, z, down).point.y;
    near(bottom, 0, 'wall underside');
    const gap = bottom - top;
    assert.ok(gap >= -.000001 && gap <= .001001, `wall/floor gap ${gap} m`);
    if (gap > .00001) recessed++;
    else bearing++;
  }
  for (const [wall, isRear, start] of [[rear, true, px - 4], [corner, true, px - 2],
    [corner, false, pz], [right, false, pz + 2]]) {
    for (let i = 0; i < 40; i++) {
      // Stay outside the mitre square; its footprint is checked separately below.
      const along = start + .095 + i * 1.81 / 39;
      for (const across of [-.07499, -.04, 0, .05, .0689]) {
        support(wall, isRear ? along : px - across, isRear ? pz + across : along);
      }
    }
  }
  for (const dx of [-.06, 0, .06]) for (const dz of [-.06, 0, .06]) support(corner, px + dx, pz + dz);
  assert.ok(bearing > 0 && recessed > 0, 'legacy grout and flush finished surfaces are both represented');

  let profileRays = 0;
  for (const sign of [-1, 1]) {
    // sign=+1 looks from the room; sign=-1 looks at the unadorned external corner.
    const direction = new Vector3(sign, 0, -sign).normalize();
    for (const y of [.06, .5, 1.43, 2, 2.78]) for (const offset of [-.012, -.007, -.0008, 0, .0008, .007, .012]) {
      const x = px - .75 * direction.x + offset, z = pz - .75 * direction.z + offset;
      const h = hit([corner], x, y, z, direction);
      let depth = -.075, material = /mortar/i;
      if (sign > 0) {
        const trim = y < .1 || y > 2.75;
        const mortar = y === 1.43 || Math.abs(offset) < .001;
        depth = trim ? .075 : mortar ? .062 : .072;
        material = trim ? /bronze/i : mortar ? /mortar/i : /limestone/i;
      }
      assert.match(h.object.material.name, material);
      near(offset <= 0 ? h.point.z - pz : px - h.point.x, depth, 'first mitre face');
      if (offset === 0) near(px - h.point.x, depth, 'intersection of both mitre planes');
      profileRays++;
    }
  }
  t.diagnostic(JSON.stringify({ bearing, recessed, interiorAndExteriorRays: profileRays }));
});

test('the visitor slides along both arms, turns inside the elbow and returns across both seams', async t => {
  const { group } = parts();
  const scene = await measureWallContact(group);
  t.after(() => scene.dispose());
  const capsule = new RAPIER.Capsule(BODY.height / 2 - BODY.radius, BODY.radius);
  const p = { x: .1, z: -.7 };
  const travelled = { distance: 0, positions: 0 };
  function wallContact(p, dx, dz) {
    for (const shape of [undefined, capsule]) {
      const contact = scene.sweep(p, dx, dz, shape);
      assert.ok(['wall2m', 'wallCorner2m'].includes(contact?.module), 'swept body must contact an actual wall');
    }
  }
  function push(dx, dz) {
    const before = { ...p };
    const blocked = scene.visitor.move(p, dx, dz);
    assert.ok(blocked && blocked !== 'Floor edge', 'the wall itself must hold the visitor');
    const ax = p.x - before.x, az = p.z - before.z;
    for (const shape of [undefined, capsule]) {
      const contact = scene.sweep(before, ax, az, shape);
      assert.ok(!contact || (1 - contact.fraction) * Math.hypot(ax, az) < .0001, 'accepted move crosses a wall');
    }
    assert.equal(scene.visitor.obstruction(p), null);
    checkFloor(scene, p);
    travelled.distance += Math.hypot(ax, az);
    travelled.positions++;
  }
  function slide(axis, target) {
    const tangential = target - p[axis], steps = Math.ceil(Math.abs(tangential) / .02);
    for (let i = 0; i < steps; i++) {
      const delta = tangential / steps;
      push(axis === 'x' ? delta : .035, axis === 'x' ? -.035 : delta);
      wallContact(p, axis === 'z' ? .06 : 0, axis === 'x' ? -.06 : 0);
    }
    near(p[axis], target, 'free tangential travel');
  }
  for (const [x, z] of [[1.5, -.6], [1.7, -.85], [2.12, -1.15]]) {
    assert.equal(scene.visitor.obstruction({ x, z }), null, 'the inside of the elbow stays open');
    assert.equal(scene.sweep({ x, z }, .01, .005, capsule), null);
  }
  assert.equal(scene.visitor.obstruction(p), null);
  wallContact(p, 0, -1);
  push(0, -1);
  slide('x', 2.05);
  for (let i = 0; i < 18; i++) push(.025, -.025);
  const turn = { ...p };
  wallContact(turn, .06, 0); wallContact(turn, 0, -.06);
  slide('z', .8);
  slide('z', turn.z);
  wallContact(p, .06, 0); wallContact(p, 0, -.06);
  slide('x', .1);
  assert.equal(scene.visitor.move(p, 0, .25), null);
  checkFloor(scene, p);
  t.diagnostic(JSON.stringify({ turn, travelled, correctedFootRays: scene.corrections }));
});

test('reversing the return wall keeps the joint plane but puts the plain backing inside', () => {
  const { right, corner } = parts();
  right.rotation.y = Math.PI / 2;
  right.updateMatrixWorld(true);
  const join = pz + 2;
  near(new Box3().setFromObject(right, true).min.z, join, 'incorrect rotation still mates');
  near(new Box3().setFromObject(corner, true).max.z, join, 'elbow mating plane');
  const wanted = profile(corner, false, join - .006, .5);
  const wrong = profile(right, false, join + .006, .5);
  assert.match(wanted.material, /limestone/i); assert.match(wrong.material, /mortar/i);
  near(wrong.depth - wanted.depth, .003, 'back face protrudes beyond the stone');
});

test('removing the elbow leaves floor-edge stops in place of both physical arms', async t => {
  const { group, corner } = parts();
  group.remove(corner);
  const scene = await measureWallContact(group);
  t.after(() => scene.dispose());
  for (const [x, z, dx, dz] of [[1.8, -.7, 0, -1.5], [1.9, -.75, 1.5, 0]]) {
    const p = { x, z };
    assert.equal(scene.visitor.obstruction(p), null);
    assert.equal(scene.sweep(p, dx, dz), null, 'no wall remains on the missing arm');
    assert.equal(scene.visitor.move(p, dx, dz), 'Floor edge');
    checkFloor(scene, p);
  }
});

test('combining the real backing into one L mesh recreates the original false obstacle', async t => {
  const { group, corner } = parts();
  const backing = [];
  corner.traverse(mesh => { if (mesh.isMesh && /mortar substrate/i.test(mesh.material.name)) backing.push(mesh); });
  assert.ok(backing.length >= 2, 'the installed backing has independently bounded arms');
  const inverse = new Matrix4().copy(corner.matrixWorld).invert();
  const actualGeometry = backing.map(mesh =>
    mesh.geometry.clone().applyMatrix4(new Matrix4().multiplyMatrices(inverse, mesh.matrixWorld)));
  const combined = new Mesh(mergeGeometries(actualGeometry), backing[0].material);
  combined.name = 'Original combined L backing';
  for (const mesh of backing) mesh.removeFromParent();
  corner.add(combined);
  const scene = await measureWallContact(group);
  t.after(() => scene.dispose());
  const p = { x: 1.5, z: -.6 };
  assert.equal(scene.visitor.obstruction(p), combined.name, 'component envelope incorrectly fills the interior');
  assert.equal(scene.sweep(p, .15, -.1), null, 'actual L triangles leave the same movement clear');
  checkFloor(scene, p);
});
