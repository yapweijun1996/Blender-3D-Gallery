import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtemp, readdir, readFile, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { project as driveProject } from '../../src/drive/route.js';
import { buildRoadGraph, buildLaneCenterlines, simplifyPolyline } from '../../src/world/network/graph.js';
import { ORIGIN, project, projectOsm } from '../../src/world/network/project.js';
import { buildingHeight, buildTileFiles } from './build-tiles.mjs';

const osm = JSON.parse(await readFile(new URL('../../output/osm/marina_bay.json', import.meta.url), 'utf8'));
const graph = buildRoadGraph(osm);
const cli = fileURLToPath(new URL('./build-tiles.mjs', import.meta.url));
const wayEdge = id => graph.edges.find(edge => edge.wayId === id);

function reachable(start, { reverse = false, undirected = false } = {}) {
  const adjacent = new Map(graph.nodes.map(node => [node.id, []]));
  for (const { from, to, oneway } of graph.edges) {
    const [a, b] = reverse ? [to, from] : [from, to];
    adjacent.get(a).push(b);
    if (undirected || !oneway) adjacent.get(b).push(a);
  }
  const visited = new Set([start]);
  const queue = [start];
  for (const node of queue) {
    for (const next of adjacent.get(node)) {
      if (visited.has(next)) continue;
      visited.add(next);
      queue.push(next);
    }
  }
  return visited;
}

test('projection matches the drive origin, scale and axes', () => {
  assert.deepEqual(project([ORIGIN.lon, ORIGIN.lat]).map(value => value || 0), [0, 0]);
  const east = projectOsm({ lon: ORIGIN.lon + 0.001, lat: ORIGIN.lat });
  const north = projectOsm({ lon: ORIGIN.lon, lat: ORIGIN.lat + 0.001 });
  assert(east[0] > 111 && east[0] < 112);
  assert(north[1] < -110 && north[1] > -111);
  const mbs = [103.862331, 1.283659];
  assert.deepEqual(project(mbs), driveProject(mbs));
});

test('Bayfront Avenue, Raffles Avenue and Nicoll Highway are in the main component', () => {
  const start = wayEdge(83145747).from;
  const component = reachable(start, { undirected: true });
  assert(component.size > graph.nodes.length / 2);
  for (const name of ['Bayfront Avenue', 'Raffles Avenue', 'Nicoll Highway']) {
    const roads = graph.edges.filter(edge => edge.name === name);
    assert(roads.length >= 20, name);
    assert(roads.every(({ from, to }) => component.has(from) && component.has(to)), name);
  }
  const outbound = reachable(start);
  const inbound = reachable(start, { reverse: true });
  for (const wayId of [173791995, 16688065]) {
    const { from, to } = wayEdge(wayId);
    assert(outbound.has(from) && outbound.has(to), `reach OSM way ${wayId}`);
    assert(inbound.has(from) && inbound.has(to), `return from OSM way ${wayId}`);
  }
});

test('known road attributes, defaults and reverse one-way direction match the extract', () => {
  for (const [id, name, roadClass, lanes, speed] of [
    [83145747, 'Bayfront Avenue', 'secondary', 3, 50],
    [173791995, 'Raffles Avenue', 'primary', 4, 50],
    [479565613, 'Raffles Avenue', 'primary', 6, 50],
    [16688065, 'Nicoll Highway', 'trunk', 4, 70],
    [23037305, 'Bayfront Avenue', 'secondary', 2, 50],
  ]) {
    const edge = wayEdge(id);
    assert.deepEqual([edge.name, edge.class, edge.lanes, edge.maxspeed, edge.oneway], [name, roadClass, lanes, speed, true]);
    assert.equal(edge.laneCenterlines.length, lanes);
    assert(edge.laneCenterlines.every(lane => lane.direction === 'forward'));
  }

  const reversed = wayEdge(1458010811);
  assert.equal(reversed.oneway, true);
  assert.equal(reversed.lanes, 1);
  assert.equal(reversed.from, 13371439083);
  assert.equal(reversed.to, 13371439086);
  assert.deepEqual(reversed.points[0], projectOsm(osm.elements.find(element => element.id === 1458010811).geometry.at(-1)));
  assert(graph.edges.some(edge => edge.bridge));
  assert(graph.edges.some(edge => edge.tunnel));
});

test('two-way traffic keeps left in x-east/z-south and lanes are 3.4 m apart', () => {
  const eastbound = [[0, 0], [30, 0]];
  const four = buildLaneCenterlines(eastbound, { lanes: 4, oneway: false });
  assert.deepEqual(four.map(({ direction }) => direction), ['forward', 'forward', 'backward', 'backward']);
  for (const [index, offset] of [-1.7, -5.1, 1.7, 5.1].entries()) {
    assert(Math.abs(four[index].points[0][1] - offset) < 1e-9);
  }
  assert.equal(four[2].points[0][0], 30);
  const northbound = buildLaneCenterlines([[0, 0], [0, -30]], { lanes: 2, oneway: false });
  assert.equal(northbound[0].points[0][0], -1.7);
  assert.equal(northbound[1].points[0][0], 1.7);
  const oneWay = buildLaneCenterlines(eastbound, { lanes: 3, oneway: true });
  assert.deepEqual(oneWay.map(lane => lane.points[0][1]), [-3.4, 0, 3.4]);
  assert.deepEqual(simplifyPolyline([[0, 0], [2, 0.4], [4, 0]]), [[0, 0], [4, 0]]);
  assert.deepEqual(simplifyPolyline([[0, 0], [2, 0.6], [4, 0]]), [[0, 0], [2, 0.6], [4, 0]]);
});

test('tagged crosswalks split road edges and signalised junctions have a patch', () => {
  const signal = graph.nodes.find(node => node.id === 233879603);
  const dual = graph.nodes.find(node => node.id === 3772852905);
  assert.equal(signal.signalised, true);
  assert.equal(dual.signalised, true);
  assert.equal(dual.crossing, true);
  assert(graph.pedestrian.crossings.some(node => node.id === dual.id && node.signalised));
  const patch = graph.junctions.find(junction => junction.nodeId === signal.id);
  assert.equal(patch.signalised, true);
  assert(patch.polygon.length >= 4);
  assert.deepEqual(patch.polygon[0], patch.polygon.at(-1));
  assert(graph.pedestrian.edges.some(edge => edge.class === 'steps'));
  assert(graph.pedestrian.edges.some(edge => edge.class === 'crossing'));
  assert(graph.edges.every(edge => !['footway', 'pedestrian', 'steps', 'crossing'].includes(edge.class)));

  const coords = id => ({ lon: ORIGIN.lon + ((id - 1) % 3) * 0.0001, lat: ORIGIN.lat + Math.floor((id - 1) / 3) * 0.0001 });
  const makeWay = (id, nodes, tags) => ({ id, type: 'way', nodes, geometry: nodes.map(coords), tags });
  const fixture = buildRoadGraph([
    makeWay(30, [1, 2, 3], { highway: 'primary' }),
    makeWay(31, [2, 5], { highway: 'residential' }),
    makeWay(32, [1, 4], { highway: 'footway', footway: 'crossing' }),
    makeWay(33, [4, 3], { highway: 'trunk', bridge: 'yes' }),
    { id: 1, type: 'node', ...coords(1), tags: { highway: 'crossing' } },
  ]);
  assert.deepEqual(fixture.edges.filter(edge => edge.wayId === 30).map(edge => [edge.from, edge.to]), [[1, 2], [2, 3]]);
  assert.equal(fixture.nodes.find(node => node.id === 2).edges.length, 3);
  assert.equal(fixture.nodes.find(node => node.id === 1).crossing, true);
  assert.equal(fixture.pedestrian.edges.length, 1);

  const gradeSeparated = buildRoadGraph([
    makeWay(40, [1, 5], { highway: 'residential' }),
    makeWay(41, [2, 4], { highway: 'primary', bridge: 'yes' }),
  ]);
  assert.equal(gradeSeparated.edges.length, 2);
  assert.equal(gradeSeparated.nodes.length, 4);
  assert.equal(gradeSeparated.junctions.length, 0);

  const crossingOnly = buildRoadGraph([
    makeWay(50, [1, 2, 3], { highway: 'motorway', oneway: 'no' }),
    { id: 2, type: 'node', ...coords(2), tags: { highway: 'crossing' } },
  ]);
  assert.deepEqual(crossingOnly.edges.map(edge => [edge.from, edge.to, edge.oneway]), [[1, 2, false], [2, 3, false]]);
  assert.equal(crossingOnly.junctions[0].crossing, true);
  assert.equal(crossingOnly.junctions[0].signalised, false);
});

test('height uses explicit metres, levels, then a building class default', () => {
  assert.equal(buildingHeight({ building: 'hotel', height: '44 m', 'building:levels': '5' }), 44);
  assert.equal(buildingHeight({ building: 'house', height: '20 ft' }), 6.096);
  assert.equal(buildingHeight({ building: 'yes', height: '0', 'building:levels': '3' }).toFixed(2), '9.60');
  assert.equal(buildingHeight({ building: 'house' }), 6.4);
});

test('CLI generates deterministic 250 m tiles under 120 KB and preserves mapped features', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'world-network-test-'));
  try {
    const first = join(directory, 'first');
    const second = join(directory, 'second');
    for (const output of [first, second]) execFileSync(process.execPath, [cli, '--output', output]);
    const listing = (await readdir(first)).sort();
    assert.deepEqual((await readdir(second)).sort(), listing);

    const index = JSON.parse(await readFile(join(first, 'index.json'), 'utf8'));
    assert.equal(index.tileSize, 250);
    assert.deepEqual(index.origin, ORIGIN);
    assert.deepEqual(listing, ['index.json', ...index.tiles.map(tile => tile.file)].sort());
    assert(index.tiles.length > 100);
    assert.deepEqual(await readFile(join(first, 'index.json')), await readFile(join(second, 'index.json')));
    const markers = Object.fromEntries(['roads', 'junctions', 'kerbs', 'pedestrian', 'buildings', 'water', 'parks',
      'trees', 'streetLamps', 'crossings', 'busStops', 'subwayEntrances'].map(layer => [layer, new Set()]));
    let countSignals = 0;
    let roadFragmentsAtSeam = 0;
    for (const entry of index.tiles) {
      const firstFile = join(first, entry.file);
      assert.equal((await stat(firstFile)).size, entry.bytes);
      assert(entry.bytes < 120_000, entry.file);
      const contents = await readFile(firstFile);
      assert.deepEqual(contents, await readFile(join(second, entry.file)), entry.file);
      const tile = JSON.parse(contents);
      assert.deepEqual([tile.x, tile.z], [entry.x, entry.z]);

      for (const [layer, ids] of Object.entries(markers)) {
        for (const feature of tile[layer]) {
          ids.add(feature.id ?? feature.nodeId ?? feature.road);
          for (const point of feature.geometry ?? [feature.point]) {
            assert(point.every(value => Number.isFinite(value) && value >= 0 && value <= 250), entry.file);
          }
        }
      }
      countSignals += tile.junctions.filter(junction => junction.point && junction.signalised).length;
      roadFragmentsAtSeam += tile.roads.filter(road =>
        road.geometry.some(point => point.some(value => value === 0 || value === 250))).length;
    }
    assert.equal(countSignals, 145);
    assert(roadFragmentsAtSeam > 0);
    assert.deepEqual(Object.fromEntries(['buildings', 'water', 'parks', 'trees', 'streetLamps', 'busStops', 'subwayEntrances']
      .map(layer => [layer, markers[layer].size])),
    { buildings: 1566, water: 37, parks: 45, trees: 551, streetLamps: 0, busStops: 96, subwayEntrances: 88 });
    for (const layer of ['roads', 'junctions', 'kerbs', 'pedestrian', 'crossings']) assert(markers[layer].size > 0);
  } finally {
    await rm(directory, { recursive: true, force: true });
  }
});

test('tile builder assigns lamps and clips road geometry across a signed tile seam', () => {
  const left = { lon: ORIGIN.lon - 0.001, lat: ORIGIN.lat - 0.001 };
  const right = { lon: ORIGIN.lon + 0.001, lat: ORIGIN.lat - 0.001 };
  const road = { type: 'way', id: 99, nodes: [1, 2], geometry: [left, right], tags: { highway: 'residential' } };
  const lamp = { type: 'node', id: 100, ...right, tags: { highway: 'street_lamp' } };
  const { files } = buildTileFiles([road, lamp]);
  const west = JSON.parse(files.get('-1_0.json'));
  const east = JSON.parse(files.get('0_0.json'));
  assert.equal(west.roads[0].geometry.at(-1)[0], 250);
  assert.equal(east.roads[0].geometry[0][0], 0);
  assert.equal(west.roads[0].geometry.at(-1)[1], east.roads[0].geometry[0][1]);
  assert.equal(west.streetLamps.length, 0);
  assert.equal(east.streetLamps[0].id, lamp.id);
  assert.deepEqual(buildTileFiles([lamp, road]).files, files);
});
