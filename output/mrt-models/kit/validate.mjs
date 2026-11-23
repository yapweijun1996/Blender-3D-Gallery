import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const kit = dirname(fileURLToPath(import.meta.url));
const verifyRenders = process.argv.includes('--with-renders');
const validator = createRequire(import.meta.url)('../../../node_modules/gltf-validator');
const budgets = {
  mrt_carriage: 7000, mrt_platform: 3500, platform_screen_door: 700,
  fare_gate: 600, station_sign: 400, route_map: 300, train_seat: 250,
  train_door: 300, grab_handle: 120, card_reader: 150, arrival_display: 200,
};
const permittedMaterials = new Set([
  'paint','glass','tire','light','trim','wall','roof','window','metal','concrete',
  'chrome','plate','rubber','seat','screen',
]);
const movementNodes = {
  mrt_carriage: ['door_L1','door_L2','door_R1','door_R2'],
  platform_screen_door: ['leaf_1','leaf_2'],
  fare_gate: ['flap_L','flap_R'],
};
const wheelNames = ['wheel_FL','wheel_FR','wheel_RL','wheel_RR',
  'wheel_FL2','wheel_FR2','wheel_RL2','wheel_RR2'];
const add = (a,b) => a.map((x,i) => x+b[i]);
const subtract = (a,b) => a.map((x,i) => x-b[i]);
const dot = (a,b) => a.reduce((total,x,i) => total+x*b[i],0);
const cross = ([x,y,z],[u,v,w]) => [y*w-z*v,z*u-x*w,x*v-y*u];
const round = (x) => Number(x.toFixed(6));
const near = (a,b,epsilon=0.00005) => assert.ok(Math.abs(a-b)<epsilon,`${a} vs ${b}`);
const digest = (data) => createHash('sha256').update(data).digest('hex');

function box(points) {
  const min = [Infinity,Infinity,Infinity];
  const max = min.map(x => -x);
  for (const point of points) for (let i=0;i<3;i++) {
    min[i] = Math.min(min[i],point[i]);
    max[i] = Math.max(max[i],point[i]);
  }
  return { min, max, size: subtract(max,min).map(round) };
}

function unpackGlb(bytes) {
  assert.equal(bytes.toString('ascii',0,4),'glTF');
  assert.equal(bytes.readUInt32LE(4),2);
  assert.equal(bytes.readUInt32LE(8),bytes.length);
  const jsonEnd = 20+bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8',20,jsonEnd));
  const binary = bytes.subarray(jsonEnd+8);
  assert.equal(bytes.toString('ascii',jsonEnd+4,jsonEnd+7),'BIN');
  assert.equal(gltf.buffers.length,1);
  assert.equal(gltf.buffers[0].uri,undefined);
  assert.equal(gltf.buffers[0].byteLength,binary.length);
  return { gltf,binary };
}

function readAccessor(gltf,binary,index) {
  const accessor = gltf.accessors[index];
  const view = gltf.bufferViews[accessor.bufferView];
  const start = (view.byteOffset??0)+(accessor.byteOffset??0);
  if (accessor.type==='SCALAR' && accessor.componentType===5123) {
    return Array.from({length:accessor.count},(_,i) => binary.readUInt16LE(start+2*i));
  }
  assert.equal(accessor.type,'VEC3');
  assert.equal(accessor.componentType,5126);
  return Array.from({length:accessor.count},(_,i) =>
    [0,4,8].map(a => binary.readFloatLE(start+12*i+a)));
}

function geometry(gltf,binary) {
  const groups = {};
  for (const node of gltf.nodes) {
    const local = [];
    for (const primitive of gltf.meshes[node.mesh].primitives) {
      const points = readAccessor(gltf,binary,primitive.attributes.POSITION);
      const indices = readAccessor(gltf,binary,primitive.indices);
      for (let i=0;i<indices.length;i+=3) {
        const triangle = indices.slice(i,i+3).map(index => points[index]);
        const [a,b,c] = triangle;
        assert.ok(Math.hypot(...cross(subtract(b,a),subtract(c,a)))>1e-12,`Degenerate in ${node.name}`);
        local.push(triangle);
      }
    }
    groups[node.name] = { node, local, world: local.map(tri =>
      tri.map(p => add(p,node.translation??[0,0,0]))) };
  }
  return groups;
}

function intersection(tri, origin, delta) {
  const [a,b,c] = tri;
  const e1 = subtract(b,a);
  const e2 = subtract(c,a);
  const p = cross(delta,e2);
  const d = dot(e1,p);
  if (Math.abs(d)<1e-11) return Infinity;
  const q = subtract(origin,a);
  const u = dot(q,p)/d;
  const r = cross(q,e1);
  const v = dot(delta,r)/d;
  const t = dot(e2,r)/d;
  return u>=-1e-7 && v>=-1e-7 && u+v<=1+1e-7 && t>=0 && t<=1 ? t : Infinity;
}

function firstHit(groups, from, to, open=false) {
  const delta = subtract(to,from);
  let hit = Infinity;
  for (const group of Object.values(groups)) {
    const moving = open && group.node.extras?.openTranslationMeters;
    const origin = moving ? subtract(from,moving) : from;
    for (const tri of group.world) hit = Math.min(hit,intersection(tri,origin,delta));
  }
  return hit;
}

function crossings(groups,rays) {
  for (const [from,to] of rays) {
    assert.ok(firstHit(groups,from,to)<Infinity,`Closed volume missing at ${from}`);
    assert.equal(firstHit(groups,from,to,true),Infinity,`Open passage blocked at ${from}`);
  }
}

function verifyUse(stem, groups, extents) {
  if (stem==='mrt_carriage') {
    for (const name of wheelNames) {
      const bounds = box(groups[name].local.flat());
      assert.ok(bounds.size[0]<.26);
      for (const i of [1,2]) {
        near(bounds.size[i],.86);
        near(bounds.max[i]+bounds.min[i],0);
      }
      near(groups[name].node.translation[1],.43);
    }
    const rays = [];
    for (const side of [-1,1]) for (const center of [-3.4,3.4]) {
      for (const dz of [-.53,-.25,.18,.52]) for (const y of [1.28,1.8,2.35,2.87]) {
        rays.push([[side*1.77,y,center+dz],[side*.91,y,center+dz]]);
      }
      for (const x of [0,.8,1.43]) {
        const t = firstHit(groups,[side*x,1.26,center-.05],[side*x,1.11,center-.05],true);
        near(1.26-.15*t,1.2,.001);
      }
    }
    crossings(groups,rays);
    for (const x of [-.35,0,.35]) for (let z=-9.5;z<=9.5;z+=.25) {
      near(1.26-.15*firstHit(groups,[x,1.26,z],[x,1.11,z]),1.2,.001);
    }
    for (const x of [-.35,0,.35]) for (const y of [1.3,1.7,2.15,2.65,2.95]) {
      assert.equal(firstHit(groups,[x,y,-9.5],[x,y,9.5]),Infinity);
    }
    return {doorCrossingRays:rays.length,walkableAisleMeters:.7,
      floorSamples:231,doorSillSamples:12,openChecks:'pass'};
  }
  if (stem==='mrt_platform') {
    near(extents.size[0],120);
    for (let x=-59.5;x<60;x+=1) {
      const t = firstHit(groups,[x,1.25,1.8],[x,1.1,1.8]);
      near(1.25-.15*t,1.15,.001);
    }
    return {platformLengthMeters:120,continuousDeckSamples:120};
  }
  if (stem==='platform_screen_door') {
    near(extents.size[0],3);
    const left = groups.leaf_1.local;
    const right = groups.leaf_2.local;
    assert.equal(left.length,right.length,'Screen door leaves must use mirrored profiles');
    assert.deepEqual(box(left.flat()).size,box(right.flat()).size);
    const rays = [-.6,-.3,.3,.6].flatMap(x => [.3,.9,1.5,2.1].map(y =>
      [[x,y,.6],[x,y,.02]]));
    crossings(groups,rays);
    return {bayWidthMeters:3,passageRays:rays.length,openChecks:'pass'};
  }
  if (stem==='fare_gate') {
    const rays = [-.21,-.11,.11,.21].flatMap(x => [.42,.62,.82].map(y =>
      [[x,y,1],[x,y,-1]]));
    crossings(groups,rays);
    return {passageRays:rays.length,openChecks:'pass'};
  }
  return {};
}

const records = [];
const issues = [];
for (const [stem,budget] of Object.entries(budgets)) {
  const file = stem+'.glb';
  const bytes = await readFile(join(kit,file));
  const validation = await validator.validateBytes(new Uint8Array(bytes),{uri:file,maxIssues:0});
  const { gltf,binary } = unpackGlb(bytes);
  assert.ok(bytes.length<=400_000);
  for (const forbidden of ['animations','skins','cameras','images','textures','samplers','extensions']) {
    assert.equal(gltf[forbidden],undefined);
  }
  assert.equal(gltf.nodes.length,gltf.meshes.length);
  assert.deepEqual(gltf.scenes[0].nodes,gltf.nodes.map((_,i)=>i));
  const materials = gltf.materials.map(m=>m.name);
  assert.equal(new Set(materials).size,materials.length);
  assert.ok(materials.every(m=>permittedMaterials.has(m)));
  const paint = gltf.materials.find(m=>m.name==='paint');
  if (paint) {
    const paintIndex = gltf.materials.indexOf(paint);
    assert.equal(paint.pbrMetallicRoughness.baseColorFactor[3],1);
    for (const mesh of gltf.meshes) for (const primitive of mesh.primitives) {
      if (primitive.material===paintIndex) assert.equal(primitive.attributes.COLOR_0,undefined);
    }
  }
  const primitives = gltf.meshes.flatMap(mesh=>mesh.primitives);
  assert.ok(primitives.length<=16);
  assert.deepEqual(gltf.nodes.map(n=>n.name).sort(),
    ['body',...(movementNodes[stem]??[]),...(stem==='mrt_carriage'?wheelNames:[])].sort());
  assert.equal(gltf.nodes.find(n=>n.name==='body').translation,undefined);
  const groups = geometry(gltf,binary);
  const triangles = Object.values(groups).reduce((sum,g)=>sum+g.local.length,0);
  assert.ok(triangles<=budget);
  const extents = box(Object.values(groups).flatMap(g=>g.world.flat()));
  near(extents.min[1],0);
  near(extents.min[0]+extents.max[0],0);
  near(extents.min[2]+extents.max[2],0);
  const checks = verifyUse(stem,groups,extents);
  const { numErrors:errors,numWarnings:warnings } = validation.issues;
  if (errors || warnings) issues.push({ file,messages:validation.issues.messages });
  if (verifyRenders) {
    const record = JSON.parse(await readFile(join(kit,'comparisons',stem+'.json'),'utf8'));
    assert.equal(record.candidateSha256,digest(bytes));
    assert.equal(record.sourceSha256,digest(await readFile(join(kit,'../../..',record.source))));
    assert.equal(record.sheetSha256,digest(await readFile(join(kit,record.sheet))));
    assert.equal(record.views.length,6);
    assert.match(record.renderer,/Cycles CPU/);
    assert.equal(record.threads,2);
  }
  records.push({
    file,triangles,budget,bytes:bytes.length,size_m:{x:extents.size[0],y:extents.size[1],z:extents.size[2]},
    primitives:primitives.length,materials,
    validator:{version:validation.validatorVersion,errors,warnings,result:errors||warnings?'fail':'pass'},
    sha256:digest(bytes),checks,
  });
  console.log(file,triangles,bytes.length,JSON.stringify(extents.size),primitives.length,`${errors}/${warnings}`);
}
assert.deepEqual(issues,[]);
await writeFile(join(kit,'models.json'),JSON.stringify(records,null,2)+'\n');
