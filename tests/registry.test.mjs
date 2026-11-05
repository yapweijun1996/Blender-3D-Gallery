import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { loadCatalog, validateCatalog, validateMetadata } from '../scripts/catalog.mjs';
import { loadDemos, validateDemos } from '../scripts/demo-registry.mjs';

const raw = JSON.parse(fs.readFileSync('models/catalog.json', 'utf8'));
const demos = JSON.parse(fs.readFileSync('data/demos.json', 'utf8'));
const mutate = (change) => { const value = structuredClone(raw); change(value); return value; };

test('catalog enrichment preserves all 39 assets and supplies measured metadata', () => {
  const catalog = loadCatalog();
  const expected = raw.collections.flatMap(collection => collection.assets);
  const actual = catalog.collections.flatMap(collection => collection.assets);
  assert.equal(actual.length, 39);
  assert.deepEqual(actual.map(({ id, file, thumbnail }) => ({ id, file, thumbnail })), expected.map(({ id, file, thumbnail }) => ({ id, file, thumbnail })));
  for (const collection of catalog.collections) for (const asset of collection.assets) {
    assert.equal(asset.slug, asset.id);
    assert.equal(asset.collectionId, collection.id);
    assert.equal(asset.collectionName, collection.name);
    assert.ok(Number.isInteger(asset.vertices) && asset.vertices > 0);
    assert.ok(Number.isInteger(asset.materials) && asset.materials > 0);
    assert.ok(Number.isInteger(asset.animations) && asset.animations >= 0);
    assert.equal(asset.format, 'GLB');
    assert.equal(asset.downloadable, true);
    assert.ok(asset.license.length > 0);
  }
  assert.equal(actual.find(asset => asset.id === 'solar-earth').license, actual.find(asset => asset.id === 'solar-earth').details.rights);
});

test('catalog rejects duplicate identities and slugs across collections', () => {
  for (const change of [
    value => { value.collections[1].id = value.collections[0].id; },
    value => { value.collections[1].slug = value.collections[0].id; },
    value => { value.collections[1].assets[0].id = value.collections[0].assets[0].id; },
    value => { value.collections[1].assets[0].slug = value.collections[0].assets[0].id; },
  ]) assert.throws(() => validateCatalog(mutate(change)), /duplicate/);
});

test('catalog rejects malformed required and optional values before coercion', () => {
  for (const [field, values] of Object.entries({
    id: [null, 123, '', 'two words', 'bad--slug'],
    slug: [null, 123, '', '../slug'],
    name: [null, 123, '', '  '],
    category: [null, [], '', false],
    tags: [null, 'tag', [1]],
    downloadable: [null, 'false', 0],
    license: [null, false, ''],
  })) for (const value of values) {
    assert.throws(() => validateCatalog(mutate(catalog => { catalog.collections[0].assets[0][field] = value; })), /Invalid/);
  }
  for (const value of [null, {}, { collections: [] }, { collections: [null] }]) assert.throws(() => validateCatalog(value), /Invalid/);
});

test('catalog paths reject traversal, URL schemes, query fragments and encoded separators', () => {
  for (const file of ['../outside.glb', '/models/a.glb', 'models/../outside.glb', 'models/./a.glb', 'models//a.glb', 'models/a.glb?x=1', 'models/a.glb#x', 'models/%2e%2e/a.glb', 'models\\a.glb', 'https://example.com/a.glb', 'javascript:alert(1)', 'models/a.js']) {
    assert.throws(() => validateCatalog(mutate(catalog => { catalog.collections[0].assets[0].file = file; })), /Unsafe/);
  }
  assert.throws(() => validateCatalog(mutate(catalog => { catalog.collections[0].assets[0].thumbnail = 'models/a.html'; })), /Unsafe/);
});

test('optional defaults are explicit and false download permission is retained', () => {
  const input = mutate(catalog => {
    const asset = catalog.collections[0].assets[0];
    asset.downloadable = false;
    asset.category = '  Table   furniture  ';
    asset.tags = ['wood', 'wood', ' cue   sport '];
  });
  const asset = validateCatalog(input).collections[0].assets[0];
  assert.equal(asset.downloadable, false);
  assert.equal(asset.category, 'Table furniture');
  assert.deepEqual(asset.tags, ['wood', 'cue sport']);
  assert.deepEqual(validateCatalog(raw).collections[0].assets[1].tags, []);
  assert.equal(raw.collections[0].assets[0].slug, undefined, 'validation must not mutate the source registry');
});

test('catalog refuses symlink references outside the model directory', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'b3g-registry-'));
  try {
    fs.mkdirSync(path.join(root, 'models'));
    fs.writeFileSync(path.join(root, 'outside.webp'), 'outside');
    const input = { collections: [{ id: 'test', name: 'Test', assets: [{ id: 'test', name: 'Test', category: 'Test', file: 'models/test.glb', thumbnail: 'models/test.webp' }] }] };
    fs.writeFileSync(path.join(root, 'models/catalog.json'), JSON.stringify(input));
    fs.symlinkSync(path.join(root, 'outside.webp'), path.join(root, 'models/test.webp'));
    assert.throws(() => loadCatalog(root), /unsafe asset/);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('demo registry resolves verified posters and legacy launch routes', () => {
  const catalog = loadCatalog();
  const actual = loadDemos(process.cwd(), catalog);
  assert.deepEqual(actual.map(demo => demo.route), ['?page=game', '?page=solar']);
  assert.deepEqual(actual.map(demo => demo.category), ['Game', 'Simulation']);
  for (const demo of actual) {
    const asset = catalog.collections.flatMap(collection => collection.assets).find(asset => asset.id === demo.thumbnailAssetId);
    assert.equal(demo.thumbnail, asset.thumbnail);
    assert.deepEqual(demo.technologies, ['Three.js']);
    assert.equal(demo.status, 'available');
  }
});

test('demo schema rejects duplicates, missing posters, invalid routes and malformed values', () => {
  const catalog = validateCatalog(raw);
  for (const change of [
    value => { value[1].id = value[0].id; },
    value => { value[1].slug = value[0].slug; },
    value => { value[0].route = 'javascript:alert(1)'; },
    value => { value[0].route = 'https://example.com'; },
    value => { value[0].route = '?page=unknown'; },
    value => { value[1].route = value[0].route; },
    value => { value[0].thumbnailAssetId = 'missing'; },
    value => { value[0].category = null; },
    value => { value[0].technologies = 'Three.js'; },
    value => { value[0].status = true; },
    value => { value[0].title = ''; },
    value => { value[0].tags = [null]; },
  ]) {
    const input = structuredClone(demos); change(input);
    assert.throws(() => validateDemos(input, catalog), /Invalid/);
  }
  assert.throws(() => validateDemos([], catalog), /Invalid/);
  assert.throws(() => validateDemos([null], catalog), /Invalid/);
});


test('legacy IDs cannot be claimed by a different canonical model slug', () => {
  assert.throws(() => validateCatalog(mutate(catalog => {
    catalog.collections[0].assets[0].slug = catalog.collections[0].assets[1].id;
    catalog.collections[0].assets[1].slug = 'different-slug';
  })), /Ambiguous/);
});

test('metadata validates the display and text fields consumed by existing viewers', () => {
  const earth = JSON.parse(fs.readFileSync('models/solar-system/metadata/earth.json', 'utf8'));
  assert.equal(validateMetadata(earth, 'earth'), earth);
  for (const change of [
    value => { value.id = 'wrong'; },
    value => { value.display = null; },
    value => { value.display.previewRotationY = '0'; },
    value => { value.attribution = {}; },
    value => { value.attribution = [{credit: null}]; },
    value => { value.scientific_properties.diameter_km = '12756'; },
    value => { value.scientific_properties = []; },
  ]) {
    const value = structuredClone(earth); change(value);
    assert.throws(() => validateMetadata(value, 'earth'), /metadata/);
  }
});
