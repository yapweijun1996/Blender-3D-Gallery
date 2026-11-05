import test from 'node:test';
import assert from 'node:assert/strict';
import { loadCatalog } from '../scripts/catalog.mjs';
import { solarSceneAssets } from '../src/solar/assets.js';

test('solar scene uses attributed NASA assets without losing physical facts', () => {
  const all = loadCatalog().collections.flatMap(c => c.assets);
  const scene = solarSceneAssets(all);
  assert.equal(scene.length, 17);
  const expected = {sun:'nasa-sun', mercury:'nasa-mercury', venus:'nasa-venus', earth:'nasa-earth', mars:'nasa-mars', jupiter:'nasa-jupiter', saturn:'nasa-saturn', uranus:'nasa-uranus', neptune:'nasa-neptune', moon:'nasa-moon', pluto:'nasa-pluto', 'asteroid-01':'nasa-vesta', 'asteroid-02':'nasa-eros', comet:'nasa-tempel-1'};
  for (const [id, assetId] of Object.entries(expected)) {
    const asset = scene.find(a => a.solarId === id);
    const base = all.find(a => a.solarId === id);
    assert.equal(asset.id, assetId);
    assert.deepEqual(asset.details.scientific_properties, base.details.scientific_properties);
    assert.ok(asset.details.attribution.some(c => c.credit.includes('NASA')));
  }
  assert.equal(scene.find(a => a.solarId === 'asteroid-03').id, 'solar-asteroid-03');
  assert.ok(scene.find(a => a.solarId === 'saturn').modelScale > 2);
  assert.throws(() => solarSceneAssets(all.filter(a => a.id !== 'nasa-earth')), /Missing solar model/);
});
