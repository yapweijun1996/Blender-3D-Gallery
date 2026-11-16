import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { loadCatalog } from '../scripts/catalog.mjs';

const root = 'models/gjh-chibi-visitor';
const unityVariants = ['terra', 'sol', 'astra'];
const expectedIds = [
  'gjh-chibi-visitor-blender',
  ...unityVariants.map(variant => 'gjh-chibi-visitor-' + variant),
];
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'gjh-chibi-visitor');
const visitorLicense = catalog.collections
  .flatMap(item => item.assets)
  .find(asset => asset.id === 'gjh-mall-visitor').license;

test('GJH Chibi Visitor registers the Blender primary before three earlier Unity experiments', () => {
  assert.ok(collection);
  assert.match(collection.name, /GJH Chibi Visitor/);
  assert.match(collection.description, /primary Blender/i);
  assert.match(collection.description, /earlier.*Unity/i);
  assert.equal(collection.assets.length, 4);
  assert.deepEqual(collection.assets.map(asset => asset.id), expectedIds);
  assert.deepEqual(
    collection.assets.map(asset => asset.name),
    [
      'GJH Chibi Visitor',
      'GJH Chibi Visitor (Unity experiment, terra)',
      'GJH Chibi Visitor (Unity experiment, sol)',
      'GJH Chibi Visitor (Unity experiment, astra)',
    ],
  );
  for (const asset of collection.assets) {
    assert.equal(asset.category, 'Characters');
    assert.equal(asset.root, 'GJHChibiVisitor');
    assert.equal(asset.downloadable, false);
    assert.equal(asset.license, visitorLicense);
    assert.deepEqual(asset.details.display.previewCameraDirection, [0, 0.15, 1]);
  }
  assert.equal(fs.existsSync(root + '/catalog-entry.draft.json'), false);
});

test('gjh-chibi-visitor-blender: source, measured metrics, kit and previews are complete', () => {
  const id = 'gjh-chibi-visitor-blender';
  const asset = collection.assets[0];
  const assetRoot = root + '/blender';
  const metadata = JSON.parse(fs.readFileSync(assetRoot + '/metadata.json', 'utf8'));
  assert.equal(asset.id, id);
  assert.equal(metadata.id, id);
  assert.equal(metadata.name, 'GJH Chibi Visitor');
  assert.equal(metadata.category, 'Characters');
  assert.equal(metadata.status, 'validated');
  assert.equal(metadata.blender_version, '5.2.3 LTS');
  assert.equal(metadata.generator, 'generate.py');
  assert.equal(metadata.rights, visitorLicense);
  assert.match(metadata.accuracy_notes, /not redistributed/i);
  assert.deepEqual(asset.details, metadata);
  assert.equal(metadata.metrics.glb_bytes, asset.bytes);
  assert.equal(metadata.metrics.triangles, asset.triangles);
  assert.equal(metadata.metrics.vertices, asset.vertices);
  assert.equal(metadata.metrics.animations, 0);
  assert.equal(asset.animations, 0);
  assert.equal(metadata.validation.errors, 0);
  assert.equal(metadata.validation.warnings, 0);
  assert.equal(metadata.paths.glb, 'exports/' + id + '.glb');
  assert.equal(metadata.paths.source, 'gjh-chibi-visitor.blend');
  assert.equal(metadata.paths.kit_glb, 'exports/gjh-chibi-visitor-blender-kit.glb');
  assert.equal(fs.existsSync(assetRoot + '/generate.py'), true);
  assert.ok(fs.statSync(assetRoot + '/generate.py').size > 0);
  assert.ok(fs.statSync(assetRoot + '/gjh-chibi-visitor.blend').size > 0);
  assert.equal(fs.existsSync(assetRoot + '/exports/' + id + '.glb'), true);
  assert.equal(fs.existsSync(assetRoot + '/exports/gjh-chibi-visitor-blender-kit.glb'), true);
  for (const view of ['front', 'side', 'back', '3q']) {
    const previewPath = assetRoot + '/previews/' + view + '.webp';
    const bytes = fs.readFileSync(previewPath);
    assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
    assert.equal(bytes.toString('ascii', 8, 12), 'WEBP');
  }
  assert.ok(fs.statSync(assetRoot + '/previews/front.webp').size < 150 * 1024);
});

for (const variant of unityVariants) {
  const id = 'gjh-chibi-visitor-' + variant;
  const asset = collection.assets.find(item => item.id === id);
  const metadata = JSON.parse(fs.readFileSync(root + '/' + variant + '/metadata.json', 'utf8'));

  test(id + ': earlier Unity experiment paths and measured metadata are unchanged', () => {
    assert.equal(metadata.id, id);
    assert.equal(metadata.name, 'GJH Chibi Visitor (Unity experiment, ' + variant + ')');
    assert.equal(metadata.category, 'Characters');
    assert.equal(metadata.status, 'validated');
    assert.equal(metadata.unity_version, '6000.0.85f2');
    assert.equal(metadata.gltfast_version, '6.21.0');
    assert.equal(metadata.author, 'Yap Wei Jun project / ' + variant + ' AI model');
    assert.equal(metadata.rights, visitorLicense);
    assert.match(metadata.description, /earlier experimental comparison built in Unity/i);
    assert.ok(metadata.accuracy_notes.includes('character-sheet image was not available'));
    assert.deepEqual(asset.details, metadata);
    assert.equal(metadata.metrics.glb_bytes, asset.bytes);
    assert.equal(metadata.metrics.triangles, asset.triangles);
    assert.equal(metadata.metrics.vertices, asset.vertices);
    assert.equal(metadata.metrics.animations, asset.animations);
    assert.equal(asset.animations, 0);
    assert.equal(metadata.validation.errors, 0);
    assert.equal(metadata.validation.warnings, 0);
    assert.equal(metadata.paths.glb, 'exports/' + id + '.glb');
    assert.equal(metadata.paths.source, 'source/ChibiBuilder.cs');
    assert.ok(fs.statSync(root + '/' + variant + '/source/ChibiBuilder.cs').size > 0);
    assert.equal(fs.existsSync(root + '/' + variant + '/exports/' + id + '.glb'), true);
    for (const view of ['front', 'side', 'back', '3q']) {
      const previewPath = root + '/' + variant + '/previews/' + view + '.webp';
      const bytes = fs.readFileSync(previewPath);
      assert.equal(bytes.toString('ascii', 0, 4), 'RIFF');
      assert.equal(bytes.toString('ascii', 8, 12), 'WEBP');
    }
    assert.ok(fs.statSync(root + '/' + variant + '/previews/front.webp').size < 150 * 1024);
  });
}
