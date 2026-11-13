import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';import {createHash} from 'node:crypto';import {execFileSync} from 'node:child_process';
const slugs=JSON.parse(fs.readFileSync(new URL('../mall038-slugs.json',import.meta.url))),catalog=JSON.parse(fs.readFileSync(new URL('../models/catalog.json',import.meta.url)));
for(const slug of slugs)test(slug+' independent source, GLB and exact catalog evidence',()=>{
 const dir=new URL('../models/'+slug+'/',import.meta.url),read=f=>fs.readFileSync(new URL(f,dir)),sha=b=>createHash('sha256').update(b).digest('hex');
 for(const f of ['generate.py','sources/'+slug+'.blend','exports/optimized.glb','previews/hero.webp','previews/front.webp','previews/rear.webp','previews/side.webp','metadata/'+slug+'.json','LICENSE.md'])assert.ok(read(f).length>0,f);
 const entries=catalog.collections.flatMap(c=>c.assets).filter(a=>a.id===slug);assert.equal(entries.length,1);assert.equal(entries[0].file,'models/'+slug+'/exports/optimized.glb');
 execFileSync(process.execPath,[new URL('validate.mjs',dir).pathname],{stdio:'pipe'});
 const report=JSON.parse(read('reports/assets.json')),source=JSON.parse(read('reports/sources.json'));assert.equal(report.result,'PASS');assert.equal(report.sha256,sha(read('exports/optimized.glb')));assert.equal(source.source_sha256,sha(read('sources/'+slug+'.blend')));assert.equal(source.original_source_unchanged,true);
});
