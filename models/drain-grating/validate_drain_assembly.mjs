import fs from 'node:fs';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';import {Box3} from 'three';import {readGlb} from './glb.mjs';
const dir=fileURLToPath(new URL('.',import.meta.url));
const drain=await readGlb(dir+'../roadside-concrete-drain/exports/optimized.glb'),grating=await readGlb(dir+'exports/optimized.glb');
grating.scene.position.y=.5;grating.scene.updateMatrixWorld(true);
const a=[],b=[];drain.scene.traverse(o=>{if(o.isMesh)a.push({name:o.name,box:new Box3().setFromObject(o)})});grating.scene.traverse(o=>{if(o.isMesh)b.push({name:o.name,box:new Box3().setFromObject(o)})});
let pairs=0;const penetrations=[];
for(const x of a)for(const y of b){pairs++;const depths=['x','y','z'].map(k=>Math.min(x.box.max[k],y.box.max[k])-Math.max(x.box.min[k],y.box.min[k]));if(depths.every(v=>v>1e-6))penetrations.push([x.name,y.name,depths]);}
assert.deepEqual(penetrations,[]);
const db=new Box3().setFromObject(drain.scene),gb=new Box3().setFromObject(grating.scene);
for(const k of ['x','z']){assert.ok(Math.abs(db.min[k]-gb.min[k])<1e-6);assert.ok(Math.abs(db.max[k]-gb.max[k])<1e-6);}
assert.ok(Math.abs(gb.min.y-db.max.y)<1e-6);
const report={result:'PASS',grating_glTF_translation:[0,.5,0],cross_mesh_pairs:pairs,penetrations,plan_bounds_match:true,vertical_contact_gap:gb.min.y-db.max.y,scope:'Illustrative geometric composability only; not a load, safety, hydraulic or drainage certification.'};
fs.writeFileSync(dir+'reports/drain-assembly.json',JSON.stringify(report,null,2)+'\n');console.log(report);
