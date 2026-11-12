import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { loadCatalog } from '../scripts/catalog.mjs';

const folder = 'models/mall-floor-direction-sign';
const id = 'mall-floor-direction-sign';
const catalog = loadCatalog();
const asset = catalog.collections.flatMap(c => c.assets).find(a => a.id === id);
const bytes = fs.readFileSync(`${folder}/exports/${id}.glb`);
const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
const report = JSON.parse(fs.readFileSync(`${folder}/reports/assets.json`));
const sources = JSON.parse(fs.readFileSync(`${folder}/reports/sources.json`));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);
const root = gltf.scene.getObjectByName('ASSET_MallFloorDirectionSign');
const labels = ['FloorIdentity', 'DirectionDining', 'DirectionShops', 'DirectionCinema', 'DirectionFacilities'];
const meshes = node => { const result = []; node?.traverse(o => { if (o.isMesh) result.push(o); }); return result; };

test('floor direction sign is registered before queue kit with synchronized measured metadata', () => {
  assert.ok(asset);
  assert.equal(asset.downloadable, false);
  assert.equal(asset.license, metadata.rights);
  assert.equal(asset.root, root.name);
  assert.equal(metadata.display.previewRotationY, Math.PI);
  const index = catalog.collections.findIndex(c => c.id === id);
  assert.equal(catalog.collections[index + 1].id, 'mall-queue-stanchions');
  assert.equal(bytes.length, metadata.metrics.glb_bytes);
  assert.equal(createHash('sha256').update(bytes).digest('hex'), metadata.metrics.sha256);
  assert.equal(report.sha256, metadata.metrics.sha256);
  assert.deepEqual(metadata.validation, report.validation);
  assert.equal(report.validation.errors, 0);
  assert.equal(report.validation.warnings, 0);
});

test('floor-centred, metre-scale GLB has six independent mesh-bearing modules', () => {
  assert.equal(root.children.length, 6);
  const bounds = new Box3().setFromObject(root);
  assert.ok(Math.abs(bounds.min.y) < .001);
  assert.ok(Math.abs((bounds.max.x + bounds.min.x) / 2) < .001);
  const dimensions = bounds.getSize(new Vector3());
  assert.ok(dimensions.x > 1.2 && dimensions.x < 1.3);
  assert.ok(dimensions.y > 2.5 && dimensions.y < 2.6);
  assert.ok(dimensions.z > .5 && dimensions.z < .6);
  for (const name of ['SignStructure', ...labels]) {
    const node = root.getObjectByName(name);
    assert.equal(node.parent, root);
    assert.ok(meshes(node).length > 0);
    assert.ok(meshes(node).every(m => m.geometry.attributes.position.count > 0));
  }
});

test('each label cartridge can be removed and replaced without changing the structure or other labels', () => {
  for (const name of labels) {
    const target = root.getObjectByName(name);
    const siblings = root.children.filter(o => o !== target).map(node => ({ node, meshes: meshes(node) }));
    const before = root.children.slice();
    target.visible = false;
    for (const { node } of siblings) assert.equal(node.visible, true);
    target.visible = true;
    const replacement = target.clone(true);
    root.remove(target);
    root.add(replacement);
    assert.equal(target.parent, null);
    assert.ok(meshes(replacement).length > 0);
    for (const { node, meshes: original } of siblings) {
      assert.equal(node.parent, root);
      assert.deepEqual(meshes(node), original);
    }
    root.remove(replacement);
    root.add(target);
    root.children = before;
  }
});

test('reopened source retains editable text and original destination labels, with no live editing claim', () => {
  assert.equal(sources.source_reopened, 'PASS');
  for (const [name, title] of [['DirectionDining','Dining'], ['DirectionShops','Shops'],
    ['DirectionCinema','Cinema'], ['DirectionFacilities','Restrooms']]) {
    assert.ok(Object.values(sources.groups[name].editable_text).includes(title));
  }
  assert.ok(Object.values(sources.groups.FloorIdentity.editable_text).includes('02'));
  assert.match(metadata.replacement.note, /No live label editing/);
});
