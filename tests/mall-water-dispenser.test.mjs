import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { loadCatalog } from '../scripts/catalog.mjs';

const folder = 'models/mall-water-dispenser';
const metadata = JSON.parse(fs.readFileSync(`${folder}/metadata/mall-water-dispenser.json`));

test('mall water dispenser has one additive catalog registration and synchronized measured report', () => {
  const asset = loadCatalog().collections.flatMap(c => c.assets).find(a => a.id === 'mall-water-dispenser');
  assert.ok(asset);
  const bytes = fs.readFileSync(`${folder}/exports/optimized.glb`);
  const report = JSON.parse(fs.readFileSync(`${folder}/reports/assets.json`));
  assert.equal(asset.root, 'ASSET_MallWaterDispenser');
  assert.equal(metadata.backlog_id, 'shopping-mall-009');
  assert.equal(metadata.metrics.sha256, createHash('sha256').update(bytes).digest('hex'));
  assert.equal(metadata.metrics.sha256, report.sha256);
  assert.ok(report.triangles < 12000 && report.glb_bytes < 1000000);
  for (const name of ['hero', 'front', 'rear', 'side', 'open']) {
    const png = fs.readFileSync(`${folder}/previews/${name}.png`);
    assert.equal(png.subarray(0, 8).toString('hex'), '89504e470d0a1a0a');
  }
});

test('asset source contract names independently editable fixture parts', () => {
  assert.deepEqual(metadata.interaction.clips, ['ServicePanelOpenClose']);
  assert.match(metadata.accuracy_notes, /cold and ambient only/i);
  assert.match(metadata.accuracy_notes, /not.*certification/i);
});
