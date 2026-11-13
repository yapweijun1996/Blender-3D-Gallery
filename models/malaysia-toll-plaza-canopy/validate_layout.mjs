import assert from 'node:assert/strict';import fs from 'node:fs';import {fileURLToPath} from 'node:url';import {Box3} from 'three';import {readGlb} from './glb.mjs';
const dir=fileURLToPath(new URL('.',import.meta.url)),spec=JSON.parse(fs.readFileSync(dir+'backlog.json'));
const {scene}=await readGlb(dir+'exports/optimized.glb');const boxes=[];
scene.traverse(o=>{if(o.isMesh&&o.name.startsWith(spec.id===383?'COLUMN_Gantry':'BASE_Island'))boxes.push(new Box3().setFromObject(o));});
boxes.sort((a,b)=>a.min.x-b.min.x);assert.equal(boxes.length,spec.id===383?2:3);
const widths=boxes.slice(1).map((b,i)=>b.min.x-boxes[i].max.x);for(const w of widths)assert.ok(Math.abs(w-(spec.id===383?8.05:3.85))<.001);
const report={backlog_id:spec.id,clear_widths_m:widths,purpose:'Illustrative modular layout datum only, not certified installation, road or structural clearance.',result:'PASS'};
fs.writeFileSync(dir+'reports/layout.json',JSON.stringify(report,null,2)+'\n');console.log(report);
