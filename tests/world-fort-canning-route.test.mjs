import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buildTrafficGraph } from '../src/world/traffic.js';
import { FORT_CANNING_TILES, prepareFortCanningRoute } from '../src/world/tunnel-integration/route.js';

const base = new Map(FORT_CANNING_TILES.map(key => [key,
  JSON.parse(readFileSync(new URL('../models/world/tiles/' + key + '.json', import.meta.url)))]));
const signal = new AbortController().signal;

test('prepares the six actual tiles together without replacing unrelated features', async () => {
  const requested = [];
  const route = await prepareFortCanningRoute(async (key, loadingSignal) => {
    assert.equal(loadingSignal, signal);
    requested.push(key);
    return base.get(key);
  }, signal);
  assert.deepEqual(requested, FORT_CANNING_TILES);
  assert.equal(route.tiles.size, FORT_CANNING_TILES.length);
  assert.deepEqual(route.tiles.get('-8_-7').parks, base.get('-8_-7').parks);
  assert.ok([...route.tiles.values()].every(tile => tile.roads.every(road => road.wayId !== 774912613)));
  assert.ok(route.geometry.surfaces.some(surface => surface.id === 'road'));

  const graph = buildTrafficGraph(route.tiles.values(), route.trafficOptions);
  assert.ok(graph.nodes.get(235180430).laneDisjointMerge);
  assert.equal(graph.edges.get('888048851:0').forwardSignal.approach, graph.edges.get('888048851:2').forwardSignal.approach);
  assert.deepEqual(graph.nodes.get(408999681).forward, ['75551640:0']);
});

test('a missing, mismatched or aborted tile bundle cannot produce a route', async () => {
  await assert.rejects(prepareFortCanningRoute(async key => key === '-8_-8' ? null : base.get(key), signal),
    /Missing Fort Canning tile -8_-8/);
  await assert.rejects(prepareFortCanningRoute(async key => key === '-7_-7' ? { ...base.get(key), roads: [] } : base.get(key), signal),
    /does not match the pinned geometry: -7_-7/);
  const controller = new AbortController();
  await assert.rejects(prepareFortCanningRoute(async key => {
    controller.abort();
    return base.get(key);
  }, controller.signal), { name: 'AbortError' });
});
