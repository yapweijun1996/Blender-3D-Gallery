import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { AnimationMixer, Box3, Group, MathUtils, Raycaster, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import {
  assembleEscalatorTerminals,
  escalatorTerminalPaths,
} from '../mall-modules-preview/escalator-terminal.js';
import { createEscalatorRoute } from '../mall-modules-preview/escalator-passenger-route.js';

const load = (path) => readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
const assets = Object.fromEntries(
  await Promise.all(
    Object.entries(escalatorTerminalPaths).map(async ([name, path]) => [name, await load(path)]),
  ),
);
const sources = Object.fromEntries(Object.entries(assets).map(([name, gltf]) => [name, gltf.scene]));
const visitor = await load('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb');
const p = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const upStart = -3.5339295944;
const downStart = 22.5426721993;
const boundaries = [-0.8, 1.2, 17.37, 19.16];
const options = (machine) => ({
  machine,
  clips: assets.escalator.animations,
  avatar: visitor.scene,
  avatarClips: visitor.animations,
});

function install(transformed = false, direction) {
  const { group } = assembleEscalatorTerminals(sources);
  const outer = new Group();
  if (transformed) {
    outer.position.set(7, 0.9, -2);
    outer.rotation.y = 0.73;
  }
  outer.add(group);
  outer.updateMatrixWorld(true);
  const machine = group.children.find((o) => o.userData.moduleId === 'escalator');
  const route = createEscalatorRoute(options(machine), direction);
  const floors = [];
  for (const terminal of group.children.filter((o) => o.userData.terminal)) {
    floors.push(
      ...terminal.children.filter(
        (o) => o.userData.role === 'centre' || o.userData.moduleId === 'escalatorTransition2m',
      ),
    );
  }
  machine.traverse((o) => {
    if (/^(STEP_BODY_|COMB_|LANDING_)/.test(o.name)) floors.push(o);
  });
  return { outer, machine, route, floors };
}

// A numeric phase belongs to the released route's original clock, including each belt's own loop.
function nativeClock(machine, t) {
  const mixer = new AnimationMixer(machine);
  for (const clip of assets.escalator.animations) {
    const action = mixer.clipAction(clip).play();
    action.time = MathUtils.euclideanModulo(t, clip.duration);
  }
  mixer.update(0);
  machine.updateWorldMatrix(true, true);
  return mixer;
}

function poles(visual) {
  const result = [];
  for (const name of ['LeftFoot', 'RightFoot']) {
    const foot = visual.getObjectByName(name);
    let low = null;
    foot.traverse((mesh) => {
      if (!mesh.isMesh) return;
      for (let index = 0; index < mesh.geometry.attributes.position.count; index++) {
        const pos = mesh.getVertexPosition(index, p()).applyMatrix4(mesh.matrixWorld);
        if (!low || pos.y < low.position.y) low = { mesh, index, position: pos };
      }
    });
    result.push(() => low.mesh.getVertexPosition(low.index, p()).applyMatrix4(low.mesh.matrixWorld));
  }
  return result;
}

function owner(mesh) {
  for (let node = mesh; node; node = node.parent) {
    if (/^(STEP_BODY_..|LANDING_Lower|LANDING_Upper)$/.test(node.name)) return node;
    if (['floor2m', 'escalatorTransition2m'].includes(node.userData.moduleId)) return node;
  }
}

function checkContacts(t, direction) {
  const descending = direction === 'down';
  const { route, floors } = install(false, direction);
  t.after(() => route.dispose());
  const readFeet = poles(route.visual),
    owners = new Set(),
    phases = new Set();
  const ray = new Raycaster(),
    down = p(0, -1, 0),
    previous = [null, null];
  let samples = 0,
    contacts = 0,
    maxSlip = 0,
    maxPenetration = 0,
    unsupported = 0;
  const times = [];
  for (let n = 0; n <= Math.floor(route.duration * 120); n++) times.push(n / 120);
  times.push(
    route.duration,
    ...boundaries.flatMap((native) =>
      [-1e-6, 0, 1e-6].map((e) => (descending ? downStart - native : native - upStart) + e),
    ),
  );
  let previousZ = route.visual.position.z;
  let maximumBacktrack = 0;
  for (const elapsed of times.sort((a, b) => a - b)) {
    route.seek(elapsed);
    const forward = descending ? 1 : -1;
    assert.ok(forward * route.visual.getWorldDirection(p()).z > 0.99999);
    maximumBacktrack = Math.max(maximumBacktrack, -forward * (route.visual.position.z - previousZ));
    previousZ = route.visual.position.z;
    phases.add(route.phase);
    samples++;
    let planted = 0;
    for (let i = 0; i < 2; i++) {
      const pole = readFeet[i]();
      ray.set(p(pole.x, pole.y + 0.3, pole.z), down);
      const hit = ray.intersectObjects(floors, true)[0];
      if (!hit) {
        previous[i] = null;
        continue;
      }
      const gap = pole.y - hit.point.y;
      maxPenetration = Math.max(maxPenetration, -gap);
      if (Math.abs(gap) > 1e-6) {
        previous[i] = null;
        continue;
      }
      const supported = owner(hit.object);
      assert.ok(supported, 'Unexpected support ' + hit.object.name);
      owners.add(supported.userData.moduleId ?? supported.name);
      planted++;
      contacts++;
      const anchor = supported.worldToLocal(pole.clone());
      if (previous[i]?.surface === supported)
        maxSlip = Math.max(maxSlip, anchor.distanceTo(previous[i].anchor));
      previous[i] = { surface: supported, anchor };
    }
    if (!planted) {
      if (!unsupported)
        t.diagnostic(
          'First unsupported at ' + elapsed + ' ' + JSON.stringify(readFeet.map((read) => read().toArray())),
        );
      unsupported++;
    }
  }
  assert.equal(unsupported, 0);
  assert.ok(maximumBacktrack < 1e-5, 'backward root motion ' + maximumBacktrack);
  assert.ok(maxPenetration < 1e-6 && maxSlip < 0.000001, `penetration ${maxPenetration}, slip ${maxSlip}`);
  assert.deepEqual([...phases], ['approach', 'board', 'ride', 'alight', 'depart']);
  assert.deepEqual(
    [...owners].sort(),
    ['floor2m', 'escalatorTransition2m', 'LANDING_Lower', 'LANDING_Upper', 'STEP_BODY_00'].sort(),
  );
  const lower = p(0, 0, 6),
    upper = p(0, 3, -6);
  assert.ok(route.visual.position.distanceTo(descending ? lower : upper) < 1e-5);
  route.restart();
  assert.ok(route.visual.position.distanceTo(descending ? upper : lower) < 1e-5);
  t.diagnostic(
    JSON.stringify({
      direction: direction ?? 'up',
      samples,
      contacts,
      unsupported,
      maxSlip,
      maxPenetration,
      maximumBacktrack,
      duration: route.duration,
    }),
  );
}

test('real shoes stay in contact across both terminals, both transfers and native STEP_00', (t) =>
  checkContacts(t));
test('the descending rider walks forward with at least one shoe planted from the upper slab to the lower slab', (t) =>
  checkContacts(t, 'down'));

function poseSignature(machine, visual) {
  const nodes = [visual];
  visual.traverse((o) => {
    if (!o.isMesh) nodes.push(o);
  });
  for (const clip of assets.escalator.animations)
    nodes.push(machine.getObjectByName(clip.tracks[0].name.split('.')[0]));
  return nodes.flatMap((n) => {
    n.updateMatrix();
    return n.matrix.toArray();
  });
}

function checkSeams(t, direction) {
  const descending = direction === 'down';
  const { route, machine } = install(false, direction);
  t.after(() => route.dispose());
  for (const time of [0, ...boundaries]) {
    const delta = 1e-5;
    const elapsed = descending ? downStart - time : time - upStart;
    route.seek(elapsed - delta);
    const before = poseSignature(machine, route.visual);
    route.seek(elapsed + delta);
    const after = poseSignature(machine, route.visual);
    const maxChange = Math.max(...after.map((v, i) => Math.abs(v - before[i])));
    assert.ok(maxChange < 0.0001, `pose jump ${maxChange} at ${time}`);
    const reference = assets.escalator.scene.clone(true),
      mixer = nativeClock(reference, time + (descending ? -delta : delta));
    for (const clip of assets.escalator.animations) {
      const name = clip.tracks[0].name.split('.')[0];
      const a = machine.getObjectByName(name),
        b = reference.getObjectByName(name);
      a.updateMatrix();
      b.updateMatrix();
      const difference = Math.max(
        ...a.matrix.elements.map((value, i) => Math.abs(value - b.matrix.elements[i])),
      );
      assert.ok(difference < 2e-6, name + ' at ' + time + ' transformed-matrix error ' + difference);
    }
    mixer.stopAllAction();
    mixer.uncacheRoot(reference);
  }
}

test('all sewn boundaries and the native zero wrap preserve actual skeleton and machine motion', (t) =>
  checkSeams(t));
test('all 58 treads and both handrails follow their own reversed native clocks through the descender’s transfers', (t) =>
  checkSeams(t, 'down'));

function checkScrub(t, direction) {
  const a = install(false, direction),
    b = install(true, direction);
  t.after(() => {
    a.route.dispose();
    b.route.dispose();
  });
  const timeline = [0, 0.51, 2.8, 3.7, 5.7, 12, 21.25, 22.9, 25.4, a.route.duration];
  const snapshots = [];
  for (const elapsed of timeline) {
    a.route.seek(elapsed);
    b.route.seek(elapsed);
    const A = poseSignature(a.machine, a.route.visual),
      B = poseSignature(b.machine, b.route.visual);
    const max = Math.max(...A.map((v, i) => Math.abs(v - B[i])));
    assert.ok(max < 2e-6, `frame disagreement ${max} at ${elapsed}`);
    snapshots.push(A);
  }
  for (const index of [9, 4, 0, 3, 5, 1, 4, 8, 2, 7, 0]) {
    a.route.seek(timeline[index]);
    const actual = poseSignature(a.machine, a.route.visual);
    assert.ok(Math.max(...actual.map((v, i) => Math.abs(v - snapshots[index][i]))) < 1e-9);
  }
  b.route.play();
  b.route.update(0.47);
  assert.equal(b.route.time, 0.47);
  b.route.pause();
  b.route.update(0.3);
  assert.equal(b.route.time, 0.47);
  b.route.update(0);
  b.route.restart();
  assert.equal(b.route.time, 0);
  assert.equal(b.route.playing, false);
}

test('seeking in either direction yields the same poses under a translated and rotated parent', (t) =>
  checkScrub(t));
test('the descending route preserves seek, pause and restart under a rotated parent', (t) =>
  checkScrub(t, 'down'));

test('a missing native landing leaves the installed machine in its original state', () => {
  const machine = assets.escalator.scene.clone(true);
  machine.getObjectByName('LANDING_Lower').removeFromParent();
  const children = [...machine.children];
  const step = machine.getObjectByName('STEP_00');
  const initialPose = step.matrix.toArray();
  assert.throws(() => createEscalatorRoute(options(machine)), /LANDING_Lower/);
  assert.deepEqual(machine.children, children);
  assert.deepEqual(step.matrix.toArray(), initialPose);
});

test('the reversed shoe footprint fits the exposed native tread and both swing knees flex forward', (t) => {
  const { machine, route } = install(false, 'down');
  t.after(() => route.dispose());
  const step = machine.getObjectByName('STEP_00');
  const body = machine.getObjectByName('STEP_BODY_00');
  const ahead = machine.getObjectByName('STEP_BODY_01');
  const shoes = ['LeftFoot', 'RightFoot'].map((name) => route.visual.getObjectByName(name));
  let front = Infinity,
    rear = Infinity;
  for (const native of [4, 6, 8, 10, 12, 14]) {
    route.seek(downStart - native);
    const footprint = new Box3();
    for (const shoe of shoes) footprint.union(new Box3().setFromObject(shoe, true));
    const tread = new Box3().setFromObject(body, true),
      neighbour = new Box3().setFromObject(ahead, true);
    assert.ok(neighbour.max.y > tread.max.y + 0.01);
    const exposedFront = Math.max(tread.min.z, neighbour.max.z);
    front = Math.min(front, footprint.min.z - exposedFront);
    rear = Math.min(rear, tread.max.z - footprint.max.z);
    const offset = step.worldToLocal(route.visual.getWorldPosition(p()));
    assert.ok(Math.abs(offset.z - 0.123817428) < 1e-6);
    // Rotating in place at the ascending stance would leave the back of this tread.
    assert.ok(footprint.max.z + 0.24 - offset.z > tread.max.z + 0.09);
  }
  assert.ok(front > 0.02 && rear > 0.022);
  for (const [native, name] of [
    [18.62, 'Right'],
    [-0.21, 'Left'],
  ]) {
    route.seek(downStart - native);
    const pos = (suffix) => route.visual.getObjectByName(name + suffix).getWorldPosition(p());
    const hip = pos('Hip'),
      knee = pos('Knee'),
      ankle = pos('Foot');
    const where = (knee.y - hip.y) / (ankle.y - hip.y);
    const forward = knee.z - MathUtils.lerp(hip.z, ankle.z, where);
    assert.ok(forward > 0.035, 'swing knee bent away from the direction of walking: ' + forward);
  }
  t.diagnostic(JSON.stringify({ front, rear }));
});
