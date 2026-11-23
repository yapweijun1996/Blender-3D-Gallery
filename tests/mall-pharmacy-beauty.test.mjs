import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { assemblePharmacyBeauty, beautyPaths } from '../mall-modules-preview/pharmacy-beauty.js';
import { roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor, walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
for (const [id, path] of Object.entries({ ...roomAssetPaths, ...beautyPaths })) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}

const point = (x, y, z) => new Vector3(x, y, z);
const testerView = { x: -1.28, z: 1.17 };
const pickupView = { x: -.68, z: .12 };
const shelfView = { x: 1.72, z: .65 };
const staffView = { x: -1.50, z: -2.07 };
const displays = [
  roomArrival, { x: 0, z: 1.65 }, { x: -1.28, z: 1.65 }, testerView,
  { x: -.68, z: 1.17 }, pickupView, { x: 1.72, z: .12 }, shelfView,
];
const staffAisle = [shelfView, { x: 1.72, z: -2.07 }, staffView];

function near(actual, expected, label, tolerance = 1e-5) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) <= tolerance,
    label + ': expected ' + expected + ', measured ' + actual);
}

function showroom(angle = 90) {
  const room = assemblePharmacyBeauty(sources);
  room.poseDoors(angle);
  room.group.updateMatrixWorld(true);
  const fixtures = {};
  room.group.traverse(object => {
    const id = object.userData.moduleId;
    if (id in beautyPaths) {
      assert.ok(!fixtures[id], 'exactly one ' + id);
      fixtures[id] = object;
    }
  });
  assert.equal(Object.keys(fixtures).length, 3);
  return { ...room, ...fixtures, body: fixtures.testerBar.parent };
}

// All sight, aperture and support probes intersect transformed GLB triangles.
function firstHit(root, start, end) {
  const direction = end.clone().sub(start);
  const length = direction.length();
  return new Raycaster(start, direction.normalize(), 0, length).intersectObject(root, true)[0];
}

function owner(object) {
  for (let parent = object; parent; parent = parent.parent) {
    if (parent.userData.moduleId) return parent.userData.moduleId;
  }
}

function localHit(root, start, end) {
  return firstHit(root, root.localToWorld(start), root.localToWorld(end));
}

function checkGround(room, fixture, width, depth) {
  const floors = room.body.children.filter(part => part.userData.moduleId === 'floor2m');
  assert.deepEqual(fixture.scale.toArray(), [1, 1, 1]);
  const lowest = new Box3().setFromObject(fixture, true).min.y;
  near(lowest, 0, 'fixture base at finished floor');
  // Points inside each plinth avoid mouldings and bevels at the footprint perimeter.
  for (const x of [-width / 4, 0, width / 4]) {
    for (const z of [-depth / 4, depth / 4]) {
      const base = localHit(fixture, point(x, -.02, z), point(x, .02, z));
      assert.ok(base, fixture.userData.moduleId + ' has a bearing surface');
      const ray = new Raycaster(point(base.point.x, .02, base.point.z), point(0, -1, 0), 0, .05);
      const floor = ray.intersectObjects(floors, true)[0];
      assert.ok(floor);
      near(base.point.y, floor.point.y, 'plinth meets floor surface');
    }
  }
}

async function install(t, room) {
  const geometry = await measureWallContact(room.body);
  t.after(() => geometry.dispose());
  return { ...geometry, visitor: createCollisionWorld(room.group) };
}

test('the three fixtures bear on the floor and both sides of the pickup counter function in place', () => {
  const room = showroom();
  checkGround(room, room.testerBar, .78, .47);
  assert.equal(localHit(room.testerBar, point(0, -.02, .22), point(0, .02, .22)), undefined,
    'under the front overhang the recessed tester plinth does not reach the floor');
  checkGround(room, room.healthShelf, .6, .35);
  checkGround(room, room.pharmacyCounter, 3, .8);

  const throughCounter = (x, height, reverse = false) => {
    const front = point(x, height, pickupView.z);
    const rear = point(x, height, staffView.z);
    return reverse ? firstHit(room.body, rear, front) : firstHit(room.body, front, rear);
  };
  // The customer and staff can see through the central opening just above the pickup tray.
  for (const x of [-1.07, -.68, -.29]) {
    for (const height of [.96, 1.08, 1.19]) {
      assert.equal(throughCounter(x, height), undefined);
      assert.equal(throughCounter(x, height, true), undefined);
    }
  }
  for (const [x, height] of [[-.68, .905], [-.68, 1.215], [-.68, 1.50], [-1.19, 1.06], [-.17, 1.06]]) {
    assert.equal(owner(throughCounter(x, height)?.object), 'pharmacyCounter',
      'the tray, upper glazing/rail and glazed flanks bound the empty opening');
  }

  // Approach the dispensing rack from the reachable rear aisle. A ray passes into
  // the right compartment above the shelf, while its shelf edge stops a lower ray.
  const staffRay = y => firstHit(room.body, point(staffView.x, y, staffView.z), point(staffView.x, y, -.94));
  assert.equal(staffRay(1.08), undefined);
  const shelf = staffRay(1.213);
  assert.equal(owner(shelf?.object), 'pharmacyCounter');
  assert.ok(shelf.point.z < -1.30, 'the rack shelf faces the staff aisle');

  // The health shelf presents actual stock to the customer before its back panel.
  for (const [z, material] of [[.434, /carton/i], [.807, /bottle/i]]) {
    const item = firstHit(room.body, point(shelfView.x, 1.31, z), point(2.79, 1.31, z));
    assert.equal(owner(item?.object), 'healthShelf');
    assert.match(item.object.material.name, material, 'visible stock faces the aisle');
  }
});

test('both sample groups and the inset mirror face the customer, with pigments seated on their cups', () => {
  const room = showroom();
  const eye = point(testerView.x, 1.58, testerView.z);
  const targets = [
    { point: point(-2.186, .8896, 1.346), finish: /lip and powder/i },
    { point: point(-2.186, .8896, .994), finish: /lip and powder/i },
    { point: point(-2.6205, 1.235, 1.17), finish: /silvered mirror/i },
  ];

  function visible(target) {
    const end = target.point.clone().lerp(eye, -.01);
    const hit = firstHit(room.body, eye, end);
    return hit && owner(hit.object) === 'testerBar' &&
      target.finish.test(hit.object.material.name) && hit.point.distanceTo(target.point) < .0001;
  }
  for (const target of targets) assert.ok(visible(target), 'the aisle eye can see ' + target.finish);

  for (const { point: sample } of targets.slice(0, 2)) {
    const hits = new Raycaster(point(sample.x, .90, sample.z), point(0, -1, 0), 0, .04)
      .intersectObject(room.testerBar, true);
    const surface = (material, sign) => hits.find(hit =>
      material.test(hit.object.material.name) &&
      sign * hit.face.normal.clone().transformDirection(hit.object.matrixWorld).y > .99);
    const pigment = surface(/lip and powder/i, -1);
    const cupTop = surface(/metal/i, 1);
    const cupBottom = surface(/metal/i, -1);
    const pocket = surface(/pocket tray/i, 1);
    assert.ok(pigment && cupTop && cupBottom && pocket, 'pigment, cup and pocket have actual horizontal faces');
    near(pigment.point.y, cupTop.point.y, 'the pigment touches the cup');
    near(cupBottom.point.y, pocket.point.y, 'the cup touches the recessed pocket');
    assert.ok(sample.y > pigment.point.y && pigment.point.y > cupBottom.point.y);
  }

  // The same fixed customer viewpoint and targets now look at the cabinet back.
  room.testerBar.rotateY(Math.PI);
  room.group.updateMatrixWorld(true);
  for (const target of targets) assert.ok(!visible(target), 'a reverse installation loses the customer face');
});

test('the normal visitor and independent body sweeps reach both displays, pickup and the staff side', async t => {
  const room = showroom();
  const scene = await install(t, room);
  const customer = walk(scene, [...displays, ...displays.slice(0, -1).toReversed()]);
  const staff = walk(scene, [...staffAisle, ...staffAisle.slice(0, -1).toReversed()]);
  const capsule = new RAPIER.Capsule(BODY.height / 2 - BODY.radius, BODY.radius);
  for (const route of [displays, staffAisle]) {
    for (let i = 1; i < route.length; i++) {
      const start = route[i - 1], end = route[i];
      assert.equal(scene.sweep(start, end.x - start.x, end.z - start.z, capsule), null);
    }
  }

  const contacts = [];
  for (const [start, dx, dz, expected] of [
    [testerView, -1, 0, 'testerBar'], [pickupView, 0, -1, 'pharmacyCounter'],
    [shelfView, 1, 0, 'healthShelf'], [staffView, 0, 1, 'pharmacyCounter'],
  ]) {
    const hit = scene.sweep(start, dx, dz);
    assert.equal(hit?.module, expected);
    assert.equal(scene.sweep(start, dx, dz, capsule)?.module, expected);
    const stop = { ...start };
    const obstruction = scene.visitor.move(stop, dx, dz);
    assert.ok(obstruction && obstruction !== 'Floor edge');
    const margin = hit.fraction - Math.hypot(stop.x - start.x, stop.z - start.z);
    assert.ok(margin >= -.0001 && margin <= BODY.step + .002, 'visitor stops within a movement step of ' + expected + ': ' + margin);
    checkFloor(scene, stop);
    contacts.push({ fixture: expected, meshContact: hit.fraction, controllerMargin: margin });
  }
  t.diagnostic(JSON.stringify({ customer, staff, contacts }));
});

test('a shut door blocks arrival and a stocked shelf misplaced in the staff aisle closes the route', async t => {
  const closed = await install(t, showroom(0));
  assert.equal(closed.sweep(roomArrival, 0, -2.75)?.module, 'door');
  const outside = { ...roomArrival };
  assert.ok(closed.visitor.move(outside, 0, -2.75) && outside.z > 3.13);

  const room = showroom();
  room.healthShelf.position.set(1.72, 0, -.65);
  room.group.updateMatrixWorld(true);
  const obstructed = await install(t, room);
  assert.equal(obstructed.sweep(shelfView, 0, -2.72)?.module, 'healthShelf');
  const stop = { ...shelfView };
  const reason = obstructed.visitor.move(stop, 0, -2.72);
  assert.ok(reason && reason !== 'Floor edge' && stop.z > -.65);
  assert.throws(() => walk(obstructed, staffAisle), /installed mesh obstructs the walking line/);
});
