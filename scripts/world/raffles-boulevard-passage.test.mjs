import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { gunzipSync } from 'node:zlib';

import { buildRoadGraph, offsetPolyline } from '../../src/world/network/graph.js';
import { buildTileFiles } from './build-tiles.mjs';
import { scanCorridorCrossings } from './fort-canning-crossings.mjs';
import { polylineLength } from './tile-geometry.mjs';

const source = JSON.parse(gunzipSync(readFileSync(new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url))));
const tile = JSON.parse(readFileSync(new URL('../../models/world/tiles/-1_-4.json', import.meta.url)));
const ways = new Map(source.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
const graph = buildRoadGraph(source);
const roads = new Map(graph.edges.map(edge => [edge.id, edge]));
const walkers = new Map(graph.pedestrian.edges.map(edge => [edge.id, edge]));
const passageIds = ['479745478:0', '479745478:1'];
const chainIds = ['649944021:0', ...passageIds, '479745479:0'];
const street = passageIds.flatMap((id, index) => roads.get(id).points.slice(index ? 1 : 0));
const path = street.map(([x, z], index) => ({ x, z, s: polylineLength(street.slice(0, index + 1)) }));
const length = path.at(-1).s;
const width = roads.get(passageIds[0]).width;
const overlaps = scanCorridorCrossings({ path, width, length, tiles: [tile], ways, routeIds: new Set(passageIds),
  roof: { start: 0, end: 0 } });

function distanceToSegment([x, z], [ax, az], [bx, bz]) {
  const dx = bx - ax, dz = bz - az;
  const t = Math.max(0, Math.min(1, ((x - ax) * dx + (z - az) * dz) / (dx ** 2 + dz ** 2)));
  return Math.hypot(x - ax - t * dx, z - az - t * dz);
}

function minBetweenDisjointLines(a, b) {
  const endpointDistances = (points, line) => points.flatMap(point =>
    line.slice(1).map((end, index) => distanceToSegment(point, line[index], end)));
  return Math.min(...endpointDistances(a, b), ...endpointDistances(b, a));
}

function insideRing([x, z], ring) {
  return ring.slice(1).reduce((inside, [bx, bz], index) => {
    const [ax, az] = ring[index];
    return (az > z) !== (bz > z) && x < ax + (bx - ax) * (z - az) / (bz - az) ? !inside : inside;
  }, false);
}

test('the Raffles Boulevard way is a five-lane building passage between mapped surface approaches', () => {
  const nodes = [1720073406, 4727947772, 7023019223, 4281759839, 9946316970];
  for (const [index, id] of chainIds.entries()) {
    const edge = roads.get(id);
    assert.deepEqual([edge.from, edge.to], nodes.slice(index, index + 2));
    assert.equal(edge.oneway, true);
    assert.equal(edge.lanes, 5);
    assert.equal(edge.width, 17);
    assert.equal(edge.tunnel, passageIds.includes(id));
    assert.ok(tile.roads.find(road => road.id === id));
    if (index) assert.deepEqual(roads.get(chainIds[index - 1]).points.at(-1), edge.points[0]);
  }
  assert.ok(Math.abs(length - 22.9706464985) < 1e-6);
  const { tags } = ways.get(479745478);
  assert.equal(tags.tunnel, 'building_passage');
  assert.equal(tags.maxheight, '4.5');
  for (const key of ['layer', 'level', 'ele', 'incline']) assert.equal(tags[key], undefined);
});

test('the structure intersects both edges in plan and pins only mapped vertical tags', () => {
  const roof = overlaps.find(({ edgeId, kind }) => edgeId === '393090492' && kind === 'building');
  assert.deepEqual(roof.ranges, [[0, 22.970646]]);
  const { tags } = ways.get(393090492);
  assert.deepEqual([tags.layer, tags.level, tags.min_height, tags.height], ['1', '1', '4.5', '6']);
  const ring = tile.buildings.find(({ id }) => id === 393090492).geometry.map(([x, z]) => [x + 250 * tile.x, z + 250 * tile.z]);
  // The projected roof meets the lane envelope at opposing portal corners.
  const northEdge = offsetPolyline(street, width / 2), southEdge = offsetPolyline(street, -width / 2);
  assert.deepEqual(northEdge.map(point => insideRing(point, ring)), [true, true, false]);
  assert.deepEqual(southEdge.map(point => insideRing(point, ring)), [false, true, true]);
});

test('both footway ribbon overlaps follow one covered path on the north side', () => {
  const { tags } = ways.get(749001558);
  assert.deepEqual(tags, { covered: 'yes', highway: 'footway', lit: 'yes' });
  const cases = [
    ['749001558:4', 7004337795, 7004337798, [20.767294, 21.874791]],
    ['749001558:7', 7004337798, 6743567254, [0, 20.469652]],
  ];
  for (const [id, from, to, range] of cases) {
    const edge = walkers.get(id);
    assert.deepEqual([edge.wayId, edge.from, edge.to], [749001558, from, to]);
    assert.ok(edge.points.every(([, z]) => z < Math.min(...street.map(([, roadZ]) => roadZ))));
    const separation = minBetweenDisjointLines(street, edge.points);
    assert.ok(Math.abs(separation - 9.0898791044) < 1e-6);
    assert.ok(separation > width / 2);
    const overlap = overlaps.find(feature => feature.edgeId === id);
    assert.equal(overlap.at, null);
    assert.deepEqual(overlap.ranges, [range]);
  }
  assert.ok(ways.get(736307191).nodes.includes(6743567254));
  const stairBranch = ways.get(749001563);
  assert.equal(stairBranch.nodes[0], 7004337798);
  assert.equal(ways.get(751214885).nodes[0], stairBranch.nodes.at(-1));
  for (const id of [736307191, 751214885]) {
    const steps = ways.get(id);
    assert.equal(steps.tags.level, '0;1');
    assert.equal(steps.tags.incline, undefined);
  }
});

test('the source preserves the service-mouth topology and lane tags without supplying turn permissions', () => {
  const mouth = ways.get(429052425);
  assert.deepEqual(mouth.nodes, [7023019223, 7023019224]);
  assert.deepEqual([mouth.tags.highway, mouth.tags.level, mouth.tags.tunnel], ['service', '-1;0', 'building_passage']);
  for (const key of ['oneway', 'access', 'motorcar', 'motor_vehicle', 'vehicle', 'turn:lanes']) assert.equal(mouth.tags[key], undefined);
  assert.ok(roads.get('429052425:0').points[1][1] > roads.get('429052425:0').points[0][1]);
  assert.equal(ways.get(1431080706).nodes[0], mouth.nodes[1]);
  assert.equal(ways.get(1431080706).tags.access, 'destination');
  assert.equal(ways.get(1431080706).tags.oneway, 'yes');
  assert.equal(ways.get(649944021).tags['turn:lanes'], 'none|through|through|through|through');
  for (const id of [649944021, 479745478, 479745479]) {
    const { tags } = ways.get(id);
    assert.deepEqual([tags['busway:left'], tags['lanes:bus'], tags['lanes:bus:conditional']],
      ['lane', '1', '1 @ (Mo-Sa 07:30-23:00)']);
  }
  assert.equal(source.elements.some(({ type }) => type === 'relation'), false);
});

test('the pinned source reproduces all three annotated tile files and withholds the passage when the soffit is unknown', () => {
  const { files } = buildTileFiles(source);
  for (const name of ['-1_-4.json', '-1_-5.json', '-2_-5.json']) {
    assert.equal(files.get(name), readFileSync(new URL('../../models/world/tiles/' + name, import.meta.url), 'utf8'));
  }
  const elements = source.elements.map(element => element.type === 'way' && element.id === 393090492
    ? { ...element, tags: { ...element.tags, min_height: undefined } } : element);
  const rejected = JSON.parse(buildTileFiles(elements).files.get('-1_-4.json'));
  assert.equal(rejected.roadSurfaces, undefined);
  assert.ok(rejected.roads.filter(road => road.wayId === 479745478).every(road => road.tunnel && !road.passageRoof));
  assert.equal(rejected.buildings.find(building => building.id === 393090492).minHeight, undefined);
});
