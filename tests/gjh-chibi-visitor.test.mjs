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
    assert.deepEqual(asset.details.display.previewCameraDirection, [0, 0.1, 1]);
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
  assert.deepEqual(metadata.metrics, {
    glb_bytes: 705712,
    triangles: 39332,
    vertices: 20062,
    animations: 0,
  });
  assert.deepEqual(metadata.geometry.bounds_glTF_m, {
    min: [-0.43915856559797767, 9.761146821385402e-10, -0.23486734294780168],
    max: [0.3614102843854713, 0.9999999957435435, 0.23814682057993303],
    dimensions: [0.8005688499834489, 0.9999999947674288, 0.47301416352773473],
  });
  assert.ok(Math.abs(metadata.geometry.height_metres - 1) < 1e-8);
  assert.equal(metadata.geometry.raised_left_hand_max_y_metres, 0.5710543547765367);
  assert.equal(metadata.geometry.feet_at_floor_y_metres, 0);
  assert.equal(asset.animations, 0);
  assert.equal(metadata.validation.errors, 0);
  assert.equal(metadata.validation.warnings, 0);
  assert.equal(metadata.paths.glb, 'exports/' + id + '.glb');
  assert.equal(metadata.paths.source, 'gjh-chibi-visitor.blend');
  assert.equal(metadata.paths.kit_glb, 'exports/gjh-chibi-visitor-blender-kit.glb');
  assert.equal(metadata.paths.stand_glb, 'exports/gjh-chibi-visitor-blender-stand.glb');
  assert.equal(fs.existsSync(assetRoot + '/generate.py'), true);
  assert.ok(fs.statSync(assetRoot + '/generate.py').size > 0);
  assert.equal(fs.existsSync(assetRoot + '/convert-previews.py'), true);
  assert.ok(fs.statSync(assetRoot + '/convert-previews.py').size > 0);
  assert.ok(fs.statSync(assetRoot + '/gjh-chibi-visitor.blend').size > 0);
  assert.equal(fs.existsSync(assetRoot + '/exports/' + id + '.glb'), true);
  assert.equal(fs.existsSync(assetRoot + '/' + metadata.paths.stand_glb), true);
  assert.equal(fs.existsSync(assetRoot + '/exports/gjh-chibi-visitor-blender-kit.glb'), true);
  const waveBytes = fs.readFileSync(assetRoot + '/exports/' + id + '.glb');
  const wave = measure(readDocument(waveBytes), waveBytes);
  assert.deepEqual(wave, metadata.metrics);
  assert.ok(wave.triangles < 40000 && wave.glb_bytes < 2 * 1024 * 1024);
  const waveDocument = readDocument(waveBytes);
  const waveRoot = waveDocument.nodes[waveDocument.scenes[waveDocument.scene ?? 0].nodes[0]];
  assert.equal(waveRoot.extras.pose, 'wave');
  const standBytes = fs.readFileSync(assetRoot + '/' + metadata.paths.stand_glb);
  const stand = measure(readDocument(standBytes), standBytes);
  assert.deepEqual(stand, { glb_bytes: 705616, triangles: 39332, vertices: 20062, animations: 0 });
  assert.ok(stand.triangles < 40000 && stand.glb_bytes < 2 * 1024 * 1024);
  const standDocument = readDocument(standBytes);
  const standRoot = standDocument.nodes[standDocument.scenes[standDocument.scene ?? 0].nodes[0]];
  assert.equal(standRoot.extras.pose, 'stand');
  const kitPath = assetRoot + '/' + metadata.paths.kit_glb;
  const kitBytes = fs.readFileSync(kitPath);
  const kit = measure(readDocument(kitBytes), kitBytes);
  assert.deepEqual(kit, { glb_bytes: 3083148, triangles: 167452, vertices: 95936, animations: 0 });
  assert.ok(kit.triangles < 175000 && kit.glb_bytes < 5 * 1024 * 1024);
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
