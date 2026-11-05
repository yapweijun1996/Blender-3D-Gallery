import test from 'node:test';
import assert from 'node:assert/strict';
import { loadCatalog } from '../scripts/catalog.mjs';

test('NASA solar candidates are attributed, discoverable and excluded from the solar demo', () => {
  const catalog = loadCatalog();
  const collection = catalog.collections.find(c => c.id === 'nasa-candidates');
  for (const id of ['sun', 'mercury', 'venus', 'earth', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'vesta', 'eros']) {
    const asset = collection.assets.find(a => a.id === `nasa-${id}`);
    assert.ok(asset, id);
    assert.notEqual(asset.family, 'solar-system');
    assert.match(asset.details.attribution[0].credit, /NASA/);
    assert.ok(asset.bytes > 0 && asset.triangles > 0);
  }
});
