import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { assembleHomeFurnishings, furnishingPaths } from '../mall-modules-preview/home-furnishings.js';
import { roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor, walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
for (const [id, path] of Object.entries({ ...roomAssetPaths, ...furnishingPaths })) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const up = new Vector3(0,1,0), down = new Vector3(0,-1,0);
function near(a,b,label) {
  assert.ok(Number.isFinite(a) && Math.abs(a-b) < .000001, `${label}: ${a}, expected ${b}`);
}
function showroom(angle = 90) {
  const room = assembleHomeFurnishings(sources);
  room.poseDoors(angle);
  room.group.updateMatrixWorld(true);
  const modules = {};
  room.group.traverse(part => {
    const id = part.userData.moduleId;
    if (id) (modules[id] ??= []).push(part);
  });
  return { ...room, modules, body: modules.door[0].parent };
}
async function install(t, room) {
  const scene = await measureWallContact(room.body);
  t.after(() => scene.dispose());
  return { ...scene, visitor: createCollisionWorld(room.group) };
}

// Probe the centroid of each lowest horizontal triangle. A prop can be
// supported by the cabinet top just as the furniture feet are supported by the floor.
function bearing(item, supports) {
  const base = new Box3().setFromObject(item,true).min.y;
  const a = new Vector3(), b = new Vector3(), c = new Vector3(), centre = new Vector3();
  let triangles = 0;
  item.traverse(mesh => {
    if (!mesh.isMesh) return;
    const geometry = mesh.geometry, positions = geometry.getAttribute('position'), index = geometry.getIndex();
    const count = index?.count ?? positions.count;
    for (let i = 0; i < count; i += 3) {
      for (const [j,v] of [[0,a],[1,b],[2,c]]) {
        v.fromBufferAttribute(positions,index ? index.getX(i+j) : i+j).applyMatrix4(mesh.matrixWorld);
      }
      if ([a,b,c].some(v => Math.abs(v.y-base) > 1e-6)) continue;
      if (Math.abs((b.x-a.x)*(c.z-a.z)-(b.z-a.z)*(c.x-a.x)) < 1e-9) continue;
      centre.copy(a).add(b).add(c).divideScalar(3);
      const low = new Raycaster(new Vector3(centre.x,base-.02,centre.z),up).intersectObject(item,true)[0];
      const top = new Raycaster(new Vector3(centre.x,base+.02,centre.z),down).intersectObjects(supports,true)[0];
      assert.ok(low && top, item.userData.moduleId + ' needs an actual supporting triangle');
      near(low.point.y-top.point.y,0,item.userData.moduleId + ' bearing gap');
      triangles++;
    }
  });
  assert.ok(triangles > 0, item.userData.moduleId + ' needs a tested base');
  return { baseY:base, triangles };
}

const sofaView = {x:-1.1,z:-.70}, diningView = {x:.55,z:.10};
const route = [roomArrival,{x:0,z:1.6},{x:-1.1,z:1.6},sofaView,{x:.55,z:-.70},diningView,
  {x:.55,z:1.6},{x:0,z:1.6},roomArrival];

test('seven installed furnishings retain their native scale and sit on the real floor or cabinet top', t => {
  const { modules } = showroom();
  const items = Object.keys(furnishingPaths).flatMap(id => modules[id]);
  assert.equal(items.length,7);
  assert.equal(modules.diningChair.length,2);
  const contact = [];
  for (const item of items) {
    assert.deepEqual(item.scale.toArray(),[1,1,1]);
    const id = item.userData.moduleId;
    const evidence = bearing(item,id === 'oilLamp' ? modules.sideTable : modules.floor2m);
    near(evidence.baseY,id === 'oilLamp' ? .6225 : 0,'intended support height');
    contact.push({id,...evidence});
  }
  const centre = modules.diningTable[0].position;
  for (const chair of modules.diningChair) {
    const forward = new Vector3(0,0,1).applyQuaternion(chair.quaternion);
    const towardTable = centre.clone().sub(chair.position).normalize();
    assert.ok(forward.dot(towardTable)>.999,'chairs face one another across the table');
  }
  // These display items occupy separate volumes. The lamp and cabinet have a shared contact plane.
  const boxes = items.map(item=>new Box3().setFromObject(item,true));
  for(let i=0;i<boxes.length;i++) for(let j=0;j<i;j++) {
    const overlap=boxes[i].clone().intersect(boxes[j]);
    if (!overlap.isEmpty()) {
      const size=overlap.getSize(new Vector3());
      assert.ok(Math.min(size.x,size.y,size.z)<1e-6,'display objects overlap in volume');
    }
  }
  t.diagnostic(JSON.stringify({contact}));
});

test('a visitor can enter, browse both displays by different aisles and return through the open door', async t => {
  const room = showroom(), scene = await install(t,room);
  const forward = walk(scene,route), reverse = walk(scene,route.toReversed());
  const capsule = new RAPIER.Capsule(BODY.height/2-BODY.radius,BODY.radius);
  for (let i=1; i<route.length; i++) {
    const start=route[i-1], dx=route[i].x-start.x, dz=route[i].z-start.z;
    assert.equal(scene.sweep(start,dx,dz,capsule),null,'capsule clears the same furniture and frames');
  }
  const contacts = [];
  for (const [start,dx,dz,id] of [[sofaView,0,-2,'sofa'],[diningView,2,0,'diningTable']]) {
    const contact=scene.sweep(start,dx,dz);
    assert.equal(contact?.module,id,'the intended piece is in front of its viewing position');
    assert.equal(scene.sweep(start,dx,dz,capsule)?.module,id,'independent capsule contact');
    const end={...start};
    const obstruction=scene.visitor.move(end,dx,dz);
    assert.ok(obstruction && obstruction!=='Floor edge','the visitor stops at the furnishing');
    const clearance=2*contact.fraction-Math.hypot(end.x-start.x,end.z-start.z);
    assert.ok(clearance>=-.0001 && clearance<=BODY.step+.004,'controller stop compared with displayed triangles: '+clearance);
    checkFloor(scene,end);
    contacts.push({id,measuredTravel:2*contact.fraction,stopMargin:clearance});
  }
  t.diagnostic(JSON.stringify({forward,reverse,contacts}));
});

test('the same displays stay behind a closed door and a sofa misplaced in the entrance obstructs the open route', async t => {
  const closed=await install(t,showroom(0));
  assert.equal(closed.sweep(roomArrival,0,-2)?.module,'door');
  const outside={...roomArrival};
  assert.ok(closed.visitor.move(outside,0,-2) && outside.z>3.135);
  const room=showroom();
  const sofa=room.modules.sofa[0];
  sofa.position.set(0,0,1.8);
  room.group.updateMatrixWorld(true);
  const blocked=await install(t,room);
  assert.equal(blocked.sweep(roomArrival,0,-2.8)?.module,'sofa','the displaced real sofa fills the entrance aisle');
  assert.throws(()=>walk(blocked,route),/installed mesh obstructs the walking line/);
  const end={...roomArrival};
  const reason=blocked.visitor.move(end,0,-2.8);
  assert.ok(reason && reason!=='Floor edge' && end.z>1.8);
  checkFloor(blocked,end);
});
