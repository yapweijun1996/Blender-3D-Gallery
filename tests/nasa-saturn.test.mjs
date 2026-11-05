import test from 'node:test';
import assert from 'node:assert/strict';
import { loadCatalog } from '../scripts/catalog.mjs';

test('NASA Saturn remains a distinct attributed candidate outside the solar demo', () => {
  const assets = loadCatalog().collections.flatMap(collection => collection.assets);
  const candidate = assets.find(asset => asset.id === 'nasa-saturn');
  assert.ok(candidate);
  assert.equal(candidate.collectionId, 'nasa-candidates');
  assert.notEqual(candidate.family, 'solar-system');
  assert.equal(candidate.triangles, 3328);
  assert.match(candidate.details.attribution[0].credit, /NASA Visualization/);
  assert.ok(assets.some(asset => asset.id === 'solar-saturn' && asset.family === 'solar-system'));
});
