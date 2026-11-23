import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, renameSync, writeFileSync } from 'node:fs';

const url = file => new URL(file,import.meta.url);
const read = name => readFileSync(url(name));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const rootName = 'motion_male_fixed.glb';
const trialName = '.runtime/motion_thumb_trial.glb';
const old = read(rootName);
const patch = read(trialName);
const decode = data => JSON.parse(data.toString('utf8',20,20+data.readUInt32LE(12)));
const a = decode(old);
const b = decode(patch);
assert.deepEqual(a.nodes,b.nodes);
assert.deepEqual(a.skins,b.skins);
assert.deepEqual(a.animations.filter(x=>x.name!=='walk'),b.animations.filter(x=>x.name!=='walk'));
const w1 = structuredClone(a.animations.find(c=>c.name==='walk'));
const w2 = structuredClone(b.animations.find(c=>c.name==='walk'));
assert.deepEqual(w1.channels,w2.channels);
let count=0;
for (const c of w1.channels) {
  const old = w1.samplers[c.sampler];
  const out = w2.samplers[c.sampler];
  if (old.input===out.input && old.output===out.output) continue;
  assert.equal(a.nodes[c.target.node].name,'mixamorig:LeftHandThumb1');
  assert.equal(c.target.path,'rotation');
  count++;
}
assert.equal(count,1);
const start1=28+old.readUInt32LE(12);
const start2=28+patch.readUInt32LE(12);
const length=a.buffers[0].byteLength;
assert.ok(old.subarray(start1,start1+length).equals(patch.subarray(start2,start2+length)));
const previous = hash(old);
const current = hash(patch);
const moduleKeys=['tshirt','dress','jeans','hair-bob','hair-spiky','hair-sidepart','sneakers'];
const records=[];
for (const k of moduleKeys) {
  const p=`qa/modules/${k}.json`;
  const x=JSON.parse(read(p));
  const y=JSON.parse(read(`.runtime/walkqa/modules/${k}.json`));
  assert.equal(Object.keys(x.clips).length,15,k);
  assert.equal(x.sha256,y.sha256,k);
  assert.equal(x.motion_sha256,previous,k);
  assert.equal(y.motion_sha256,current,k);
  const old = x.clips.walk;
  const revised = y.clips.walk;
  assert.equal(old.samples,revised.samples,k);
  if (k==='dress') assert.ok(revised.total_triangle_pairs<old.total_triangle_pairs,k);
  else assert.ok(revised.total_triangle_pairs<=old.total_triangle_pairs && revised.peak_inside<=old.peak_inside,k);
  x.clips.walk=revised;
  x.motion_sha256=current;
  records.push([p,x]);
  console.log(k,old.total_triangle_pairs,revised.total_triangle_pairs,revised.min_signed_m);
}
writeFileSync(url('.runtime/motion_without_thumb.glb'),old);
writeFileSync(url('.runtime/motion_publish.glb'),patch);
renameSync(url('.runtime/motion_publish.glb'),url(rootName));
for (const [p,obj] of records) {
  const stage=url(p+'.tmp');
  writeFileSync(stage,JSON.stringify(obj,null,2)+'\n');
  renameSync(stage,url(p));
}
writeFileSync(url('qa/walk_motion_proof.json'),JSON.stringify({previous,current,
  identicalClipNames:a.animations.filter(c=>c.name!=='walk').map(c=>c.name),
  amendedWalkChannel:'mixamorig:LeftHandThumb1.rotation',unchangedOriginalPoseDataBytes:length,
},null,2)+'\n');
