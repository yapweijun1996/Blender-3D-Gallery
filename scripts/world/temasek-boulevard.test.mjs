import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';

import { splitByRing } from '../../src/world/network/polygon.js';
import { buildTileFiles } from './build-tiles.mjs';
import { scanCorridorCrossings } from './fort-canning-crossings.mjs';
import { polylineLength, ringArea } from './tile-geometry.mjs';

const source = JSON.parse(gunzipSync(readFileSync(new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
const ways = new Map(source.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
const { files } = buildTileFiles(source);
const tileName = '-1_-6.json';
const tile = JSON.parse(files.get(tileName));
const chains = [
  ['21702431:4', '395443687:0', '750875319:0'],
  ['21701084:0', '395443688:0', '750875316:0'],
];
const roofId = 393210509;

function checkedIn(file) {
  return readFileSync(new URL(`../../models/world/tiles/${file}`, import.meta.url), 'utf8');
}

test('the pinned compiler reproduces Suntec, Millenia Walk and Marina Square tile bytes', () => {
  for (const file of [tileName, '-1_-4.json', '-2_-4.json']) assert.equal(files.get(file), checkedIn(file));
  assert.deepEqual(tile.roadSurfaces.map(surface => surface.edges), chains);
  assert.deepEqual(tile.roads.filter(road => road.passageRoof === roofId).map(road => road.id), chains.map(chain => chain[1]));
  const building = tile.buildings.find(candidate => candidate.id === roofId);
  assert.deepEqual([building.minHeight, building.height, building.passages], [5, 20, undefined]);
  const tags = ways.get(roofId).tags;
  assert.deepEqual([tags.min_height, tags.height], ['5', '20']);
  const [north, south] = tile.roadSurfaces.map(surface => surface.geometry);
  for (const [ring, other] of [[north, south], [south, north]]) {
    assert.ok(Math.abs(ringArea(ring)) > 500);
    for (const [i, end] of ring.slice(1).entries()) {
      assert.ok(splitByRing(ring[i], end, other.slice(0, -1)).every(span => !span.inside), 'carriageways do not overlap');
    }
  }
});

test('both covered centerlines meet their road approaches and the modeled roof in plan', () => {
  for (const [index, chain] of chains.entries()) {
    const lanes = index === 0 ? 'left;through|through' : 'left|left';
    const route = chain.map(id => tile.roads.find(road => road.id === id));
    assert.ok(route.every(road => road.width === 6.8 && road.lanes === 2 && road.oneway));
    assert.deepEqual(route[0].geometry.at(-1), route[1].geometry[0]);
    assert.deepEqual(route[1].geometry.at(-1), route[2].geometry[0]);
    assert.deepEqual(route[1].forwardConnector, { id: route[2].id, lanes: [0, 1] });
    assert.equal(route[1].turnLanes, lanes);
    const tags = ways.get(route[1].wayId).tags;
    assert.equal(tags['turn:lanes'], lanes);
    assert.equal(tags.tunnel, 'building_passage');
    assert.equal(tags.level, undefined);
    assert.equal(tags.ele, undefined);

    const points = route[1].geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]);
    const path = points.map(([x, z], i) => ({ x, z, s: polylineLength(points.slice(0, i + 1)) }));
    const length = path.at(-1).s;
    assert.ok(length > 39.7 && length < 39.9);
    const overlaps = scanCorridorCrossings({ path, tiles: [tile], ways, width: 6.8, length,
      routeIds: new Set(chain), roof: { start: 0, end: 0 } });
    const roof = overlaps.find(feature => feature.edgeId === String(roofId) && feature.kind === 'building');
    assert.deepEqual(roof.ranges, [[0, Number(length.toFixed(6))]]);
  }

  assert.equal(tile.roads.find(road => road.id === '21701084:0').toll, 'yes');
  assert.equal(tile.roads.find(road => road.id === '750875319:0').turnLanes, 'left|left');
  const driveway = tile.roads.find(road => road.id === '753843011:0');
  assert.equal(driveway.from, 3983027173);
  assert.equal(driveway.class, 'service');
  assert.equal(driveway.forwardConnector, undefined);
});

test('invalid road access or missing walkway evidence leaves both passages closed', () => {
  const changedAccess = source.elements.map(element => element.type === 'way' && element.id === 395443687
    ? { ...element, tags: { ...element.tags, motorcar: 'private' } }
    : element);
  const missingWalkway = source.elements.filter(element => element.type !== 'way' || element.id !== 1321783356);
  for (const elements of [changedAccess, missingWalkway]) {
    const fallback = JSON.parse(buildTileFiles(elements).files.get(tileName));
    assert.equal(fallback.roadSurfaces, undefined);
    assert.equal(fallback.buildings.find(candidate => candidate.id === roofId).minHeight, undefined);
    assert.ok(fallback.roads.every(road => !road.passageRoof && !road.forwardConnector));
    assert.ok(fallback.kerbs.every(kerb => !kerb.surfaceGeometry));
    assert.deepEqual(fallback.kerbs, tile.kerbs.map(({ surfaceGeometry, ...original }) => original));
  }
  assert.deepEqual(tile.kerbs.filter(kerb => kerb.surfaceGeometry).map(kerb => [kerb.road, kerb.side]), [
    ['750875317:0', 'left'], ['753843011:0', 'left'], ['753843011:0', 'right'],
    ['1447712291:0', 'left'], ['1447712291:0', 'right'],
  ]);
});
