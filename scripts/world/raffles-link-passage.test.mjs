import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';
import { offsetPolyline } from '../../src/world/network/geometry.js';
import { splitByRing } from '../../src/world/network/polygon.js';
import { buildTileFiles } from './build-tiles.mjs';
import { polylineLength } from './tile-geometry.mjs';

const source = JSON.parse(gunzipSync(readFileSync(new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
const ways = new Map(source.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
const file = '-3_-4.json';
const roof = 620812487;
const covered = 532351088;
const branch = '684523974:0';
const chain = ['684524081:0', `${covered}:0`, '159938518:0'];
const { files } = buildTileFiles(source);
const tile = JSON.parse(files.get(file));
const road = id => tile.roads.find(road => road.id === id);
const building = tile.buildings.find(building => building.id === roof);

function overlapLength(line, ring) {
  return line.slice(1).reduce((total, point, i) => {
    const segmentLength = polylineLength([line[i], point]);
    return total + splitByRing(line[i], point, ring.slice(0, -1))
      .reduce((length, span) => length + (span.inside ? (span.end - span.start) * segmentLength : 0), 0);
  }, 0);
}

test('the raw road uses both building ring nodes and has no measured clearance or grade', () => {
  const sourceRoad = ways.get(covered);
  const sourceBuilding = ways.get(roof);
  assert.deepEqual(sourceRoad.nodes, [5165958044, 1720065558]);
  assert.ok(sourceRoad.nodes.every(id => sourceBuilding.nodes.includes(id)));
  const tags = sourceRoad.tags;
  assert.deepEqual([tags.highway, tags.name, tags.tunnel, tags.oneway, tags.lanes, tags.surface, tags.sidewalk, tags['turn:lanes']],
    ['residential', 'Raffles Link', 'building_passage', 'yes', '1', 'asphalt', 'right', 'left;through']);
  for (const key of ['maxheight', 'maxheight:physical', 'layer', 'level', 'width', 'incline', 'ele', 'access', 'motorcar', 'motor_vehicle', 'vehicle']) {
    assert.equal(tags[key], undefined, key);
  }
  assert.deepEqual(sourceBuilding.tags, { building: 'yes' });
  assert.deepEqual(ways.get(684523974).tags, {
    highway: 'service', lit: 'yes', oneway: 'yes', service: 'driveway', tunnel: 'building_passage',
  });
  assert.equal(ways.get(1431080692).tags.access, 'destination');
  assert.equal(ways.get(1431080692).tags.layer, '-1');
});

test('the pinned source emits only the one-lane passage with both open mouths and the exact downstream stitch', () => {
  assert.equal(files.get(file), readFileSync(new URL(`../../models/world/tiles/${file}`, import.meta.url), 'utf8'));
  assert.deepEqual(tile.roadSurfaces.map(({ edges }) => edges), [chain]);
  assert.deepEqual(tile.roads.filter(edge => edge.passageRoof === roof).map(edge => edge.id), [chain[1]]);
  assert.deepEqual(tile.roads.filter(edge => edge.retainShortTraffic).map(edge => edge.id), [chain[2]]);
  assert.deepEqual(road(chain[2]).forwardConnector, { id: '684524082:0', lanes: [0] });
  assert.ok(chain.every(id => road(id).turnLanes === 'left;through' && road(id).oneway && road(id).lanes === 1 && road(id).width === 3.4));
  const [coveredEdge, exit] = [road(chain[1]), road(chain[2])];
  assert.deepEqual([coveredEdge.layer, coveredEdge.tunnel, coveredEdge.access], [-1, true, null]);
  assert.ok(Math.abs(polylineLength(coveredEdge.geometry) - 6.458) < .002);
  assert.ok(Math.abs(polylineLength(exit.geometry) - 2.407) < .002);
  const incoming = road('710062599:1');
  assert.deepEqual([incoming.lanes, incoming.width, incoming.oneway], [2, 6.8, false]);
  assert.equal(tile.roadSurfaces[0].edges.includes(incoming.id), false);
  assert.deepEqual([road(branch).tunnel, road(branch).passageRoof, road('1431080692:0').access],
    [true, undefined, 'destination']);

  assert.deepEqual([building.height, building.minHeight, building.passages.length], [9.6, undefined, 1]);
  const [{ floor, soffit, geometry }] = building.passages;
  assert.deepEqual([floor, soffit], [0, 4.5]);
  assert.deepEqual(geometry[0], geometry.at(-1));
  assert.ok(Math.abs(polylineLength(geometry.slice(3, 5)) - 4) < .002);
  assert.ok(Math.abs(overlapLength(coveredEdge.geometry, building.geometry) - 6.309) < .002);
  for (const cap of [geometry.slice(3, 5), geometry.slice(7, 9)]) assert.equal(overlapLength(cap, building.geometry), 0);
  for (const candidate of tile.buildings.filter(building => building.id !== roof)) {
    assert.equal(overlapLength(geometry, candidate.geometry), 0, String(candidate.id));
  }
  for (const [other, json] of files) if (other !== file) {
    assert.ok(!json.includes(`"passageRoof":${roof}`));
  }
});

test('the grade-separated indoor bridge crosses the asphalt, while the outdoor footway and marked crossings clear it', () => {
  const deck = ways.get(460302684);
  assert.deepEqual([deck.tags.bridge, deck.tags.indoor, deck.tags.level, deck.tags.layer], ['yes', 'yes', '1', '1']);
  assert.ok(ways.get(460302683).nodes.includes(deck.nodes[0]));
  assert.ok(ways.get(460300683).nodes.includes(deck.nodes.at(-1)));
  assert.deepEqual(deck.nodes.filter(node => ways.get(covered).nodes.includes(node)), []);
  const path = id => tile.pedestrian.find(path => path.id === id).geometry;
  const asphalt = tile.roadSurfaces[0].geometry;
  assert.ok(Math.abs(overlapLength(path('460302684:0'), asphalt) - 3.451) < .002);
  const outer = ways.get(843814340);
  assert.deepEqual(outer.nodes.filter(node => ways.get(684523974).nodes.includes(node)), [7871401191, 7871401190]);
  for (const offset of [-1.1, 0, 1.1]) {
    assert.equal(overlapLength(offsetPolyline(path('843814340:0'), offset), building.passages[0].geometry), 0);
  }
  for (const crossing of tile.crossings) {
    const line = crossing.geometry ?? [crossing.point, [crossing.point[0] + .001, crossing.point[1]]];
    assert.equal(overlapLength(line, building.passages[0].geometry), 0);
  }
});

test('only the crossing portion of the left service-loop kerb is clipped', () => {
  const changed = tile.kerbs.filter(kerb => kerb.surfaceGeometry);
  assert.deepEqual(changed.map(({ road, side, layer }) => [road, side, layer]), [[branch, 'left', -1]]);
  const [{ geometry, surfaceGeometry: [retained] }] = changed;
  assert.deepEqual(retained.slice(0, -1), geometry.slice(0, -1));
  assert.ok(Math.abs(retained.at(-1)[0] - 235.422) < .001);
  assert.ok(Math.abs(retained.at(-1)[1] - 49.014) < .001);
  const ring = tile.roadSurfaces[0].geometry;
  const removed = overlapLength(geometry, ring);
  assert.ok(Math.abs(removed - .394) < .002);
  assert.ok(Math.abs(polylineLength(geometry) - polylineLength(retained) - removed) < .001);
  assert.ok(overlapLength(retained, ring) < .00001);
});

test('changes to access, dimensions, walkway level or roof evidence keep the original tile closed', () => {
  for (const [wayId, tags] of [
    [covered, { motorcar: 'private', access: 'yes' }],
    [covered, { 'maxheight:physical': '3.2' }],
    [710062599, { vehicle: 'permit' }],
    [460302684, { level: '2' }],
    [roof, { height: '12' }],
  ]) {
    const elements = source.elements.map(element => element.type === 'way' && element.id === wayId
      ? { ...element, tags: { ...element.tags, ...tags } }
      : element);
    const rejected = JSON.parse(buildTileFiles(elements).files.get(file));
    assert.equal(rejected.roadSurfaces, undefined, String(wayId));
    assert.equal(rejected.buildings.find(building => building.id === roof).passages, undefined);
    assert.ok(rejected.roads.every(edge => edge.passageRoof === undefined && edge.retainShortTraffic === undefined));
    assert.ok(rejected.kerbs.every(kerb => kerb.surfaceGeometry === undefined));
  }
});
