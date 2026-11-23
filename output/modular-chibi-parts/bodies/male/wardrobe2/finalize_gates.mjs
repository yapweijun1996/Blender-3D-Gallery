import assert from 'node:assert/strict';
import { copyFileSync, existsSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { items, status } from './status.mjs';

process.chdir(fileURLToPath(new URL('.',import.meta.url)));
const json = path=>JSON.parse(readFileSync(path,'utf8'));
const sha = path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const selected = items.map(item=>{
  const result = json(`qa/${item}.result.json`);
  const report = json(`qa/${item}.full.gate.json`);
  const name = result.picked.name;
  assert.equal(report.sha256,sha(name+'.glb'));
  assert.equal(report.body_measurement,'full Blender BVH');
  assert.equal(Object.keys(report.clips).length,15);
  assert.equal(Object.values(report.clips).reduce((n,row)=>n+row.samples,0),2915);
  return {item,result,name};
});
for (const {item,result,name} of selected) {
  const targetGate = `qa/${name}.gate.json`;
  const archive = `qa/${name}.prefinal.gate.json`;
  if (!existsSync(archive)) copyFileSync(targetGate,archive);
  copyFileSync(`qa/${item}.full.gate.json`,targetGate);
  copyFileSync(targetGate,`qa/${item}.gate.json`);
  const revised = status(item,result.picked.round);
  const newRounds = result.rounds.map(r=>r.round===revised.round ? revised : r);
  const visual = json(`qa/${item}.visual.json`);
  if (revised.pass && visual.pass) {
    copyFileSync(`${name}.glb`,`${item}.glb`);
  } else if (existsSync(item+'.glb')) {
    assert.equal(sha(item+'.glb'),sha(name+'.glb'));
    unlinkSync(item+'.glb');
  }
  writeFileSync(`qa/${item}.result.json`,JSON.stringify({picked:revised,rounds:newRounds},null,2)+'\n');
}
