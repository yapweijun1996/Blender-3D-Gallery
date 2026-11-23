import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { AnimationMixer, Group, MathUtils, Raycaster, Vector3 } from 'three';
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
const nativeStart = -3.5339295944;
const boundaries = [-0.8, 1.2, 17.37, 19.16];
const options = (machine) => ({
  machine,
  clips: assets.escalator.animations,
  avatar: visitor.scene,
  avatarClips: visitor.animations,
});

function install(transformed = false) {
  const { group } = assembleEscalatorTerminals(sources);
  const outer = new Group();
  if (transformed) {
    outer.position.set(7, 0.9, -2);
    outer.rotation.y = 0.73;
  }
  outer.add(group);
  outer.updateMatrixWorld(true);
  const machine = group.children.find((o) => o.userData.moduleId === 'escalator');
  const route = createEscalatorRoute(options(machine));
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

test('real shoes stay in contact across both terminals, both transfers and native STEP_00', (t) => {
  const { route, floors } = install();
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
    ...boundaries.flatMap((native) => [-1e-6, 0, 1e-6].map((e) => native - nativeStart + e)),
  );
  for (const elapsed of times.sort((a, b) => a - b)) {
    route.seek(elapsed);
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
  assert.ok(maxPenetration < 1e-6 && maxSlip < 0.000001, `penetration ${maxPenetration}, slip ${maxSlip}`);
  assert.deepEqual([...phases], ['approach', 'board', 'ride', 'alight', 'depart']);
  assert.deepEqual(
    [...owners].sort(),
    ['floor2m', 'escalatorTransition2m', 'LANDING_Lower', 'LANDING_Upper', 'STEP_BODY_00'].sort(),
  );
  assert.ok(
    Math.abs(route.visual.position.z + 6) < 0.00001 && Math.abs(route.visual.position.y - 3) < 0.00001,
  );
  route.restart();
  assert.ok(Math.abs(route.visual.position.z - 6) < 0.00001 && Math.abs(route.visual.position.y) < 0.00001);
  t.diagnostic(
    JSON.stringify({ samples, contacts, unsupported, maxSlip, maxPenetration, duration: route.duration }),
  );
});

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

test('all sewn boundaries and the native zero wrap preserve actual skeleton and machine motion', (t) => {
  const { route, machine } = install();
  t.after(() => route.dispose());
  for (const time of [0, ...boundaries]) {
    const delta = 1e-5;
    route.seek(time - nativeStart - delta);
    const before = poseSignature(machine, route.visual);
    route.seek(time - nativeStart + delta);
    const after = poseSignature(machine, route.visual);
    const maxChange = Math.max(...after.map((v, i) => Math.abs(v - before[i])));
    assert.ok(maxChange < 0.0001, `pose jump ${maxChange} at ${time}`);
    const reference = assets.escalator.scene.clone(true),
      mixer = nativeClock(reference, time + delta);
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
});

test('seeking in either direction yields the same poses under a translated and rotated parent', (t) => {
  const a = install(),
    b = install(true);
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
});

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
