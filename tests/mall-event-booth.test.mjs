import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { loadCatalog } from '../scripts/catalog.mjs';

const folder = 'models/mall-event-booth';
const asset = loadCatalog().collections.flatMap(c => c.assets).find(a => a.id === 'mall-event-booth');
const bytes = fs.readFileSync(`${folder}/exports/mall-event-booth.glb`);
const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/mall-event-booth.json`));
const gltf = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
gltf.scene.updateMatrixWorld(true);

function named(name) { return gltf.scene.getObjectByName(name); }
function meshDescendant(node) { let found = null; node?.traverse(o => { if (o.isMesh) found = o; }); return found; }

test('event booth is registered and measured metadata is synchronized', () => {
  assert.ok(asset);
  assert.equal(asset.root, 'ASSET_MallEventBooth');
  assert.equal(metadata.display.previewRotationY, Math.PI, 'gallery camera faces the poster front');
  assert.equal(metadata.metrics.glb_bytes, bytes.length);
  assert.equal(metadata.metrics.sha256, createHash('sha256').update(bytes).digest('hex'));
  assert.equal(metadata.metrics.sha256, JSON.parse(fs.readFileSync(`${folder}/reports/assets.json`)).sha256);
  assert.equal(metadata.validation.errors, 0);
  assert.equal(metadata.validation.warnings, 0);
});

test('poster and display are real independent mesh-bearing groups', () => {
  const root = named('ASSET_MallEventBooth');
  const poster = named('PosterPanel');
  const display = named('DisplayContent');
  assert.ok(root && poster && display);
  assert.ok(meshDescendant(named('BoothStructure')));
  assert.ok(meshDescendant(poster));
  assert.ok(meshDescendant(display));
  assert.notEqual(meshDescendant(poster), meshDescendant(display));
  assert.equal(named('BoothGeometry'), undefined);
  assert.equal(poster.parent, root);
  assert.equal(display.parent, root);
});

test('hiding/replacing either module leaves the other and booth structure intact', () => {
  const root = named('ASSET_MallEventBooth');
  const structure = named('BoothStructure');
  const structureMesh = meshDescendant(structure);
  for (const [targetName, otherName] of [['PosterPanel', 'DisplayContent'], ['DisplayContent', 'PosterPanel']]) {
    const target = named(targetName), other = named(otherName);
    const otherMesh = meshDescendant(other);
    target.visible = false;
    assert.equal(other.visible, true);
    assert.equal(structure.visible, true);
    target.visible = true;
    const index = root.children.indexOf(target);
    const replacement = target.clone(true);
    root.remove(target);
    root.add(replacement);
    assert.equal(target.parent, null);
    assert.equal(other.parent, root);
    assert.equal(structure.parent, root);
    assert.equal(meshDescendant(other), otherMesh);
    assert.equal(meshDescendant(structure), structureMesh);
    assert.ok(meshDescendant(replacement));
    root.remove(replacement);
    root.add(target);
    root.children.splice(root.children.indexOf(target), 1);
    root.children.splice(index, 0, target);
  }
});
