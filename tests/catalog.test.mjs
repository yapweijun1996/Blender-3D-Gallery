import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { loadCatalog } from '../scripts/catalog.mjs';

function glbJson(file) {
  const bytes = fs.readFileSync(file);
  return JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString('utf8'));
}

test('billiards catalog includes each physical asset and the legacy scene', () => {
  const catalog = loadCatalog();
  const assets = catalog.collections.find(item => item.id === 'billiards').assets;
  const ids = assets.map(asset => asset.id);
  const expected = ['pool-table', 'cue-stick-01', 'cue-stick-02', 'rack', 'chalk', 'cue-ball',
    ...Array.from({ length: 15 }, (_, i) => `ball-${String(i + 1).padStart(2, '0')}`),
    'eight-ball-billiards'];
  assert.deepEqual(ids, expected);
  assert.equal(new Set(assets.map(asset => asset.file)).size, expected.length);
  for (const asset of assets) {
    assert.ok(asset.bytes > 0 && asset.triangles > 0, asset.id);
    assert.ok(fs.statSync(asset.thumbnail).size > 0, asset.id);
  }
});

test('individual GLBs have only their own root and a zero origin', () => {
  const { assets } = loadCatalog().collections.find(item => item.id === 'billiards');
  for (const asset of assets.filter(item => item.root)) {
    const data = glbJson(asset.file);
    const rootNodes = data.scenes[data.scene ?? 0].nodes.map(index => data.nodes[index]);
    assert.deepEqual(rootNodes.map(node => node.name), [asset.root], asset.id);
    assert.deepEqual(rootNodes[0].translation ?? [0, 0, 0], [0, 0, 0], asset.id);
    assert.ok(!data.nodes.some(node => node.name?.startsWith('STUDIO')), asset.id);
  }
  const table = glbJson(assets.find(asset => asset.id === 'pool-table').file);
  assert.ok(!table.nodes.some(node => /ball|cue|rack|chalk/i.test(node.name ?? '')));
  const ball = glbJson(assets.find(asset => asset.id === 'ball-08').file);
  assert.ok(ball.nodes.some(node => node.name === 'Ball 08 | numeral 8'));
  const cue = glbJson(assets.find(asset => asset.id === 'cue-stick-01').file);
  assert.ok(cue.nodes.some(node => node.name === 'Cue 1 | shaft'));
});

test('assembled scene retains all 21 roots at their assembled locations', () => {
  const { assets } = loadCatalog().collections.find(item => item.id === 'billiards');
  const scene = glbJson(assets.find(item => item.id === 'eight-ball-billiards').file);
  const roots = scene.scenes[scene.scene ?? 0].nodes.map(index => scene.nodes[index]);
  assert.deepEqual(new Set(roots.map(root => root.name)), new Set(assets.filter(item => item.root).map(item => item.root)));
  assert.notDeepEqual(roots.find(root => root.name === 'ASSET_Ball_08').translation ?? [0, 0, 0], [0, 0, 0]);
});

test('number marks follow the ball surface on opposite sides', () => {
  const { assets } = loadCatalog().collections.find(item => item.id === 'billiards');
  const radius = 0.028575;
  for (let number = 1; number <= 15; number++) {
    const asset = assets.find(item => item.id === `ball-${String(number).padStart(2, '0')}`);
    const bytes = fs.readFileSync(asset.file);
    const jsonLength = bytes.readUInt32LE(12);
    const data = JSON.parse(bytes.subarray(20, 20 + jsonLength).toString('utf8'));
    const binaryStart = 20 + jsonLength + 8;
    const numberNodes = data.nodes.filter(node => /number medallion|\| numeral/.test(node.name ?? ''));
    assert.equal(numberNodes.length, 4, `${asset.id} needs two medallions and two numerals`);
    for (const node of numberNodes) {
      const primitive = data.meshes[node.mesh].primitives[0];
      const accessor = data.accessors[primitive.attributes.POSITION];
      const view = data.bufferViews[accessor.bufferView];
      assert.equal(accessor.componentType, 5126);
      assert.equal(accessor.type, 'VEC3');
      assert.ok(accessor.min[0] > 0.025 || accessor.max[0] < -0.025, `${node.name} must sit on a side of the ball`);
      assert.ok(accessor.max[0] - accessor.min[0] > 0.0001, `${node.name} must curve with the sphere`);
      const start = binaryStart + (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
      const stride = view.byteStride ?? 12;
      for (let i = 0; i < accessor.count; i++) {
        const offset = start + i * stride;
        const distance = Math.hypot(bytes.readFloatLE(offset), bytes.readFloatLE(offset + 4), bytes.readFloatLE(offset + 8));
        assert.ok(distance >= radius && distance <= radius + 0.00012, `${node.name} vertex must stay close to ball surface`);
      }
    }
    const sphere = data.nodes.find(node => node.name === `Ball ${String(number).padStart(2, '0')} | resin`);
    const position = data.meshes[sphere.mesh].primitives[0].attributes.POSITION;
    assert.ok(data.accessors[position].count > 1000, `${asset.id} should have smooth sphere geometry`);
  }
});
