import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
import {loadCatalog} from '../scripts/catalog.mjs';

const require = createRequire(import.meta.url);
const validator = require('gltf-validator');
const root = 'models/pomelo-stem';
const assetRoot = `${root}/mascot`;
const catalog = loadCatalog();
const collection = catalog.collections.find(item => item.id === 'pomelo-stem');
const expectedId = 'pomelo-stem-mascot';
const expectedLicense = catalog.collections
  .flatMap(item => item.assets)
  .find(asset => asset.id === 'gjh-chibi-visitor-blender').license;
const expectedClips = [
  {name: 'Idle', duration_seconds: 2.5},
  {name: 'Wave', duration_seconds: 1.5},
  {name: 'Blink', duration_seconds: 3},
  {name: 'Cheer', duration_seconds: 1.600000023841858},
  {name: 'Jump', duration_seconds: 1.2000000476837158},
];

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

function clipDetails(document) {
  return (document.animations ?? []).map(animation => {
    const ranges = animation.samplers.map(sampler => {
      const accessor = document.accessors[sampler.input];
      return [accessor.min[0], accessor.max[0]];
    });
    const start = Math.min(...ranges.map(range => range[0]));
    const end = Math.max(...ranges.map(range => range[1]));
    return {name: animation.name, duration_seconds: end - start};
  });
}

function assertSkinnedCharacter(document, expectedJointCount) {
  const scene = document.scenes[document.scene ?? 0];
  const roots = scene.nodes;
  const anchorIndex = roots.find(index => document.nodes[index].name === 'PomeloStemMascot');
  assert.notEqual(anchorIndex, undefined, 'named rig anchor is a scene root');
  assert.equal(document.skins.length, 1);
  assert.equal(document.skins[0].joints.length, expectedJointCount);
  const meshNodes = document.nodes.filter(node => node.mesh !== undefined);
  assert.ok(meshNodes.length > 0);
  for (const node of meshNodes) {
    assert.equal(node.skin, 0, `${node.name} uses the character skin`);
    for (const primitive of document.meshes[node.mesh].primitives) {
      assert.ok(primitive.attributes.JOINTS_0 !== undefined, `${node.name} has joint attributes`);
      assert.ok(primitive.attributes.WEIGHTS_0 !== undefined, `${node.name} has weight attributes`);
    }
  }
}

function assertMeasuredExport(document, bytes, expected, expectedJointCount, metadata) {
  assert.deepEqual(measure(document, bytes), {
    glb_bytes: expected.glb_bytes,
    triangles: expected.triangles,
    vertices: expected.vertices,
    animations: expected.animations,
  });
  assertSkinnedCharacter(document, expectedJointCount);
  assert.deepEqual(clipDetails(document), expected.animation_clips);
  assert.equal(document.animations.length, 3);
  assert.equal(expected.animations, 3);
  assert.deepEqual(metadata.animation_clips, expectedClips);
}

test('Pomelo STEM registers one rigged character asset', () => {
  assert.ok(collection);
  assert.equal(collection.name, 'Pomelo STEM');
  assert.equal(collection.assets.length, 1);
  assert.deepEqual(collection.assets.map(asset => asset.id), [expectedId]);

  const asset = collection.assets[0];
  const metadata = JSON.parse(fs.readFileSync(`${assetRoot}/metadata.json`, 'utf8'));
  assert.equal(asset.name, 'Pomelo STEM Mascot');
  assert.equal(asset.category, 'Characters');
  assert.equal(asset.root, 'PomeloStemMascot');
  assert.equal(asset.downloadable, false);
  assert.equal(asset.license, expectedLicense);
  assert.match(asset.description, /original.*fruit mascot/i);
  assert.match(asset.description, /skinned/i);
  assert.match(asset.description, /Idle, Wave, Blink, Cheer, and Jump/i);
  assert.ok(asset.tags.includes('rigged'));
  assert.ok(asset.tags.includes('animated'));
  assert.equal(asset.animations, 5);
  assert.deepEqual(asset.details.display.previewCameraDirection, [0, 0, 1]);
  assert.equal(asset.details.display.front_axis, '+Z');
  assert.equal(fs.existsSync(`${root}/catalog-entry.draft.json`), false);
  assert.deepEqual(asset.details, metadata);
});

test('Pomelo STEM metadata matches the registered animated GLB', () => {
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
  assert.deepEqual(measure(document, bytes), metadata.metrics);
  assert.equal(metadata.metrics.animations, 5);
  assert.equal(metadata.blender_version, '5.2.3 LTS');
  assert.equal(metadata.skeleton.joint_count, 20);
  assert.deepEqual(metadata.animation_clips, expectedClips);
  assert.equal(metadata.validation.errors, 0);
  assert.equal(metadata.validation.warnings, 0);
  assert.equal(metadata.additional_exports.stand.joint_count, 20);
  assert.equal(metadata.additional_exports.kit.joint_count, 26);
  assert.equal(asset.animations, metadata.animation_clips.length);

  assertSkinnedCharacter(document, metadata.skeleton.joint_count);
  assert.deepEqual(clipDetails(document), metadata.animation_clips);
  assert.ok(Math.abs(metadata.geometry.bounds_glTF_m.dimensions[1] - metadata.geometry.height_metres) < 1e-8);
  for (const filename of ['generate.py', 'convert-previews.py', 'pomelo-stem-mascot.blend',
    'exports/pomelo-stem-mascot-stand.glb', 'exports/pomelo-stem-mascot-kit.glb'])
    assert.ok(fs.statSync(`${assetRoot}/${filename}`).size > 0, filename);
  for (const filename of metadata.paths.animation_previews)
    assert.ok(fs.statSync(`${assetRoot}/${filename}`).size > 0, filename);
  assert.ok(fs.statSync(`${assetRoot}/previews/front.webp`).size < 150 * 1024);
  for (const view of ['front', 'side', 'back', '3q', 'expressions']) {
    const preview = fs.readFileSync(`${assetRoot}/previews/${view}.webp`);
    assert.equal(preview.toString('ascii', 0, 4), 'RIFF');
    assert.equal(preview.toString('ascii', 8, 12), 'WEBP');
  }
});

test('Pomelo stand and expression kit keep the rig, clips, mounts, and size budgets', () => {
  const metadata = JSON.parse(fs.readFileSync(`${assetRoot}/metadata.json`, 'utf8'));
  for (const [key, filename, jointCount] of [
    ['stand', 'pomelo-stem-mascot-stand.glb', 20],
    ['kit', 'pomelo-stem-mascot-kit.glb', 26],
  ]) {
    const {bytes, document} = readGlb(filename);
    const measured = measure(document, bytes);
    const expected = metadata.additional_exports[key];
    assert.deepEqual(measured, {
      glb_bytes: expected.glb_bytes,
      triangles: expected.triangles,
      vertices: expected.vertices,
      animations: expected.animations,
    });
    assertSkinnedCharacter(document, jointCount);
    assert.deepEqual(clipDetails(document), expectedClips);
    const rootIndices = document.scenes[document.scene ?? 0].nodes;
    assert.ok(rootIndices.some(index => document.nodes[index].name === 'PomeloStemMascot'));
    if (key === 'stand') {
      assert.ok(measured.triangles < 40000);
      assert.ok(measured.glb_bytes < 2 * 1024 ** 2);
    }
    if (key === 'kit') {
      assert.ok(measured.glb_bytes < 5 * 1024 ** 2);
      const jointNames = document.skins[0].joints.map(index => document.nodes[index].name);
      assert.deepEqual(jointNames.filter(name => /^Mount_\d\d_Expression_/.test(name)), expected.expression_mounts);
    }
  }
  const defaultGlb = readGlb('pomelo-stem-mascot.glb');
  const defaultMetrics = measure(defaultGlb.document, defaultGlb.bytes);
  assert.ok(defaultMetrics.triangles < 40000);
  assert.ok(defaultMetrics.glb_bytes < 2 * 1024 ** 2);
});

test('all Pomelo GLBs pass Khronos validation with zero errors and warnings', async () => {
  for (const filename of [
    'pomelo-stem-mascot.glb',
    'pomelo-stem-mascot-stand.glb',
    'pomelo-stem-mascot-kit.glb',
  ]) {
    const bytes = fs.readFileSync(`${assetRoot}/exports/${filename}`);
    const result = await validator.validateBytes(new Uint8Array(bytes), {uri: filename, maxIssues: 1000});
    assert.equal(result.issues.numErrors, 0, `${filename} errors`);
    assert.equal(result.issues.numWarnings, 0, `${filename} warnings`);
  }
});
