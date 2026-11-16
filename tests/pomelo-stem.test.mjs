import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {loadCatalog} from '../scripts/catalog.mjs';

const root = 'models/pomelo-stem';
const assetRoot = `${root}/mascot`;
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'pomelo-stem');
const expectedId = 'pomelo-stem-mascot';
const expectedLicense = catalog.collections
  .flatMap(item => item.assets)
  .find(asset => asset.id === 'gjh-chibi-visitor-blender').license;

function readGlb(filename) {
  const bytes = fs.readFileSync(`${assetRoot}/exports/${filename}`);
  assert.equal(bytes.toString('ascii', 0, 4), 'glTF');
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonLength = bytes.readUInt32LE(12);
  const document = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  return {bytes, document};
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

test('Pomelo STEM registers one character asset after the existing collections', () => {
  assert.ok(collection);
  assert.equal(catalog.collections.at(-1).id, 'pomelo-stem');
  assert.equal(collection.name, 'Pomelo STEM');
  assert.equal(collection.assets.length, 1);
  assert.deepEqual(collection.assets.map(asset => asset.id), [expectedId]);

  const asset = collection.assets[0];
  assert.equal(asset.name, 'Pomelo STEM Mascot');
  assert.equal(asset.category, 'Characters');
  assert.equal(asset.root, 'PomeloStemMascot');
  assert.equal(asset.downloadable, false);
  assert.equal(asset.license, expectedLicense);
  assert.match(asset.description, /original fruit mascot/i);
  assert.match(asset.description, /procedurally in Blender/i);
  assert.match(asset.description, /static.*one-metre/i);
  assert.match(asset.description, /six static expressions/i);
  assert.deepEqual(asset.details.display.previewCameraDirection, [0, 0, 1]);
  assert.equal(asset.details.display.front_axis, '+Z');
  assert.equal(fs.existsSync(`${root}/catalog-entry.draft.json`), false);
});

test('pomelo-stem-mascot metadata is measured from the registered hero GLB', () => {
  const asset = collection.assets[0];
  const metadata = JSON.parse(fs.readFileSync(`${assetRoot}/metadata.json`, 'utf8'));
  const {bytes, document} = readGlb('pomelo-stem-mascot.glb');
  assert.equal(metadata.id, expectedId);
  assert.equal(metadata.name, asset.name);
  assert.equal(metadata.category, asset.category);
  assert.equal(metadata.status, 'validated');
  assert.equal(metadata.generator, 'generate.py');
  assert.equal(metadata.root_node, 'PomeloStemMascot');
  assert.equal(metadata.rights, expectedLicense);
  assert.deepEqual(asset.details, metadata);
  assert.deepEqual(measure(document, bytes), metadata.metrics);
  assert.equal(metadata.metrics.animations, 0);
  assert.equal(metadata.blender_version, '5.2.3 LTS');
  assert.equal(metadata.validation.errors, 0);
  assert.equal(metadata.validation.warnings, 0);
  assert.equal(metadata.additional_exports.stand.animations, 0);
  assert.equal(metadata.additional_exports.kit.animations, 0);

  const roots = document.scenes[document.scene ?? 0].nodes;
  assert.equal(roots.length, 1);
  assert.equal(document.nodes[roots[0]].name, 'PomeloStemMascot');
  assert.ok(fs.statSync(`${assetRoot}/previews/front.webp`).size < 150 * 1024);
  for (const view of ['side', 'back', '3q', 'expressions'])
    assert.ok(fs.statSync(`${assetRoot}/previews/${view}.webp`).size > 0);
  for (const filename of ['generate.py', 'convert-previews.py', 'pomelo-stem-mascot.blend',
    'exports/pomelo-stem-mascot-stand.glb', 'exports/pomelo-stem-mascot-kit.glb'])
    assert.ok(fs.statSync(`${assetRoot}/${filename}`).size > 0, filename);
});

test('Pomelo STEM exports preserve the shared root and measured budgets', () => {
  const metadata = JSON.parse(fs.readFileSync(`${assetRoot}/metadata.json`, 'utf8'));
  for (const [key, filename] of [
    ['stand', 'pomelo-stem-mascot-stand.glb'],
    ['kit', 'pomelo-stem-mascot-kit.glb'],
  ]) {
    const {bytes, document} = readGlb(filename);
    const rootIndices = document.scenes[document.scene ?? 0].nodes;
    assert.equal(rootIndices.length, 1);
    assert.equal(document.nodes[rootIndices[0]].name, 'PomeloStemMascot');
    assert.deepEqual(measure(document, bytes), metadata.additional_exports[key]);
  }
  assert.ok(metadata.metrics.triangles < 40000);
  assert.ok(metadata.metrics.glb_bytes < 2 * 1024 ** 2);
  assert.ok(metadata.additional_exports.stand.triangles < 40000);
  assert.ok(metadata.additional_exports.kit.glb_bytes < 5 * 1024 ** 2);
});
