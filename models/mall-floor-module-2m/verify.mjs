import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';

const id = 'mall-floor-module-2m';
const read = name => readFile(new URL(name, import.meta.url));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const metadata = JSON.parse(await read(`metadata/${id}.json`));
const sourceCheck = JSON.parse(await read('reports/source-reimport.json'));
assert.equal(hash(await read(metadata.paths.source)), sourceCheck.sourceSHA256);
assert.equal(hash(await read(metadata.paths.preview)), metadata.sha256.preview);
const measured = [];
for (const variant of metadata.lods) {
  const bytes = await read(variant.file);
  const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  const validation = await validateBytes(bytes, { uri: variant.file });
  assert.deepEqual([validation.issues.numErrors, validation.issues.numWarnings], [0, 0]);
  assert.equal(doc.scenes.length, 1);
  assert.equal(doc.nodes.length, 1);
  assert.equal(doc.nodes[0].extras.lod, variant.level);
  assert.equal(doc.nodes[0].name, `MODULE_StraightFloor_L${variant.level}`);
  assert.ok(!doc.animations && !doc.cameras && !doc.skins && !doc.extensionsRequired);
  assert.ok(doc.buffers.every(b => !b.uri) && doc.images.every(im => !im.uri && im.bufferView !== undefined));
  const draws = doc.meshes[0].primitives.length;
  const result = { level: variant.level, bytes: bytes.length, triangles: validation.info.totalTriangleCount,
    draws, sha256: hash(bytes) };
  for (const [key, value] of Object.entries(result)) assert.equal(variant[key], value);
  const reopened = sourceCheck.variants[variant.level];
  assert.equal(reopened.sha256, result.sha256);
  assert.equal(reopened.reimport.triangles, result.triangles);
  measured.push(result);
}
assert.ok(measured[0].triangles > measured[1].triangles && measured[1].triangles > measured[2].triangles);
assert.ok(measured[0].bytes > measured[1].bytes && measured[1].bytes > measured[2].bytes);
assert.equal(measured[2].draws, 1);
console.log(JSON.stringify(measured,null,2));
