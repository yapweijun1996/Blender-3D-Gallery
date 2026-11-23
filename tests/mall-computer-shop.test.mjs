import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { AnimationMixer, Box3, LoopOnce, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { assembleComputerShop, computerPaths } from '../mall-modules-preview/computer-shop.js';
import { roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor, walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
let lidClip;
for (const [id, path] of Object.entries({ ...roomAssetPaths, ...computerPaths })) {
  const gltf = await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
  sources[id] = gltf.scene;
  if (id === 'laptop') lidClip = gltf.animations.find(clip => clip.name === 'MOVABLE_LidAction');
}
const vector = (x, y, z) => new Vector3(x, y, z);
const demoView = { x: -.02, z: 1.25 };
const shelfView = { x: 1.30, z: -1.53 };
const rightAisle = { x: 1.5, z: 1.25 };
const route = [
  roomArrival, demoView, rightAisle, { x: 1.5, z: -1.53 }, shelfView,
  { x: -2.19, z: -1.53 }, { x: -2.19, z: 1.25 }, demoView, roomArrival,
];

function showroom() {
  const room = assembleComputerShop(sources);
  room.poseDoors(90);
  room.group.updateMatrixWorld(true);
  const fixtures = {};
  room.group.traverse(object => {
    const id = object.userData.moduleId;
    if (id in computerPaths) {
      assert.ok(!fixtures[id], 'duplicate fixture ' + id);
      assert.deepEqual(object.scale.toArray(), [1, 1, 1]);
      fixtures[id] = object;
    }
  });
  assert.ok(fixtures.laptop && fixtures.tvTable && fixtures.securityTether && fixtures.electronicsShelf);
  return { ...room, ...fixtures, body: fixtures.tvTable.parent };
}

function rays(objects, origin, direction, length) {
  return new Raycaster(origin, direction, 0, length).intersectObjects(objects, true);
}

function probeContact(upper, supports, location) {
  const world = upper.localToWorld(location);
  const above = world.clone(), below = world.clone();
  above.y += .004;
  below.y -= .004;
  const lowerFace = rays([upper], below, vector(0, 1, 0), .008)[0];
  const support = rays(supports, above, vector(0, -1, 0), .008)[0];
  assert.ok(lowerFace && support, upper.userData.moduleId + ' needs two mating surfaces');
  assert.ok(Math.abs(lowerFace.point.y - world.y) < 1e-6 &&
    Math.abs(lowerFace.point.y - support.point.y) < 1e-6, 'the actual surfaces meet');
  return support.object;
}

function owns(object, id) {
  for (let part = object; part; part = part.parent) {
    if (part.userData.moduleId === id) return true;
  }
  return false;
}

function sight(room, viewer, target) {
  const eye = vector(viewer.x, 1.55, viewer.z);
  const toward = target.clone().sub(eye);
  const length = toward.length();
  return rays([room.body], eye, toward.normalize(), length + .025);
}

async function install(t, room) {
  const scene = await measureWallContact(room.body);
  t.after(() => scene.dispose());
  return { ...scene, visitor: createCollisionWorld(room.group) };
}

test('desk and shelf stand on their feet, with the laptop and both tether soles on their assigned surfaces', () => {
  const room = showroom();
  const floors = room.body.children.filter(part => part.userData.moduleId === 'floor2m');
  for (const [fixture, dx, dz] of [[room.tvTable, .87, .37], [room.electronicsShelf, .50, .15]]) {
    for (const x of [-dx, dx]) for (const z of [-dz, dz]) {
      probeContact(fixture, floors, vector(x, 0, z));
    }
  }
  for (const x of [-.14, 0, .14]) for (const z of [-.095, 0, .095]) {
    probeContact(room.laptop, [room.tvTable], vector(x, 0, z));
  }
  for (const x of [-.013, 0, .013]) for (const z of [-.012, .012]) {
    probeContact(room.securityTether, [room.tvTable], vector(x, 0, z));
  }
  for (const x of [-.007, 0, .007]) for (const z of [-.005, .005]) {
    const support = probeContact(room.securityTether, [room.laptop], vector(-.15 + x, .02, z));
    assert.equal(support.name, 'BASE_Chassis', 'the sensor bonds to the fixed chassis');
  }

  // A reversed tether still touches the desk at its reel, but leaves its sensor unsupported.
  room.securityTether.rotateY(Math.PI);
  room.group.updateMatrixWorld(true);
  probeContact(room.securityTether, [room.tvTable], vector(0, 0, 0));
  const sensor = room.securityTether.localToWorld(vector(-.15, .02, 0));
  const lower = rays([room.securityTether], vector(sensor.x, sensor.y - .003, sensor.z), vector(0, 1, 0), .005)[0];
  const below = rays([room.laptop, room.tvTable], sensor.clone().add(vector(0, .002, 0)), vector(0, -1, 0), .05)[0];
  assert.ok(lower && below && owns(below.object, 'tvTable'));
  assert.ok(Math.abs(lower.point.y - below.point.y - .02) < 1e-6, 'reversal leaves a 20 mm air gap');
});

test('the original laptop lid clears the installed tether throughout its native clip', t => {
  const { laptop, securityTether } = showroom();
  const chassis = laptop.getObjectByName('BASE_Chassis');
  const lid = laptop.getObjectByName('MOVABLE_Lid');
  assert.ok(chassis && lid && lidClip);
  const tetherBounds = new Box3().setFromObject(securityTether, true);
  const baseBounds = new Box3().setFromObject(chassis, true);
  const up = vector(0, 1, 0), down = vector(0, -1, 0);
  // Sample the real upper surface of the cable and sensor where they cross the chassis.
  const columns = [];
  for (let x = Math.max(tetherBounds.min.x, baseBounds.min.x); x < baseBounds.max.x; x += .003) {
    for (let z = tetherBounds.min.z; z < tetherBounds.max.z; z += .003) {
      const start = vector(x, tetherBounds.max.y + .01, z);
      const top = rays([securityTether], start, down, .1)[0];
      if (top && rays([chassis], start, down, .1)[0]) columns.push(top.point);
    }
  }
  assert.ok(columns.length > 50);
  const mixer = new AnimationMixer(laptop);
  const action = mixer.clipAction(lidClip);
  action.setLoop(LoopOnce, 1);
  action.clampWhenFinished = true;
  action.play();
  let minimum = Infinity, hits = 0;
  const steps = Math.ceil(lidClip.duration * 120);
  for (let step = 0; step <= steps; step++) {
    mixer.setTime(lidClip.duration * step / steps);
    laptop.updateMatrixWorld(true);
    for (const top of columns) {
      // Start beneath both devices so a lid passing through the sensor yields a negative gap.
      const underside = rays([lid], vector(top.x, baseBounds.min.y - .01, top.z), up, .5)[0];
      if (underside) {
        minimum = Math.min(minimum, underside.point.y - top.y);
        hits++;
      }
    }
  }
  mixer.stopAllAction();
  mixer.uncacheRoot(laptop);
  assert.ok(hits > columns.length && Number.isFinite(minimum));
  assert.ok(minimum > .010, 'sampled clearance in metres: ' + minimum);
  t.diagnostic(JSON.stringify({ poses: steps + 1, columns: columns.length, hits, minimumMetres: minimum }));
});

test('a shopper sees the open laptop and tether and reaches the glass-front electronics display and exit', async t => {
  const room = showroom();
  const scene = await install(t, room);
  const journey = walk(scene, route);
  const capsule = new RAPIER.Capsule(BODY.height / 2 - BODY.radius, BODY.radius);
  for (let i = 1; i < route.length; i++) {
    const start = route[i - 1], end = route[i];
    assert.equal(scene.sweep(start, end.x - start.x, end.z - start.z, capsule), null);
  }

  const screen = sight(room, demoView, room.laptop.localToWorld(vector(0, .15, -.071)))[0];
  assert.equal(screen?.object.name, 'LID_Display');
  const keys = sight(room, demoView, room.laptop.localToWorld(vector(-.003, .029, .025)))[0];
  assert.match(keys?.object.name ?? '', /KEYBOARD/);
  for (const [x, y] of [[0, .002], [-.15, .023]]) {
    const face = sight(room, demoView, room.securityTether.localToWorld(vector(x, y, 0)))[0];
    assert.ok(owns(face?.object, 'securityTether'), 'the customer can see both tether endpoints');
    const local = room.securityTether.worldToLocal(face.point.clone());
    assert.ok(Math.hypot(local.x - x, local.z) < .035, 'the sightline reaches the intended endpoint');
  }

  const cabinet = sight(room, shelfView, room.electronicsShelf.localToWorld(vector(-.253, .905, .03)));
  assert.ok(cabinet.length && owns(cabinet[0].object, 'electronicsShelf') && cabinet[0].object.material.transparent);
  const tablet = cabinet.find(hit => !hit.object.material.transparent);
  assert.ok(tablet && owns(tablet.object, 'electronicsShelf'));
  assert.ok(tablet.distance > cabinet[0].distance + .12, 'the tablet sits behind the front glass');
  assert.ok(tablet.point.distanceTo(room.electronicsShelf.localToWorld(vector(-.253, .905, .03))) < .025);

  const contacts = [];
  for (const [start, id] of [[demoView, 'tvTable'], [shelfView, 'electronicsShelf']]) {
    const hit = scene.sweep(start, 0, -1);
    assert.equal(hit?.module, id);
    assert.equal(scene.sweep(start, 0, -1, capsule)?.module, id);
    const stop = { ...start };
    const reason = scene.visitor.move(stop, 0, -1);
    assert.ok(reason && reason !== 'Floor edge');
    const margin = hit.fraction - (start.z - stop.z);
    assert.ok(margin >= -.0001 && margin <= BODY.step + .002);
    checkFloor(scene, stop);
    contacts.push({ fixture: id, meshContact: hit.fraction, controllerMargin: margin });
  }
  t.diagnostic(JSON.stringify({ journey, contacts }));
});

test('misplacing the demo table in the right aisle blocks the route to the electronics shelf', async t => {
  const room = showroom();
  for (const fixture of [room.tvTable, room.laptop, room.securityTether]) fixture.position.x += 1.3;
  room.group.updateMatrixWorld(true);
  const scene = await install(t, room);
  const start = rightAisle;
  assert.equal(scene.sweep(start, 0, shelfView.z - start.z)?.module, 'tvTable');
  const stop = { ...start };
  const reason = scene.visitor.move(stop, 0, shelfView.z - start.z);
  assert.ok(reason && reason !== 'Floor edge' && stop.z > 1);
  checkFloor(scene, stop);
});
