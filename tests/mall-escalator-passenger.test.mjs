import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { AnimationMixer, Box3, Group, Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { createEscalatorPassenger } from '../mall-modules-preview/escalator-passenger.js';
import { passengerView } from '../mall-modules-preview/escalator-terminal.js';

async function load(path) {
  const bytes = await readFile(new URL('../models/' + path, import.meta.url));
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  return new GLTFLoader().parseAsync(buffer, '');
}
const [machineSource, visitorSource] = await Promise.all([
  load('escalator/exports/optimized.glb'),
  load('gjh-mall-visitor/exports/gjh-mall-visitor.glb'),
]);
function install(machine = machineSource.scene.clone(true)) {
  return createEscalatorPassenger({
    machine,
    clips: machineSource.animations,
    avatar: visitorSource.scene,
    avatarClips: visitorSource.animations,
  });
}
function near(actual, expected, tolerance = 1e-6) {
  assert.ok(Math.abs(actual - expected) <= tolerance, actual + ' differs from ' + expected);
}
function pose(object) {
  return [...object.position.toArray(), ...object.quaternion.toArray(), ...object.scale.toArray()];
}
function feet(visual) {
  return ['LeftFoot', 'RightFoot'].map((name) => {
    const meshes = [];
    visual.getObjectByName(name).traverse((part) => {
      if (part.isMesh) meshes.push(part);
    });
    assert.ok(meshes.length);
    return meshes;
  });
}
function lowestWorldVertex(meshes) {
  const point = new Vector3();
  const lowest = new Vector3(0, Infinity, 0);
  for (const mesh of meshes) {
    const position = mesh.geometry.getAttribute('position');
    for (let i = 0; i < position.count; i++) {
      point.fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld);
      if (point.y < lowest.y) lowest.copy(point);
    }
  }
  return lowest;
}
function belongsTo(object, parent) {
  for (let item = object; item; item = item.parent) if (item === parent) return true;
  return false;
}
const movingNames = machineSource.animations.map((clip) => clip.tracks[0].name.split('.')[0]);

test('both feet remain on the same native moving tread through the flat ends and incline', (t) => {
  const machine = machineSource.scene.clone(true);
  const ride = install(machine);
  t.after(() => ride.dispose());
  const shoes = feet(ride.visual);
  const supports = [
    'STEP_BODY_00',
    'STEP_BODY_01',
    'STEP_BODY_57',
    'COMB_Lower',
    'COMB_Upper',
    'LANDING_Lower',
    'LANDING_Upper',
  ].map((name) => machine.getObjectByName(name));
  const ray = new Raycaster();
  const up = new Vector3(0, 1, 0),
    down = new Vector3(0, -1, 0);
  let probes = 0,
    maximumFootGap = 0,
    previousY = -Infinity;
  const frames = Math.ceil(ride.duration * 60);
  for (let frame = 0; frame <= frames; frame++) {
    ride.seek((ride.duration * frame) / frames);
    assert.ok(!ride.playing);
    const root = ride.visual.position;
    near(root.x, 0);
    assert.ok(root.y >= previousY - 1e-6, 'one upward trip with no return-loop section');
    previousY = root.y;
    if (frame === 0) near(root.y, 0);
    if (frame === frames) near(root.y, 3);
    for (const geometry of shoes) {
      const foot = lowestWorldVertex(geometry);
      // Cast from above the neighbouring riser as well as the supporting tread.
      ray.set(foot.clone().addScaledVector(up, 0.32), down);
      const contact = ray.intersectObjects(supports, true)[0];
      assert.ok(
        contact && belongsTo(contact.object, supports[0]),
        'sole must land on STEP_BODY_00',
      );
      const gap = Math.abs(foot.y - contact.point.y);
      maximumFootGap = Math.max(maximumFootGap, gap);
      assert.ok(gap < 1e-6, 'sole leaves the crest');
      probes++;
    }
  }
  t.diagnostic(
    JSON.stringify({ nativeClipSeconds: [0.3, 18.1], frames: frames + 1, probes, maximumFootGap }),
  );
});

test('the follow camera sees the front of both shoes on the lower flat, incline and upper flat', () => {
  const machine = machineSource.scene.clone(true);
  const ride = install(machine);
  const ray = new Raycaster();
  for (const seconds of [0, ride.duration / 2, ride.duration]) {
    ride.seek(seconds);
    const target = ride.visual.localToWorld(new Vector3(...passengerView.target));
    const direction = new Vector3(...passengerView.direction).transformDirection(ride.visual.matrixWorld);
    for (const aspect of [2.1, .74]) {
      const vertical = 17 * Math.PI / 180;
      const horizontal = Math.atan(Math.tan(vertical) * aspect);
      const distance = passengerView.radius / Math.sin(Math.min(vertical, horizontal));
      const camera = target.clone().addScaledVector(direction, distance);
      for (const name of ['LeftFoot', 'RightFoot']) {
        const foot = ride.visual.getObjectByName(name);
        const toe = new Box3().setFromObject(foot, true).getCenter(new Vector3());
        toe.z -= .08;
        ray.set(camera, toe.sub(camera).normalize());
        const hit = ray.intersectObject(machine, true)[0];
        assert.ok(hit && belongsTo(hit.object, foot), name + ' should be visible at ' + seconds + ' s');
      }
    }
  }
  ride.dispose();
});

test('all 58 native steps, both handrails and the visitor idle clip sample deterministically', (t) => {
  const machine = machineSource.scene.clone(true),
    reference = machineSource.scene.clone(true);
  const idleReference = visitorSource.scene.clone(true);
  const mechanism = new AnimationMixer(reference),
    idle = new AnimationMixer(idleReference);
  for (const clip of machineSource.animations) mechanism.clipAction(clip).play();
  const idleClip = visitorSource.animations.find((clip) => clip.name === 'idle');
  idle.clipAction(idleClip).play();
  const idleNames = [...new Set(idleClip.tracks.map((track) => track.name.split('.')[0]))];
  const ride = install(machine);
  t.after(() => {
    ride.dispose();
    mechanism.stopAllAction();
    idle.stopAllAction();
  });
  assert.equal(movingNames.length, 60);
  assert.equal(ride.duration, 17.8);
  assert.equal(ride.visual.parent, machine);
  assert.equal(ride.visual.rotation.y, Math.PI);
  assert.deepEqual(ride.visual.scale.toArray(), [1, 1, 1]);
  for (const seconds of [0, 8.1, 17.8, 1.2, 12.75, 8.1]) {
    ride.seek(seconds);
    mechanism.setTime(0.3 + seconds);
    idle.setTime(seconds);
    for (const name of movingNames) {
      assert.deepEqual(
        pose(machine.getObjectByName(name)),
        pose(reference.getObjectByName(name)),
        name,
      );
    }
    for (const name of idleNames) {
      assert.deepEqual(
        pose(ride.visual.getObjectByName(name)),
        pose(idleReference.getObjectByName(name)),
        name,
      );
    }
    const step = reference.getObjectByName('STEP_00');
    const actual = ride.visual.position;
    near(actual.x, step.position.x);
    near(actual.y, step.position.y + 0.2);
    near(actual.z, step.position.z + 0.24);
  }
});

test('playback is opt-in, scrub and restart pause, and disposal restores the original installed clone', () => {
  const machine = machineSource.scene.clone(true);
  const store = (object) =>
    Object.fromEntries(movingNames.map((name) => [name, pose(object.getObjectByName(name))]));
  const previous = store(machine);
  const idleBody = pose(visitorSource.scene.getObjectByName('Body'));
  const parent = new Group();
  parent.position.set(4, 2, 7);
  parent.rotation.y = 0.7;
  parent.add(machine);
  machine.position.set(-1, 0.3, 2);
  machine.rotation.y = -0.25;
  const ride = install(machine);
  ride.update(2);
  near(ride.time, 0);
  assert.equal(ride.playing, false);
  ride.play();
  ride.update(0.4);
  ride.update(0.6);
  near(ride.time, 1);
  const carried = machine.getObjectByName('STEP_00').localToWorld(new Vector3(0, 0.2, 0.24));
  near(carried.distanceTo(ride.visual.getWorldPosition(new Vector3())), 0);
  ride.pause();
  ride.update(2);
  near(ride.time, 1);
  ride.play();
  ride.seek(12);
  ride.update(1);
  near(ride.time, 12);
  assert.equal(ride.playing, false);
  ride.play();
  ride.update(99);
  near(ride.time, ride.duration);
  assert.equal(ride.playing, false);
  ride.play();
  near(ride.time, 0);
  assert.equal(ride.playing, true);
  ride.seek(-3);
  near(ride.time, 0);
  ride.seek(100);
  near(ride.time, ride.duration);
  ride.restart();
  near(ride.time, 0);
  assert.equal(ride.playing, false);
  assert.throws(() => ride.seek(NaN), RangeError);
  ride.play();
  assert.throws(() => ride.update(-1), RangeError);
  ride.seek(9.2);
  ride.dispose();
  ride.dispose();
  ride.play();
  ride.update(2);
  assert.equal(ride.playing, false);
  assert.equal(ride.visual.parent, null);
  assert.deepEqual(store(machine), previous);
  assert.deepEqual(pose(visitorSource.scene.getObjectByName('Body')), idleBody);
});
