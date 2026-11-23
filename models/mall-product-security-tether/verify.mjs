// Use the actual tabletop, animated laptop and all three delivered tether GLBs.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const dir=dirname(fileURLToPath(import.meta.url));
const req=createRequire(resolve('package.json')),three=dirname(req.resolve('three'));
const T=await import(pathToFileURL(resolve(three,'three.module.js')));
const {GLTFLoader}=await import(pathToFileURL(resolve(three,'../examples/jsm/loaders/GLTFLoader.js')));
const {readGlb}=await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')));
const {validateBytes}=req('gltf-validator');
const sha=b=>createHash('sha256').update(b).digest('hex');
const V=(x,y,z)=>new T.Vector3(x,y,z),up=V(0,1,0),down=V(0,-1,0),ray=new T.Raycaster();
function hit(object,from,direction) { ray.set(from,direction);return ray.intersectObject(object,true)[0]; }
function near(a,b,label) {assert.ok(Math.abs(a-b)<1e-6,label+' '+a+' vs '+b);}
const slug='mall-product-security-tether';
const [desk,pc]=await Promise.all(['tv-demo-table','laptop'].map(s=>readGlb(resolve('models',s,'exports/optimized.glb'))));
const loader=new GLTFLoader();
const laptop=(await loader.parseAsync(pc.bytes.buffer.slice(pc.bytes.byteOffset,pc.bytes.byteOffset+pc.bytes.length),''));
laptop.scene.position.set(.5,.8,.24);
laptop.scene.updateMatrixWorld(true);
const chassis=laptop.scene.getObjectByName('BASE_Chassis'),lid=laptop.scene.getObjectByName('MOVABLE_Lid');
const mixer=new T.AnimationMixer(laptop.scene),clip=laptop.animations[0];
assert.ok(chassis && lid && clip.duration>1);
function seats(tether){
  let checked=0,worst=0;
  for(const [surface,x,y,dxs,dzs] of [
    [desk.scene,.77,.80,[-.018,0,.018],[-.018,0,.018]],
    [chassis,.62,.82,[-.010,0,.010],[-.006,0,.006]]
  ]) {
    for(const dx of dxs) for(const dz of dzs) {
      const bottom=hit(tether,V(x+dx,y-.002,.32+dz),up);
      const top=hit(surface,V(x+dx,y+.001,.32+dz),down);
      assert.ok(bottom && top,'expected paired seat triangles');
      near(bottom.point.y,top.point.y,'adhesive contact');
      checked++;
      worst=Math.max(worst,Math.abs(bottom.point.y-top.point.y));
    }
  }
  return {points:checked,maximumGapM:worst};
}
function lidSweep(tether) {
  const probes=[];let maxRise=0;
  const palmY=hit(chassis,V(.62,.85,.32),down).point.y;
  for(let mmX=-166;mmX<=-97;mmX+=3) for(let mmZ=-11;mmZ<=43;mmZ+=3) {
    const x=.77+mmX/1000,z=.32+mmZ/1000;
    const housing=hit(tether,V(x,.86,z),down),base=hit(chassis,V(x,.86,z),down);
    if(!housing||!base)continue;
    const heightAbovePalm=housing.point.y-palmY;
    assert.ok(heightAbovePalm<.012001,'12 mm palm-plane envelope');
    maxRise=Math.max(maxRise,heightAbovePalm);
    const lowest=hit(tether,V(x,.79,z),up);
    if(lowest)assert.ok(lowest.point.y>=base.point.y-1e-6,'tether enters chassis');
    probes.push(housing.point.clone());
  }
  assert.ok(probes.length>35);
  const action=mixer.clipAction(clip);
  action.reset();action.setLoop(T.LoopOnce,1);action.clampWhenFinished=true;action.play();
  const frames=301;let gap=Infinity,hits=0,atTime=0;
  for(let frame=0;frame<frames;frame++) {
    const t=clip.duration*frame/(frames-1);
    mixer.setTime(t);laptop.scene.updateMatrixWorld(true);
    for(const point of probes) {
      const roof=hit(lid,point,up);
      if(!roof)continue;
      hits++;
      if(roof.distance<gap){gap=roof.distance;atTime=t;}
    }
  }
  action.stop();mixer.setTime(0);
  assert.ok(gap>.009 && gap<.018 && hits>1000);
  return {poses:frames,footprintGridPitchM:.003,maximumProjectionAbovePalmPlaneM:maxRise,footprintRaysPerPose:probes.length,lidIntersections:hits,minimumGapM:gap,clipTimeAtMinimumS:atTime};
}
const report={axis:'glTF +Y up; table at origin, install root on table at (+.770,+.800,+.320) metres',
  laptopSha256:sha(pc.bytes),tableSha256:sha(desk.bytes),clip:clip.name,clipDurationSeconds:clip.duration,levels:[]};
for(const lod of [0,1,2]){
  const file=slug+(lod?'-lod'+lod:'')+'.glb';
  const {scene,bytes,json}=await readGlb(resolve(dir,'exports',file));
  const result=await validateBytes(bytes,{uri:file});
  assert.equal(result.issues.numErrors+result.issues.numWarnings,0,JSON.stringify(result.issues));
  assert.ok(!json.animations && !json.images && !json.cameras && !JSON.stringify(json).includes('"extras"'));
  const root=scene.getObjectByName('ASSET_ProductSecurityTether_LOD'+lod);assert.ok(root);
  const bounds=new T.Box3().setFromObject(scene,true);
  near(bounds.min.y,0,'base root');near(bounds.min.x,-.1665,'device side');near(bounds.max.x,.0265,'puck side');
  if(lod===0) {
    for(const [part,toX,localZ,y] of [['Base_strain_relief',-.038,.006,.013],['Device_strain_relief',-.1255,.003,.0257]]) {
      const front=part.startsWith('Base')?1:-1,origin=V(toX-front*.006,y,localZ);
      near(hit(scene.getObjectByName(part+'_LOD0'),origin,V(front,0,0)).point.x,toX,'boot end');
      near(hit(scene.getObjectByName('Looped_polymer_lead_LOD0'),V(toX+front*.0001,y,localZ),V(-front,0,0)).point.x,toX,'wire end');
    }
  }
  scene.position.set(.77,.8,.32);scene.updateMatrixWorld(true);
  const contact=seats(scene),sweep=lidSweep(scene);
  if(lod===0){scene.position.y+=.003;scene.updateMatrixWorld(true);assert.throws(()=>seats(scene),/adhesive contact/);}
  const primitives=json.meshes.flatMap(m=>m.primitives);
  const row={level:'LOD'+lod,file:'exports/'+file,sha256:sha(bytes),bytes:bytes.length,draws:primitives.length,
    triangles:primitives.reduce((s,p)=>s+json.accessors[p.indices].count/3,0),validator:{errors:0,warnings:0,infos:result.issues.numInfos},
    bounds:[bounds.min.toArray(),bounds.max.toArray()],seat:contact,lid:sweep};
  if(lod===0)assert.ok(row.triangles<=3000);
  else {const prev=report.levels.at(-1);assert.ok(row.triangles<prev.triangles && row.draws<prev.draws && row.bytes<prev.bytes);}
  report.levels.push(row);
}
report.negativeControl='Raising the installed tether 3 mm broke both-surface seating.';
await fs.writeFile(resolve(dir,'reports/geometry.json'),JSON.stringify(report,null,2)+'\n');
console.log(report.levels.map(r=>({level:r.level,triangles:r.triangles,minGapM:r.lid.minimumGapM})));
