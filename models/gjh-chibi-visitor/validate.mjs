import assert from 'node:assert/strict';
import fs from 'node:fs';
import { validateBytes } from 'gltf-validator';
import { loadCatalog } from '../../scripts/catalog.mjs';

const base = 'models/gjh-chibi-visitor';
const unityVariants = ['terra', 'sol', 'astra'];
const registeredIds = [
  'gjh-chibi-visitor-blender',
  ...unityVariants.map(variant => 'gjh-chibi-visitor-' + variant),
];
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'gjh-chibi-visitor');
assert.ok(collection, 'GJH Chibi Visitor collection is registered');
assert.deepEqual(collection.assets.map(asset => asset.id), registeredIds, 'Blender primary must appear before the three Unity experiments');

const validatorPackage = JSON.parse(fs.readFileSync('node_modules/gltf-validator/package.json', 'utf8'));

function readDocument(bytes) {
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonLength = bytes.readUInt32LE(12);
  return JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
}

function measure(document, bytes) {
  let triangles = 0;
  for (const node of document.nodes ?? []) {
    if (node.mesh === undefined) continue;
    for (const primitive of document.meshes[node.mesh].primitives) {
      assert.equal(primitive.mode ?? 4, 4, 'Only triangle primitives are supported');
      const accessor = document.accessors[primitive.indices ?? primitive.attributes.POSITION];
      assert.equal(accessor.count % 3, 0, 'Triangle accessor count must be divisible by three');
      triangles += accessor.count / 3;
    }
  }
  const positions = new Set(
    (document.meshes ?? []).flatMap(mesh => mesh.primitives.map(primitive => primitive.attributes.POSITION)),
  );
  return {
    glb_bytes: bytes.length,
    triangles,
    vertices: [...positions].reduce((count, index) => count + document.accessors[index].count, 0),
    animations: document.animations?.length ?? 0,
  };
}

async function validateAsset({ id, root, registered = true }) {
  const relative = root + '/exports/' + id + '.glb';
  const bytes = fs.readFileSync(relative);
  const document = readDocument(bytes);
  const sceneRoots = document.scenes[document.scene ?? 0].nodes.map(index => document.nodes[index].name);
  assert.deepEqual(sceneRoots, ['GJHChibiVisitor'], id + ' scene root');
  const result = await validateBytes(new Uint8Array(bytes));
  console.log(id + ': ' + bytes.length + ' bytes; ' + result.info.totalTriangleCount + ' unique-mesh triangles; ' + result.issues.numErrors + ' errors; ' + result.issues.numWarnings + ' warnings');
  if (result.issues.numErrors || result.issues.numWarnings) {
    for (const issue of result.issues.messages.filter(item => item.severity <= 1)) console.error(issue.message);
    throw new Error('Khronos glTF validation failed for ' + id);
  }
  if (registered) {
    const metadataPath = root + '/metadata.json';
    const metadata = JSON.parse(fs.readFileSync(metadataPath, 'utf8'));
    assert.deepEqual(metadata.metrics, measure(document, bytes), id + ' measured metadata');
    metadata.validation = {
      errors: result.issues.numErrors,
      warnings: result.issues.numWarnings,
      validator: validatorPackage.version,
    };
    fs.writeFileSync(metadataPath, JSON.stringify(metadata, null, 2) + '\n');
  }
}

await validateAsset({ id: 'gjh-chibi-visitor-blender', root: base + '/blender' });
await validateAsset({ id: 'gjh-chibi-visitor-blender-kit', root: base + '/blender', registered: false });
for (const variant of unityVariants) {
  await validateAsset({ id: 'gjh-chibi-visitor-' + variant, root: base + '/' + variant });
}
