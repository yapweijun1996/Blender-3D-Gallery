import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { AnimationMixer, LoopOnce, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { assembleBakeryShop, bakeryPaths } from '../mall-modules-preview/bakery-shop.js';
import { roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
let cabinetClip;
for (const [id, path] of Object.entries({ ...roomAssetPaths, ...bakeryPaths })) {
  const { scene, animations } = await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
  sources[id] = scene;
  if (id === 'foodCabinet') cabinetClip = animations[0];
}
const point = (x, y, z) => new Vector3(x, y, z);
const up = point(0, 1, 0), down = point(0, -1, 0);
const pickup = { x: -.11, z: .56 }, glass = { x: -1.80, z: .56 }, staff = { x: -1.82, z: -1.92 };

function bakery() {
  const room = assembleBakeryShop(sources);
  room.poseDoors(90);
  room.group.updateMatrixWorld(true);
  const modules = {};
  room.group.traverse(obj => {
    if (obj.userData.moduleId in bakeryPaths) modules[obj.userData.moduleId] = obj;
  });
  assert.equal(Object.keys(modules).length, 4);
  return { ...room, ...modules, body: room.tongs.parent };
}

function hit(object, origin, direction, length) {
  return new Raycaster(origin, direction, 0, length).intersectObject(object, true)[0];
}

function support(upper, lower, localPoint) {
  const world = upper.localToWorld(localPoint);
  const bottom = hit(upper, world.clone().addScaledVector(down, .001), up, .002);
  const top = hit(lower, world.clone().addScaledVector(up, .001), down, .002);
  assert.ok(bottom && top && bottom.point.distanceTo(top.point) < 1e-6,
    'paired triangles must meet at ' + world.toArray());
  return [bottom.object.material.name, top.object.material.name];
}

test('the open toast rack sits on the worktop and its upper tray supports the spring bend and both jaws', () => {
  const room = bakery();
  assert.equal(room.inspection.object, room.servingTongs);
  assert.equal(room.inspection.label, 'Inspect serving tongs');
  for (const key of Object.keys(bakeryPaths)) assert.deepEqual(room[key].scale.toArray(), [1, 1, 1]);
  for (const x of [-.25, 0, .25]) for (const z of [-.14, 0, .14]) {
    assert.equal(support(room.toastRack, room.serviceCounter, point(x, 0, z))[1], 'Warm pale solid worktop');
  }
  for (const [x, z, material] of [[-.1, 0, /stainless/i], [.08, -.0173, /pastry tips/i], [.08, .0173, /pastry tips/i]]) {
    for (const dx of [-.00025, .00025]) for (const dz of [-.00025, .00025]) {
      const [base, tray] = support(room.tongs, room.toastRack, point(x + dx, 0, z + dz));
      assert.match(base, material);
      assert.equal(tray, 'Tray stainless');
    }
  }
  const eye = point(pickup.x, 1.55, pickup.z);
  for (const [x, z] of [[-.097, 0], [.082, -.0173], [.082, .0173]]) {
    const target = room.tongs.localToWorld(point(x, .012, z));
    const direction = target.clone().sub(eye);
    const length = direction.length();
    const first = hit(room.body, eye, direction.normalize(), length + .012);
    assert.ok(first && /stainless|pastry tips/i.test(first.object.material.name), 'customer sees the bend and both jaws');
  }

  // Move the utensil into the occupied toast row. Its bearing plane now cuts through a portion.
  room.tongs.position.z -= .102;
  room.group.updateMatrixWorld(true);
  const column = room.tongs.localToWorld(point(.020, 0, .0135));
  const above = column.clone().addScaledVector(up, .10);
  const gripLow = hit(room.tongs, column.clone().addScaledVector(down, .001), up, .04);
  const gripHigh = hit(room.tongs, above, down, .11);
  const breadLow = hit(room.toastRack, column.clone().addScaledVector(up, .0005), up, .035);
  const breadHigh = hit(room.toastRack, above, down, .11);
  assert.ok(gripLow && gripHigh && /grip|stainless/i.test(gripHigh.object.material.name));
  assert.ok(breadLow && breadHigh && /crust/i.test(breadLow.object.material.name));
  const overlap = Math.min(gripHigh.point.y, breadHigh.point.y) - Math.max(gripLow.point.y, breadLow.point.y);
  assert.ok(overlap > .010, 'the displaced grip intersects more than 10 mm of toast');
});

test('the left rear service aperture uses the cabinet’s native open pose while front and right glass remain in place', () => {
  const room = bakery();
  const cabinet = room.foodCabinet;
  const door = cabinet.getObjectByName('MOVABLE_RearDoor');
  const installed = door.position.clone();
  const ray = (x, z, sign) => hit(cabinet, cabinet.localToWorld(point(x, 1.11, z)), point(0, 0, sign), .81);
  assert.equal(ray(-.32, -.85, 1), undefined);
  assert.equal(ray(.285, -.85, 1).object.material.name, 'Clear glass alpha');
  assert.equal(ray(-.32, .75, -1).object.name, 'GLASS_Front');
  const upperTray = hit(cabinet, cabinet.localToWorld(point(-.32, 1.11, -.16)), down, .07);
  assert.equal(upperTray.object.name, 'DISPLAY_Tray001');
  const mixer = new AnimationMixer(cabinet);
  const action = mixer.clipAction(cabinetClip);
  action.setLoop(LoopOnce, 1);
  action.clampWhenFinished = true;
  action.play();
  for (const [time, open] of [[0, false], [1.25, true], [2.5, false]]) {
    mixer.setTime(time);
    room.group.updateMatrixWorld(true);
    if (open) {
      assert.ok(installed.distanceTo(door.position) < 1e-6);
      assert.equal(ray(-.32, -.85, 1), undefined);
    } else {
      assert.equal(ray(-.32, -.85, 1).object.name, 'DOOR_Glass');
    }
  }
});

test('customer and staff can reach their own sides from the open shop entrance', async t => {
  const room = bakery();
  const measured = await measureWallContact(room.body);
  t.after(() => measured.dispose());
  const scene = { ...measured, visitor: createCollisionWorld(room.group) };
  const shopper = walk(scene, [roomArrival, { x: 0, z: 1.25 }, pickup, glass, pickup,
    { x: 0, z: 1.25 }, roomArrival]);
  const staffRoute = [pickup, { x: 1.87, z: .56 }, { x: 1.87, z: -1.92 }, staff];
  const rearService = walk(scene, [...staffRoute, ...staffRoute.slice(0, -1).toReversed()]);
  const contacts = [];
  for (const [start, dz, id] of [[pickup, -1, 'serviceCounter'], [glass, -1, 'foodCabinet'], [staff, 1, 'foodCabinet']]) {
    const contact = scene.sweep(start, 0, dz);
    assert.equal(contact?.module, id);
    const stop = { ...start };
    const reason = scene.visitor.move(stop, 0, dz);
    assert.ok(reason && reason !== 'Floor edge');
    const margin = contact.fraction - Math.abs(stop.z - start.z);
    assert.ok(margin >= -.0001 && margin <= BODY.step + .004, id + ' mesh clearance ' + margin);
    contacts.push({ id, meshDistance: contact.fraction, controllerMargin: margin });
  }
  t.diagnostic(JSON.stringify({ shopper, rearService, contacts }));
});
