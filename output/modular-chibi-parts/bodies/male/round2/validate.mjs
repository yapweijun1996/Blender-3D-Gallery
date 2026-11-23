import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import validator from 'gltf-validator';

const here = new URL('./', import.meta.url);
const read = (name) => readFileSync(new URL(name, here));
const decode = (bytes) => JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const sourceBytes = read('../motion_male.glb');
const source = decode(sourceBytes);
const bindByName = (doc,bytes) => {
  const skin = doc.skins[0];
  const accessor = doc.accessors[skin.inverseBindMatrices];
  const view = doc.bufferViews[accessor.bufferView];
  const base = 28+bytes.readUInt32LE(12)+(view.byteOffset??0)+(accessor.byteOffset??0);
  const matrices = skin.joints.map((joint,index) => [doc.nodes[joint].name,
    Array.from({length:16},(_,element)=>bytes.readFloatLE(base+index*(view.byteStride??64)+element*4)),
  ]);
  return new Map(matrices);
};
const sourceBind = bindByName(source,sourceBytes);
const neutral = JSON.parse(read('../../../body-fix/body_selfcheck_before.json'));
writeFileSync(new URL('qa/neutral_rest_pairs.json', here), JSON.stringify({
  source: '../../../body-fix/body_selfcheck_before.json',
  sourceMasterSha256: neutral.master_sha256,
  ...neutral.source_rest_pose,
}, null, 2) + '\n');

const files = ['motion_male_fixed.glb','male-tshirt-v2.glb','male-dress-v2.glb','male-jeans-v2.glb'];
const results = {};
const clipTimes = (doc, anim) => {
  const input = anim.samplers.map((sampler) => doc.accessors[sampler.input]);
  return [Math.min(...input.map((a) => a.min[0])), Math.max(...input.map((a) => a.max[0]))];
};
for (const file of files) {
  const bytes = read(file);
  const doc = decode(bytes);
  const [skin] = doc.skins;
  assert.equal(skin.joints.length, 65);
  const structure = (d) => {
    const nodes = new Map(d.skins[0].joints.map((index) => [index, d.nodes[index].name]));
    return Object.fromEntries([...nodes].sort((a,b) => a[1].localeCompare(b[1])).map(([i, name]) => [
      name, (d.nodes[i].children ?? []).filter((c) => nodes.has(c)).map((c) => nodes.get(c)).sort(),
    ]));
  };
  assert.deepEqual(structure(doc), structure(source));
  const bindError = Math.max(...[...bindByName(doc,bytes)].flatMap(([key,row]) =>
    row.map((value,i)=>Math.abs(value-sourceBind.get(key)[i]))));
  assert.ok(bindError<5e-6,file+' inverse bind matrix mismatch');
  const report = await validator.validateBytes(new Uint8Array(bytes), { uri: file });
  const result = { sha256: sha256(bytes), bytes: bytes.length, joints: skin.joints.length,
    inverseBindMatrixMaxDifference: bindError, errors: report.issues.numErrors, warnings: report.issues.numWarnings, messages: report.issues.messages };
  if (file.startsWith('motion')) {
    assert.deepEqual(doc.nodes, source.nodes);
    assert.equal(doc.meshes, undefined);
    assert.deepEqual(doc.animations.map((a) => a.name), source.animations.map((a) => a.name));
    result.clips = Object.fromEntries(doc.animations.map((a,i) => {
      const [start,end] = clipTimes(doc,a);
      assert.deepEqual([start,end],clipTimes(source,source.animations[i]));
      assert.equal(a.channels.length,65*3);
      return [a.name,{ startSeconds:start,endSeconds:end,durationSeconds:end-start,channels:a.channels.length }];
    }));
  } else {
    assert.equal(doc.animations,undefined);
    result.triangles = doc.meshes.flatMap((m) => m.primitives)
      .reduce((count,primitive) => count+doc.accessors[primitive.indices].count/3,0);
  }
  results[file] = result;
  console.log(file,result.bytes,result.errors,result.warnings);
}
writeFileSync(new URL('qa/gltf_validation.json', here), JSON.stringify(results,null,2) + '\n');
assert.ok(Object.values(results).every((r) => r.errors === 0));
