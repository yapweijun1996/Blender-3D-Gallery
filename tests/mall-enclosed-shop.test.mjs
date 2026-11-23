import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import RAPIER from '@dimforge/rapier3d-compat';
import { Box3, Raycaster, Vector3 } from 'three';
import { BODY, createCollisionWorld } from '../docs/verification/mall-corridor/collision.js';
import { assembleRoom, roomArrival, roomAssetPaths } from '../mall-modules-preview/room-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor, walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const sources = {};
for (const [id, path] of Object.entries(roomAssetPaths)) {
  sources[id] = (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const up = new Vector3(0,1,0), down = new Vector3(0,-1,0), inside = new Vector3(0,0,-1), outside = new Vector3(0,0,1);
function near(a,b,label) {
  assert.ok(Number.isFinite(a) && Math.abs(a - b) <= 1e-6, `${label}: ${a}, expected ${b}`);
}
function room(angle = 0) {
  const result = assembleRoom(sources);
  result.poseDoors(angle);
  result.group.updateMatrixWorld(true);
  const modules = {};
  result.group.traverse(part => {
    const id = part.userData.moduleId;
    if (id) (modules[id] ??= []).push(part);
  });
  const walls = [...modules.wall2m, ...modules.wallCorner2m];
  const [door] = modules.door, [header] = modules.doorHeader2m;
  return { ...result, modules, walls, door, header, body: door.parent };
}
function ray(objects, x, y, z, dir) {
  return new Raycaster(new Vector3(x,y,z), dir).intersectObjects(objects,true);
}
function hit(objects,x,y,z,dir) {
  const h = ray(objects,x,y,z,dir)[0];
  assert.ok(h, `missing surface from (${x},${y},${z}) along ${dir.toArray()}`);
  return h;
}
async function physics(t, r) {
  // The separate roof is above the 1.8 m visitor. It is still included in
  // the normal controller here; the independent sweeps use the body triangles.
  const scene = await measureWallContact(r.body);
  t.after(() => scene.dispose());
  return { ...scene, visitor: createCollisionWorld(r.group) };
}
const bodyCapsule = () => new RAPIER.Capsule(BODY.height / 2 - BODY.radius, BODY.radius);

test('the six-metre shop has six paired wall joints, a central 2 m opening and floors on both sides', () => {
  const { modules, walls, door } = room();
  assert.equal(modules.floor2m.length,25);
  assert.equal(modules.wall2m.length,3);
  assert.equal(modules.wallCorner2m.length,4);
  const ends = new Map();
  for (const wall of walls) {
    assert.deepEqual(wall.scale.toArray(),[1,1,1]);
    wall.traverse(node => {
      if (!node.name.startsWith('CONNECTOR_')) return;
      const p = node.getWorldPosition(new Vector3());
      near(p.y, 0, 'ground connector');
      const k = [Math.round(p.x), Math.round(p.z)].join(',');
      near(p.x,Math.round(p.x),'connector X'); near(p.z,Math.round(p.z),'connector Z');
      ends.set(k,(ends.get(k)||0)+1);
    });
  }
  for (const key of ['-1,-3','1,-3','-3,-1','-3,1','3,-1','3,1']) assert.equal(ends.get(key),2,key);
  for (const key of ['-1,3','1,3']) assert.equal(ends.get(key),1,key);
  assert.equal(ends.size,8);
  for (const x of [-.99,0,.99]) assert.equal(ray(walls,x,1.3,4,inside).filter(h => h.point.z > 2.8).length,0,'clear front rough opening');
  // All 25 native slabs supply the interior floor and the approach outside every wall.
  for (const x of [-4,-2,0,2,4]) for (const z of [-4,-2,0,2,4]) {
    const p = modules.floor2m.find(f => f.position.x === x && f.position.z === z);
    assert.ok(p); assert.match(p.name,/^Floor_\d+$/);
    const b = new Box3().setFromObject(p,true);
    near(b.min.y,-.10,'floor bottom'); near(b.max.y,0,'floor top');
    near(hit([p],x+.21,.4,z+.17,down).point.y,0,'real triangle support');
  }
  for (const t of [-2.6,-1.3,-.3,.3,1.3,2.6]) for (const side of [-3,3]) {
    for (const offset of [-.06,0,.06]) for (const [x,z] of [[side+offset,t],[t,side+offset]]) {
      if (z > 2.9 && Math.abs(x)<1) continue;
      const base = hit(walls,x,-.3,z,up).point.y;
      const floor = hit(modules.floor2m,x,.3,z,down).point.y;
      near(base-floor,0,'bearing under both the inside and outside halves of the wall');
    }
  }
  assert.deepEqual(door.position.toArray(),[0,0,3.135]);
  assert.deepEqual(door.scale.toArray(),[1,1,1]);
});

test('the face-mounted frame and stepped header close the front interfaces at their real surfaces', () => {
  const { door, header, walls } = room();
  const frame = door.getObjectByName('FRAME_Fixed');
  const fb = new Box3().setFromObject(frame,true), hb = new Box3().setFromObject(header,true);
  near(fb.min.x,-1.05,'frame west'); near(fb.max.x,1.05,'frame east');
  near(fb.min.z,3.075,'frame back'); near(fb.max.z,3.195,'frame front');
  near(hb.min.y,2.4,'head base'); near(hb.max.y,2.8,'wall/cassette datum');
  near(hb.min.z,2.925,'head inside'); near(hb.max.z,3.195,'front projection');
  for (const s of [-1,1]) {
    for (const dx of [.008,.025,.042]) for (const y of [.35,1.2,2.18,2.57,2.71]) {
      const x = s*(1+dx);
      const outer = hit(walls,x,y,3.5,inside).point.z;
      const backOfFacing = hit([y<2.4?frame:header],x,y,2.6,outside).point.z;
      near(backOfFacing-outer,0,'50 mm face mounting overlap');
    }
    for (const y of [2.42,2.6,2.78]) for (const z of [2.95,3,3.05]) {
      const dir = new Vector3(s,0,0);
      const openingEdge = hit(walls,0,y,z,dir).point.x;
      const headerEdge = hit([header],1.5*s,y,z,dir.clone().negate()).point.x;
      near(headerEdge-openingEdge,0,'header core butts against rough opening');
    }
  }
  for (const x of [-.91,-.4,0,.4,.91]) for (const z of [3.081,3.131,3.18]) {
    const frameTop = hit([frame],x,2.7,z,down);
    const headerBottom = hit([header],x,2.18,z,up);
    near(headerBottom.point.y-frameTop.point.y,0,'frame top to header soffit');
  }
  for (const x of [-.57,.57]) {
    near(hit([header],x,2.18,2.97,up).point.y,2.4,'inside soffit spans over the opening');
    assert.equal(ray([frame],x,2.7,2.97,down).length,0,'no frame below the inner part of the header');
  }
  // A central ray fits through the original 12 mm gap between the two closed glass leaves.
  assert.equal(ray([door],0,1.38,4,inside).length,0);
  for (const x of [-.2,.2]) assert.ok(hit([door],x,1.38,4,inside));
});

test('moving the 2.10 m fixed frame back into the 2 m opening makes both jambs intersect the wall', () => {
  const {door, walls} = room();
  const frame = door.getObjectByName('FRAME_Fixed');
  function overlap(x) {
    const front = objects => hit(objects,x,1.2,3.6,inside).point.z;
    const back = objects => hit(objects,x,1.2,2.6,outside).point.z;
    return Math.min(front([frame]),front(walls)) - Math.max(back([frame]),back(walls));
  }
  for (const x of [-1.025,1.025]) near(overlap(x),0,'correct frame only touches wall');
  door.position.z=3;
  door.updateMatrixWorld(true);
  for (const x of [-1.025,1.025]) near(overlap(x),.12,'centred frame overlaps the wall through its full jamb depth');
});

test('all roof cells are present, the perimeter grid meets the wall and header, and the panels are recessed', () => {
  const r = room();
  assert.equal(r.roof.visible,false);
  r.setRoofVisible(true); assert.equal(r.roof.visible,true);
  assert.equal(r.modules.ceiling.length,25);
  const b = new Box3().setFromObject(r.roof,true);
  near(b.min.x,-3,'roof west'); near(b.max.x,3,'roof east'); near(b.min.z,-3,'roof back'); near(b.max.z,3,'roof front');
  near(b.min.y,2.8,'underside'); near(b.max.y,3.16,'suspension');
  for (const cell of r.modules.ceiling) {
    const {x,z}=cell.position;
    for (const dx of [-.3,.3]) for (const dz of [-.3,.3]) {
      near(hit([cell],x+dx,2.64,z+dz,up).point.y,2.808,'panel recess');
    }
  }
  const supporting = [...r.walls,r.header];
  for (let i=0;i<=60;i++) {
    const t=-2.9999+5.9998*i/60;
    for (const s of [-2.994,2.994]) for (const [x,z] of [[t,s],[s,t]]) {
      const rail=hit([r.roof],x,2.65,z,up);
      assert.match(rail.object.name,/GRID_/);
      near(rail.point.y-hit(supporting,x,2.95,z,down).point.y,0,'perimeter grid closes onto the shop');
    }
  }
  // The roof ends on the centrelines, leaving the outer part of the wall cap visible.
  assert.equal(ray([r.roof],2.5,2.65,3.045,up).length,0);
  near(hit(r.walls,2.5,2.95,3.045,down).point.y,2.8,'exposed wall cap');
  const headAtGate = hit([r.header],.35,2.6,3.5,inside);
  assert.ok(headAtGate.point.z > 3.075,'front casing closes the area above the frame');
  r.header.removeFromParent();
  assert.equal(ray([...r.walls,r.door],.35,2.6,3.5,inside).filter(h=>h.point.z>2.8).length,0,
    'without the 400 mm header the shop front has an opening above the door');
  const outer = hit([r.roof],.35,2.65,2.994,up);
  const air = ray([...r.walls,r.door],.35,2.95,2.994,down);
  assert.ok(outer && air.length===0,'without the header the rear of the lintel area is open');
  r.setRoofVisible(false); assert.equal(r.roof.visible,false);
});

test('closed shop encloses the visitor in every sampled direction and the four sides stop the normal controller', async t => {
  const r = room();
  const scene = await physics(t,r), capsule=bodyCapsule();
  const counts = {};
  for (let a=0;a<360;a+=5) {
    const x=5*Math.sin(a*Math.PI/180), z=5*Math.cos(a*Math.PI/180);
    for (const shape of [undefined,capsule]) {
      const h=scene.sweep({x:0,z:0},x,z,shape);
      assert.ok(['wall2m','wallCorner2m','door'].includes(h?.module),'physical enclosure at '+a+' degrees');
      assert.ok(h.fraction>.4 && h.fraction<.8,'visitor reaches the shell from the clear centre');
      counts[h.module]=(counts[h.module]||0)+1;
    }
  }
  for (const [x,z,dx,dz,id] of [[0,-1.5,0,-3,'wall2m'],[-1.5,0,-3,0,'wall2m'],[1.5,0,3,0,'wall2m'],
    [1.8,1.5,0,3,'wallCorner2m'],[0,1.5,0,3,'door']]) {
    const p={x,z}; const h=scene.sweep(p,dx,dz);
    assert.equal(h?.module,id);
    const stop=scene.visitor.move(p,dx,dz);
    assert.ok(stop && stop!=='Floor edge','shop surface limits movement');
    const margin=3*h.fraction-Math.hypot(p.x-x,p.z-z);
    assert.ok(margin>=-.0001 && margin<=BODY.step+.0001,'controller stops at the actual mesh');
    checkFloor(scene,p);
  }
  t.diagnostic(JSON.stringify({ closedDirections:72, cylinderAndCapsuleContacts:counts }));
});

test('open doorway admits both directions; a body midway through the swing restores both hinges', async t => {
  const r = room(90), scene = await physics(t,r);
  const hinges = ['HINGE_Left','HINGE_Right'].map(k=>r.door.getObjectByName(k));
  const angles = () => hinges.map(h=>Math.round(h.rotation.y*180/Math.PI) || 0);
  assert.deepEqual(angles(),[-90,90]);
  const closed = await physics(t, room(0));
  const blocked = { ...roomArrival };
  assert.equal(closed.sweep(blocked,0,-3)?.module,'door','closed leaves block the exterior approach');
  const closedReason = closed.visitor.move(blocked,0,-3);
  assert.ok(closedReason && closedReason !== 'Floor edge' && blocked.z > 3.135);
  const route=[roomArrival,{x:0,z:2.15},{x:0,z:-1.4},{x:-.8,z:-1.55}];
  const forward=walk(scene,route),reverse=walk(scene,route.toReversed());
  for (const x of [-.2,0,.2]) assert.equal(ray([r.door],x,1.38,4.4,inside).length,0,'open doorway');
  const occupied={x:0,z:4.02};
  assert.equal(scene.visitor.obstruction(occupied),null,'body clears fully open leaves');
  assert.equal(scene.visitor.doorTransition(90,0,occupied,r.poseDoors),false,'swept close is blocked');
  assert.deepEqual(angles(),[-90,90]); assert.equal(scene.visitor.obstruction(occupied),null);
  assert.equal(scene.visitor.doorTransition(90,0,roomArrival,r.poseDoors),true);
  assert.deepEqual(angles(),[0,0]); assert.equal(scene.visitor.obstruction(occupied),null,'body clears closed leaves');
  assert.equal(scene.visitor.doorTransition(0,90,occupied,r.poseDoors),false);
  assert.deepEqual(angles(),[0,0]);
  const halfway=await physics(t,room(45));
  assert.equal(halfway.sweep(occupied,0,.0001,bodyCapsule())?.module,'door','independent triangles confirm intermediate collision');
  t.diagnostic(JSON.stringify({ openForward:forward, openReverse:reverse, occupied }));
});

test('an omitted rear straight releases a second walkable route across the still-present apron', async t => {
  const r=room();
  const rear=r.modules.wall2m.find(part=>part.position.z===-3);
  rear.removeFromParent();
  const scene=await physics(t,r);
  const walkResult=walk(scene,[{x:0,z:-1.6},{x:0,z:-4.2}]);
  assert.equal(walkResult.metres,2.6);
});
