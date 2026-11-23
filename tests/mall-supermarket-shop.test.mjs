import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, PerspectiveCamera, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { assembleSupermarketShop, supermarketPaths } from '../mall-modules-preview/supermarket-shop.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
for (const [id, file] of Object.entries({ ...roomAssetPaths, ...supermarketPaths })) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + file, import.meta.url)))).scene;
}
const bounds = part => new Box3().setFromObject(part, true);
function near(a,b) { assert.ok(Math.abs(a-b) < 1e-6, a+' differs from '+b); }
function shop() {
  const room = assembleSupermarketShop(sources);
  room.poseDoors(90);
  room.group.updateMatrixWorld(true);
  const body = room.inspection.object.parent;
  const parts = Object.groupBy(body.children, part => part.userData.moduleId);
  return { ...room, body, parts };
}
function sight(objects, a, b) {
  const distance = a.distanceTo(b);
  const ray = new Raycaster(a, b.clone().sub(a).normalize(), 0, distance+.00001);
  return ray.intersectObjects(objects,true)[0];
}
function foothold(floors, x, z) {
  const floor = sight(floors,new Vector3(x,.008,z),new Vector3(x,-.008,z));
  assert.ok(floor);
  near(floor.point.y,0);
}

test('six fixed return pads, eight cart wheels and all original fixtures bear on the finished floor', () => {
  const { parts, inspection } = shop();
  const bay = parts.cartReturn[0], floor = parts.floor2m;
  assert.equal(inspection.object,bay);
  assert.equal(inspection.label,'Inspect cart return');
  assert.equal(parts.cart.length,2);
  for (const id of Object.keys(supermarketPaths)) for (const part of parts[id]) {
    assert.deepEqual(part.scale.toArray(),[1,1,1]);
    near(bounds(part).min.y,0);
  }
  for (const x of [-.75,0,.75]) for (const z of [-.5,.5]) {
    const point=bay.localToWorld(new Vector3(x,0,z));
    for (const dx of [-.025,.025]) for (const dz of [-.025,.025]) {
      const v = point.clone().add(new Vector3(dx,-.01,dz));
      const pad = sight([bay],v,v.clone().add(new Vector3(0,.025,0)));
      assert.ok(pad,'pad underside');
      near(pad.point.y,0);
      foothold(floor,v.x,v.z);
    }
  }
  for (const cart of parts.cart) {
    const wheels=[];
    cart.traverse(p=>{ if(p.isMesh && p.name.startsWith('CASTER_Wheel')) wheels.push(p); });
    assert.equal(wheels.length,4);
    for (const wheel of wheels) {
      const box=bounds(wheel), p=box.getCenter(new Vector3());
      near(box.min.y,0); foothold(floor,p.x,p.z);
    }
  }
});

// A swept box encloses every triangle of the translating cart. Clearing each installed
// obstacle's real mesh bounds for the whole segment is a conservative sufficient check.
function firstCartObstacle(cart, body, dx, dz = 0) {
  const rest=bounds(cart);
  const sweep=rest.clone().union(rest.clone().translate(new Vector3(dx,0,dz)));
  for (const fixture of body.children) {
    if (fixture===cart || fixture.userData.moduleId==='floor2m') continue;
    let hit;
    fixture.traverse(mesh=>{
      if (!hit && mesh.isMesh && sweep.intersectsBox(bounds(mesh))) hit=mesh;
    });
    if (hit) return hit;
  }
  return null;
}

test('each parked cart can be pulled completely out and returned while its neighbour stays parked', () => {
  const { parts, body } = shop(), bay=parts.cartReturn[0];
  const mouth=bounds(bay).max.x;
  const carts=parts.cart;
  const laneGap=bounds(carts[1]).min.z-bounds(carts[0]).max.z;
  near(laneGap,.160);
  for (const cart of carts) {
    const origin=cart.position.clone();
    const travel=1.15;
    assert.equal(firstCartObstacle(cart,body,travel),null);
    cart.position.x+=travel; body.updateMatrixWorld(true);
    assert.ok(bounds(cart).min.x>mouth+.18,'even the cart nose clears the bay');
    assert.equal(firstCartObstacle(cart,body,-travel),null);
    cart.position.copy(origin); body.updateMatrixWorld(true);
    assert.ok(firstCartObstacle(cart,body,-.25)?.name.startsWith('Rear_'),'the back stop catches an overrun');
    const towardsDivider = cart === carts[0] ? .37 : -.37;
    assert.ok(firstCartObstacle(cart,body,0,towardsDivider)?.name.startsWith('Divider_'),
      'the centre divider obstructs sideways removal');
  }
});

const route = [roomArrival, [0,1.48],[-1.16,1.42],[-.98,1.42],[-.98,.68],[-1.16,.68],
  [-.45,.68],[.345,.12],[.345,-.70],[.345,-.46],[-1.39,-.46],[-.12,-.46],[0,1.48],roomArrival]
  .map(p=>Array.isArray(p)?{x:p[0],z:p[1]}:p);

test('the shopper passes the security gates, reaches both handles, checkout and stocked gondola, and leaves', async t => {
  const room=shop(), physics=await measureWallContact(room.body);
  t.after(()=>physics.dispose());
  physics.visitor=createCollisionWorld(room.group);
  const forward=walk(physics,route), reverse=walk(physics,route.toReversed());
  const gate=room.parts.securityGate[0], bases=[];
  gate.traverse(p=>{if(p.isMesh && p.name.startsWith('Base'))bases.push(bounds(p));});
  bases.sort((a,b)=>a.min.x-b.min.x);
  assert.equal(bases.length,2);
  near(bases[1].min.x-bases[0].max.x,1.36);
  const centre=gate.position.z;
  for(const x of [-.10,.10]) assert.equal(physics.visitor.obstruction({x,z:centre}),null);
  assert.ok(physics.visitor.obstruction({x:.14,z:centre}));
  const uninstalled=[];
  sources.securityGate.traverse(p=>{if(p.isMesh && p.name.startsWith('Base'))uninstalled.push(bounds(p));});
  uninstalled.sort((a,b)=>a.min.x-b.min.x);
  near(uninstalled[1].min.x-uninstalled[0].max.x,1.12);
  for(const cart of room.parts.cart) {
    const handle=cart.getObjectByName('HANDLE_Grip');
    const point=bounds(handle).getCenter(new Vector3());
    const hit=sight([room.body],new Vector3(-1.16,1.21,point.z),point);
    assert.equal(hit?.object,handle);
  }
  const belt=room.parts.checkout[0].getObjectByName('CONVEYOR_Belt');
  const beltCentre=bounds(belt).getCenter(new Vector3());
  const beltHit=sight([room.body],new Vector3(.345,1.40,beltCentre.z),beltCentre);
  assert.equal(beltHit?.object,belt);
  const shelf=room.parts.gondola[0];
  for(const [x,material] of [[-.46,/PlainPackaging/],[-.1534,/Powdercoat/]]) {
    const item=shelf.localToWorld(new Vector3(x,1.16,.132));
    const hit=sight([room.body],new Vector3(-1.39,1.25,-.46),item);
    assert.match(hit?.object.material.name??'',material);
  }
  assert.equal(physics.visitor.doorTransition(90,0,roomArrival,room.poseDoors),true);
  const outside={...roomArrival};
  assert.ok(physics.visitor.move(outside,0,-2));
  assert.equal(physics.visitor.doorTransition(0,90,roomArrival,room.poseDoors),true);
  const matrix=room.inspection.object.matrixWorld.toArray();
  room.batchStatic(); room.group.updateMatrixWorld(true);
  assert.deepEqual(room.inspection.object.matrixWorld.toArray(),matrix);
  t.diagnostic(JSON.stringify({forward,reverse,visitorDiameter:2*BODY.radius}));
});

test('parked cart baskets leave both raised return symbols visible from the aisle and the inspection view', () => {
  const { body, inspection } = shop(), bay=inspection.object;
  const glyphs=[];
  for (const x of [-.375,.375]) for (const [dx,y] of [[.015,1.120],[-.030,1.107]]) {
    glyphs.push(bay.localToWorld(new Vector3(x+dx,y,-.456)));
  }
  function checkSymbols(eye) {
    for (const p of glyphs) {
      const hit=sight([body],eye,p);
      assert.equal(hit?.object.material.name,'Porcelain return marks');
      assert.ok(hit.point.distanceTo(p)<.012,'the intended sign is visible');
    }
  }
  checkSymbols(new Vector3(-1.16,1.58,1.42));
  for (const aspect of [900/560,390/530]) {
    const camera=new PerspectiveCamera(34,aspect,.01,100), vertical=camera.fov*Math.PI/360;
    const distance=inspection.radius/Math.sin(Math.min(vertical,Math.atan(Math.tan(vertical)*aspect)));
    const target=bay.localToWorld(new Vector3(...inspection.target));
    const direction=new Vector3(...inspection.direction).transformDirection(bay.matrixWorld);
    camera.position.copy(target).addScaledVector(direction,distance);
    camera.lookAt(target); camera.updateMatrixWorld();
    checkSymbols(camera.position);
    const feet=[[-.80,-.55],[-.80,.55],[.80,-.55],[.80,.55]];
    const important=[...glyphs,...feet.map(([x,z])=>bay.localToWorld(new Vector3(x,0,z)))];
    for (const p of important) {
      const ndc=p.clone().project(camera);
      assert.ok(Math.abs(ndc.x)<.98 && Math.abs(ndc.y)<.98,'inspection crops a sign or mounting plate');
    }
  }
});
