// Run from the gallery repository root. Probe the delivered geometry in metres.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const asset = dirname(fileURLToPath(import.meta.url));
const project = createRequire(resolve('package.json'));
const THREE = await import(new URL('three.module.js',pathToFileURL(project.resolve('three'))));
const { readGlb } = await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')));
const { validateBytes } = project('gltf-validator');
const slug = 'mall-cosmetics-tester-bar';
const radiusTolerance = .000005;
const ray = new THREE.Raycaster();
function near(actual, expected, label) {
  assert.ok(Math.abs(actual - expected) < radiusTolerance, label+' measured '+actual+' expected '+expected);
}
function hit(object, origin, dir) {
  ray.set(new THREE.Vector3(...origin), new THREE.Vector3(...dir));
  const result = ray.intersectObject(object, true)[0];
  assert.ok(result,'expected geometry along ray at '+origin);
  return result.point;
}
function checkClose(scene) {
  function part(name) {
    const object=scene.getObjectByName(name+'_LOD0');
    assert.ok(object,name);
    return object;
  }
  function up(object,x,z) { return hit(object,[x,-.15,z],[0,1,0]).y; }
  function down(object,x,z) { return hit(object,[x,1.55,z],[0,-1,0]).y; }
  const deck=part('Ivory_solid_surface');
  const floor=part('Grounded_plinth');
  const mirror=part('Mirror_inset_silver_face');
  const bezel=part('Mirror_champagne_bezel');
  // Contact rays use both outward faces on each interface.
  for(const x of [-.25,0,.25]) for(const z of [-.15,0,.1]) near(up(floor,x,z),0,'floor seat');
  near(down(deck,0,.25),.867,'customer worktop');
  const minusZ=[0,0,-1];
  near(hit(mirror,[0,1.235,.2],minusZ).z,-.2805,'silver surface');
  near(hit(bezel,[0,1.235,.2],minusZ).z,-.283,'glass seat');
  near(hit(mirror,[0,1.235,-.6],[0,0,1]).z,-.283,'glass back');
  near(hit(bezel,[0,1.487,.2],minusZ).z,-.276,'bezel projects beyond silver');
  let count=0;
  for(const [s,label] of [[-1,'Lip'],[1,'Complexion']]) {
    const x0=s*.224;
    const tray=part(label+'_socket_tray');
    const metal=part(label+'_champagne_tray_edge');
    const cups=part(label+'_four_swatch_cups');
    const powder=part(label+'_four_pressed_swatches');
    near(up(metal,x0,.204),down(deck,x0,.204),'tray on counter');
    near(up(tray,x0,.204),down(metal,x0,.204),'tray on champagne edge');
    near(down(tray,x0,.204),.893,'tray surface');
    for(const dx of [-.144,-.048,.048,.144]) {
      const x=x0+dx, z=.154;
      near(down(tray,x,z),.876,'machined floor');
      near(up(cups,x,z),down(tray,x,z),'cup to machined seat');
      near(up(powder,x,z),down(cups,x,z),'swatch to cup');
      near(down(powder,x,z),.8896,'pigment surface');
      near(down(cups,x+.0325,z),.891,'cup lip');
      const sight=hit(scene,[x,1.55,z],[0,-1,0]);
      near(sight.y,.8896,'exposed sample');
      count++;
    }
    for(const [i,dx] of [-.119,0,.119].entries()) {
      const product=part(label+(s<0?'_lipstick_':'_pump_')+(i+1));
      const x=x0+dx,z=.018;
      near(up(product,x,z),down(tray,x,z),'product to blind pocket');
      assert.ok(down(product,x,z)>.98,'visible over deck');
    }
  }
  return {groundRays:9,mirrorGlassAndBezelChecks:4,powderPansWithTwoSeatedInterfaces:count,
          seatedUprightProducts:6,measuredWorktopYM:.867,frontSwatchYM:.8896,frontSwatchZM:.154};
}
const report={axis:'glTF +Y up, +Z customer',levels:[]};
for (let lod=0;lod<3;lod++) {
  const name=slug+(lod?'-lod'+lod:'')+'.glb';
  const {bytes,json,scene}=await readGlb(resolve(asset,'exports',name));
  const khronos=await validateBytes(bytes,{uri:name,maxIssues:50});
  assert.equal(khronos.issues.numErrors+khronos.issues.numWarnings,0,JSON.stringify(khronos.issues));
  assert.equal(json.scenes[json.scene].nodes.length,1);
  assert.ok(scene.getObjectByName('ASSET_CosmeticsTesterBar_LOD'+lod));
  assert.ok(!json.animations && !json.images && !json.cameras && !json.buffers.some(b=>b.uri));
  assert.ok(!JSON.stringify(json).includes('"extras"'));
  const bounds=new THREE.Box3().setFromObject(scene,true);
  for(const [point,expected] of [[bounds.min,[-.5,0,-.4]],[bounds.max,[.5,1.5,.4]]])
    point.toArray().forEach((value,axis)=>near(value,expected[axis],'bounds'));
  const primitives=json.meshes.flatMap(m=>m.primitives);
  const triangles=primitives.reduce((s,p)=>s+json.accessors[p.indices].count/3,0);
  const row={level:'LOD'+lod,file:'exports/'+name,triangles,draws:primitives.length,bytes:bytes.length,
    sha256:createHash('sha256').update(bytes).digest('hex'),bounds:[bounds.min.toArray(),bounds.max.toArray()],
    validation:{errors:0,warnings:0,infos:khronos.issues.numInfos}};
  if(lod===0) {
    assert.ok(triangles <= 12000);
    report.contacts=checkClose(scene);
    const swatch=scene.getObjectByName('Lip_four_pressed_swatches_LOD0');
    swatch.position.y+=.006;
    scene.updateMatrixWorld(true);
    assert.throws(()=>checkClose(scene),/swatch to cup/);
    report.negativeControl='Raising lip pigments 6 mm failed the swatch-to-cup test.';
  } else {
    const previous=report.levels[lod-1];
    assert.ok(row.triangles<previous.triangles && row.draws<previous.draws && row.bytes<previous.bytes);
  }
  report.levels.push(row);
}
await fs.writeFile(resolve(asset,'reports/geometry.json'),JSON.stringify(report,null,2)+'\n');
console.log(report.levels.map(({level,triangles,draws,bytes})=>({level,triangles,draws,bytes})));
