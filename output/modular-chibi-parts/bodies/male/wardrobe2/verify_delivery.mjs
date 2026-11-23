import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { items, status } from './status.mjs';

process.chdir(fileURLToPath(new URL('.',import.meta.url)));
const json = path=>JSON.parse(readFileSync(path,'utf8'));
const sha = path=>createHash('sha256').update(readFileSync(path)).digest('hex');
const motion = '../round2/motion_male_fixed.glb';
const clipNames = ['rest','idle','walk','run','wave','jump','nod','dance','sit_down',
  'sit_idle','stand_up','hold_item','hold_box','hold_bag','take_item'];
const report = [];
for (const item of items) {
  const {picked,rounds} = json(`qa/${item}.result.json`);
  const review = json(`qa/${item}.visual.json`);
  const gate = json(`qa/${item}.gate.json`);
  const validator = json(`qa/${item}.validator.json`);
  const manifest = json(`renders/${item}/manifest.json`);
  const passed = picked.pass && review.pass;
  const candidate = passed ? item+'.glb' : picked.name+'.glb';
  const hash = sha(candidate);
  assert.equal(hash,picked.sha256,item);
  assert.ok([gate,validator,manifest,review].every(d=>d.sha256===hash),item+' report hashes');
  assert.deepEqual(Object.keys(gate.clips),clipNames);
  assert.equal(gate.motion_sha256,sha(motion));
  assert.equal(gate.master_sha256,sha('../master_male.blend'));
  assert.equal(gate.body_sha256,sha('../body_male.glb'));
  for (const [name,value] of Object.entries(gate.layers_sha256)) assert.equal(value,sha('../'+name));
  assert.deepEqual(gate.sampling_fps,[24,30]);
  assert.equal(gate.body_measurement,'full Blender BVH');
  assert.equal(Object.values(gate.clips).reduce((sum,clip)=>sum+clip.frames.length,0),2915);
  for (const clip of Object.values(gate.clips)) {
    assert.equal(clip.samples, clip.frames.length);
    assert.ok(clip.frames.every((frame,i)=>!i || frame.frame>clip.frames[i-1].frame));
  }
  assert.equal(validator.sameHierarchy,true);
  assert.ok(validator.bindError<5e-6);
  assert.ok(rounds.length>=1 && rounds.length<=3);
  assert.equal(rounds.length===3 || passed,true);
  assert.equal(existsSync(item+'.glb'),passed);
  assert.equal(manifest.views.length,6);
  const imagePaths = [manifest.rest_sheet,...manifest.views];
  if (item==='bottom-skirt') imagePaths.push(manifest.motion_sheet);
  for (const path of imagePaths) {
    const bytes = readFileSync(path);
    assert.equal(bytes.subarray(1,4).toString(),'PNG');
    assert.ok(bytes.readUInt32BE(16)>0 && bytes.readUInt32BE(20)>0);
  }
  for (const r of rounds) assert.deepEqual(r,status(item,r.round));
  report.push({item,candidate,rounds:rounds.length,passed,poses:2915});
}
console.table(report);
