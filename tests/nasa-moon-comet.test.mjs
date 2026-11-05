import test from 'node:test';
import assert from 'node:assert/strict';
import { loadCatalog } from '../scripts/catalog.mjs';

test('NASA Moon and Tempel 1 are distinct, attributed candidates outside the solar demo', () => {
  const assets = loadCatalog().collections.flatMap(c => c.assets);
  for (const id of ['nasa-moon', 'nasa-tempel-1']) {
    const asset = assets.find(a => a.id === id);
    assert.ok(asset, id);
    assert.equal(asset.collectionId, 'nasa-candidates');
    assert.notEqual(asset.family, 'solar-system');
    assert.match(asset.details.attribution[0].credit, /NASA/);
    assert.ok(asset.triangles > 0);
  }
  assert.ok(assets.some(a => a.id === 'solar-moon'));
  assert.ok(assets.some(a => a.id === 'solar-comet'));
});
