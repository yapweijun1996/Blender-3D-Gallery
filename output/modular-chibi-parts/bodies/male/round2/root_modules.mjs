import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, renameSync, writeFileSync } from 'node:fs';

const keys = process.argv.slice(2);
for (const key of keys.length ? keys : ['tshirt','dress','jeans']) {
  assert.ok(['tshirt','dress','jeans'].includes(key));
  const url = new URL(`male-${key}-v2.glb`,import.meta.url);
  const bytes = readFileSync(url);
  const end = 20 + bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.toString('utf8',20,end));
  const mesh = doc.nodes.findIndex((n) => n.skin !== undefined);
  const parent = doc.nodes.findIndex((n) => n.children?.includes(mesh));
  if (parent < 0) continue;
  const scene = doc.scenes[doc.scene];
  assert.ok(scene.nodes.includes(parent));
  assert.ok(!['matrix','translation','rotation','scale'].some(k => k in doc.nodes[parent]));
  doc.nodes[parent].children = doc.nodes[parent].children.filter(i => i !== mesh);
  scene.nodes.push(mesh);
  let text = JSON.stringify(doc);
  text += ' '.repeat((4 - Buffer.byteLength(text)%4)%4);
  const json = Buffer.from(text);
  const header = Buffer.from(bytes.subarray(0,20));
  header.writeUInt32LE(json.length,12);
  header.writeUInt32LE(20+json.length+bytes.length-end,8);
  const rooted = Buffer.concat([header,json,bytes.subarray(end)]);
  const file = new URL(`qa/fit-${key}.json`,import.meta.url);
  const fit = JSON.parse(readFileSync(file,'utf8'));
  fit.sha256 = createHash('sha256').update(rooted).digest('hex');
  const stage = new URL(`qa/${key}-rooted.tmp`,import.meta.url);
  writeFileSync(stage,rooted);
  renameSync(stage,url);
  writeFileSync(file,JSON.stringify(fit,null,2)+'\n');
}
