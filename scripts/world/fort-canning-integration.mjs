import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { buildRoadGraph, LANE_WIDTH } from '../../src/world/network/graph.js';
import { projectOsm } from '../../src/world/network/project.js';
import { TILE_SIZE } from './build-tiles.mjs';
import { corridorBounds, scanCorridorCrossings } from './fort-canning-crossings.mjs';
import { polylineLength } from './tile-geometry.mjs';

const SNAPSHOT = new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url);
const FIXTURE_SHA256 = '297a9877428e2cf9714cf414f414f07586d383d1bd17dfec7fd2749a9bfaa998';
const EXIT_FIXTURE = './fixtures/fort-canning-penang-exit-2026-11-23.json';
const EXIT_FIXTURE_SHA256 = '6d4859dd0dd9b8451eca35c688a9f72d3d838b1064490d2a60c59d4fdc3b6636';
const PENANG_CHAIN = [888048852, 74559749, 888048851];
const TILE_DIRECTORY = new URL('../../models/world/tiles/', import.meta.url);
const LINK_CHAIN = ['21815891:0', '21815891:1', '719635729:0', '719635728:0', '159677768:0', '39351292:0'];
const MAIN_TUNNEL = '159677768:0';
const START = -96;
const DEPTH = 5.5, GRADE = 0.08, CLEARANCE = 4.7, ROOF_THICKNESS = 0.2;
const RAMP = 1.5 * DEPTH / GRADE;
const REQUIRED_DEPTH = CLEARANCE + ROOF_THICKNESS;
const round = value => Math.round(value * 1e6) / 1e6 || 0;
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const mix = (a, b, f) => a + (b - a) * f;

function readChain(graph, ways, rampStart) {
  const edges = new Map(graph.edges.map(edge => [edge.id, edge]));
  const routeEdges = LINK_CHAIN.map(id => edges.get(id));
  const [first] = routeEdges;
  if (routeEdges.some((edge, index) => edge?.name !== 'Fort Canning Link' || edge.width !== 3 * LANE_WIDTH ||
      edge.lanes !== 3 || !edge.oneway || edge.bridge || index > 0 && edge.from !== routeEdges[index - 1].to)) {
    throw new Error('Fort Canning Link no longer forms the expected chain');
  }
  const main = edges.get(MAIN_TUNNEL);
  if (ways.get(main.wayId)?.tags.tunnel !== 'yes' || main.layer !== -1) {
    throw new Error('The pinned 361 m Fort Canning tunnel source has changed');
  }
  let station = 0;
  const path = [{ x: first.points[0][0], z: first.points[0][1], s: 0 }];
  const spans = routeEdges.map(edge => {
    const start = station;
    for (let index = 1; index < edge.points.length; index++) {
      const [x, z] = edge.points[index], [px, pz] = edge.points[index - 1];
      station += Math.hypot(x - px, z - pz);
      path.push({ x, z, s: station });
    }
    const tags = ways.get(edge.wayId).tags;
    return { edgeId: edge.id, from: edge.from, to: edge.to, start, end: station,
      osmLayer: edge.layer, tunnelTag: tags.tunnel ?? null, maxHeight: tags.maxheight ?? null };
  });
  const original = spans.find(({ edgeId }) => edgeId === MAIN_TUNNEL);
  const offset = original.start + rampStart;
  const sections = path.map(point => ({ ...point, s: point.s - offset }));
  const pivot = sections.findIndex(({ s }) => s > 0);
  const surface = spans.find(({ start, end }) => offset >= start && offset < end);
  if (pivot <= 0 || !(offset < original.start) || surface?.osmLayer !== 0 || surface.tunnelTag) {
    throw new Error('Earlier ramp must start on the pinned surface approach');
  }
  const a = sections[pivot - 1], b = sections[pivot];
  sections.splice(pivot, 0, { x: mix(a.x, b.x, -a.s / (b.s - a.s)), z: mix(a.z, b.z, -a.s / (b.s - a.s)), s: 0 });
  return { width: first.width, sectionStart: pivot, sections, main, offset, original, spans, station };
}

function floorAt(s, length) {
  const t = Math.max(0, Math.min(1, s / RAMP, (length - s) / RAMP));
  return -DEPTH * t * t * (3 - 2 * t);
}

function roofStart(length) {
  let low = 0, high = RAMP;
  for (let step = 0; step < 44; step++) {
    const test = (low + high) / 2;
    if (floorAt(test, length) > -REQUIRED_DEPTH) low = test;
    else high = test;
  }
  return high;
}

function tileStations(a, b) {
  const stations = [];
  for (const axis of ['x', 'z']) {
    const min = Math.min(a[axis], b[axis]), max = Math.max(a[axis], b[axis]);
    for (let edge = (Math.floor(min / TILE_SIZE) + 1) * TILE_SIZE; edge < max; edge += TILE_SIZE) {
      stations.push(mix(a.s, b.s, (edge - a[axis]) / (b[axis] - a[axis])));
    }
  }
  return stations;
}

function sampledPath(path, length, knots) {
  const output = [];
  const first = path[0];
  output.push({ x: round(first.x), y: round(floorAt(first.s, length)), z: round(first.z), s: round(first.s) });
  for (let index = 1; index < path.length; index++) {
    const a = path[index - 1], b = path[index];
    const count = Math.ceil(b.s - a.s);
    const stations = [...tileStations(a, b), ...knots.filter(s => s > a.s && s < b.s),
      ...Array.from({ length: count }, (_, step) => mix(a.s, b.s, (step + 1) / count))].sort((a, b) => a - b);
    for (const s of stations) {
      if (round(s) === output.at(-1).s) continue;
      const f = (s - a.s) / (b.s - a.s);
      output.push({ x: round(mix(a.x, b.x, f)), y: round(floorAt(s, length)), z: round(mix(a.z, b.z, f)), s: round(s) });
    }
  }
  return output;
}

function fragmentsOf(points) {
  const fragments = [];
  for (let index = 1; index < points.length; index++) {
    const a = points[index - 1], b = points[index];
    const tile = ['x', 'z'].map(axis => Math.floor((a[axis] + b[axis]) / (2 * TILE_SIZE)));
    const latest = fragments.at(-1);
    if (latest && latest.tile[0] === tile[0] && latest.tile[1] === tile[1]) latest.points.push(b);
    else fragments.push({ tile, points: [a, b] });
  }
  return fragments;
}

async function loadTiles(sections, width) {
  const [minX, maxX, minZ, maxZ] = corridorBounds(sections, width).map(value => Math.floor(value / TILE_SIZE));
  const tiles = [], sourceTiles = [];
  for (let x = minX; x <= maxX; x++) {
    for (let z = minZ; z <= maxZ; z++) {
      const key = `${x}_${z}`;
      const bytes = await readFile(new URL(`${key}.json`, TILE_DIRECTORY));
      tiles.push(JSON.parse(bytes));
      sourceTiles.push({ key, sha256: sha(bytes) });
    }
  }
  return { tiles, sourceTiles };
}

async function readExitWitness(exitNodeId, exitSection) {
  const bytes = await readFile(new URL(EXIT_FIXTURE, import.meta.url));
  if (sha(bytes) !== EXIT_FIXTURE_SHA256) throw new Error('The pinned Penang Road exit witness SHA-256 changed');
  const { retrievedOnUtc, attribution, requests, elements } = JSON.parse(bytes);
  if (requests.length !== PENANG_CHAIN.length) throw new Error('The Penang Road witness must contain all three onward ways');
  const nodes = new Map(elements.filter(({ type }) => type === 'node').map(node => [node.id, node]));
  const ways = new Map(elements.filter(({ type }) => type === 'way').map(way => [way.id, way]));
  const anchor = nodes.get(exitNodeId);
  if (!anchor) throw new Error('The official exit witness is missing the pinned Link endpoint node');
  const [initialX, initialZ] = projectOsm(anchor);
  if (initialX !== exitSection.x || initialZ !== exitSection.z) throw new Error('Official exit node does not align with the pinned Link endpoint');
  let lastNode = exitNodeId, totalLength = 0;
  const edges = requests.map((source, index) => {
    const { wayId, url, responseSha256, elementsSha256 } = source;
    const way = ways.get(wayId);
    if (wayId !== PENANG_CHAIN[index] || url !== `https://api.openstreetmap.org/api/0.6/way/${wayId}/full.json` ||
        !/^[0-9a-f]{64}$/.test(responseSha256) || way?.nodes[0] !== lastNode) {
      throw new Error('The Penang Road witness is not a directed chain from the Link exit');
    }
    const ordered = way.nodes.map(id => nodes.get(id));
    const { tags } = way;
    const access = tags.motorcar ?? tags.motor_vehicle ?? tags.vehicle ?? tags.access;
    if (ordered.some(node => !Number.isFinite(node?.lat) || !Number.isFinite(node?.lon)) ||
        sha(JSON.stringify([...ordered, way])) !== elementsSha256 || tags.name !== 'Penang Road' || tags.highway !== 'primary' ||
        tags.oneway !== 'yes' || access && !['yes', 'designated', 'permissive'].includes(access)) {
      throw new Error(`Penang Road way ${wayId} no longer matches the attributed ordinary carriageway`);
    }
    const points = ordered.map(projectOsm);
    const length = polylineLength(points);
    const from = lastNode;
    lastNode = way.nodes.at(-1);
    totalLength += length;
    return { ...source, from, to: lastNode, name: tags.name, class: tags.highway, lanes: Number(tags.lanes),
      oneway: true, length: round(length), version: way.version, timestamp: way.timestamp,
      points: points.map(point => point.map(round)) };
  });
  return { sourceFixture: `scripts/world/${EXIT_FIXTURE.slice(2)}`, fixtureSha256: EXIT_FIXTURE_SHA256, retrievedOnUtc, attribution,
    from: exitNodeId, to: lastNode, length: round(totalLength), terminalSignal: nodes.get(lastNode)?.tags?.highway === 'traffic_signals', edges };
}

export async function readFortCanningIntegration({ start = START } = {}) {
  const bytes = gunzipSync(await readFile(SNAPSHOT));
  if (sha(bytes) !== FIXTURE_SHA256) throw new Error('The pinned Marina Bay fixture SHA-256 changed');
  const osm = JSON.parse(bytes);
  const graph = buildRoadGraph(osm);
  const ways = new Map(osm.elements.filter(element => element.type === 'way').map(way => [way.id, way]));
  const { width, sectionStart, sections, main, offset, original, spans, station } = readChain(graph, ways, start);
  const length = station - offset;
  const roofIn = roofStart(length);
  const roof = { start: roofIn, end: length - roofIn };
  const { tiles, sourceTiles } = await loadTiles(sections, width);
  const crossings = scanCorridorCrossings({ path: sections, tiles, ways, width, length, roof, routeIds: new Set(LINK_CHAIN) });
  const path = sampledPath(sections, length, [roof.start, RAMP, length - RAMP, roof.end]);
  const firstRampSample = path.findIndex(point => point.s === sections[sectionStart].s);
  const fortCanning = crossings.find(({ edgeId }) => edgeId === '646730739:0');
  const penang = crossings.find(({ edgeId }) => edgeId === '654224115:0');
  if (!fortCanning?.at || !penang) throw new Error('Required downstream geometry missing from the tracked tiles');
  const exitNodeId = spans.at(-1).to;
  const matchingExit = graph.edges.filter(edge => edge.from === exitNodeId);
  const tileExit = tiles.flatMap(tile => tile.roads).filter(edge => edge.from === exitNodeId);
  const onwardEdges = [...new Set([...matchingExit, ...tileExit].map(edge => edge.id))].sort();
  const exitWitness = await readExitWitness(exitNodeId, sections.at(-1));
  const mainTags = ways.get(main.wayId).tags;
  const bridge = crossings.find(({ edgeId }) => edgeId === '719635727');
  const minimumBridgeUnderside = bridge?.openCut.length
    ? round(Math.max(...bridge.openCut.flat().map(station => floorAt(station, length))) + CLEARANCE) : null;
  const blockers = crossings.filter(({ openCut }) => openCut.length > 0)
    .map(({ kind, edgeId }) => ({ kind, edgeId }));
  const linearDepth = Math.max(0, penang.start - fortCanning.end) * GRADE;
  return {
    source: { osmWayId: main.wayId, edgeId: main.id, tunnelTag: mainTags.tunnel, osmLayer: main.layer,
      locationNote: mainTags.note, timestamp: osm.osm3s.timestamp_osm_base,
      attribution: '© OpenStreetMap contributors (ODbL)', fixtureSha256: FIXTURE_SHA256, tiles: sourceTiles },
    name: main.name, width, lanes: main.lanes, laneWidth: LANE_WIDTH, oneway: main.oneway, tileSize: TILE_SIZE,
    length: round(length), depth: DEPTH, maxGrade: GRADE, rampLength: RAMP,
    simulation: {
      originalTunnelLength: round(original.end - original.start), originalStartStation: start,
      originalEndStation: round(station - original.start), clearance: CLEARANCE, roofThickness: ROOF_THICKNESS,
      roof: { start: round(roof.start), end: round(roof.end) },
      chain: spans.map(edge => ({ ...edge, start: round(edge.start - offset), end: round(edge.end - offset) })),
      exitNodeId, onwardEdges, exitWitness,
      overheadBridge: { edgeId: '719635727', minimumSimulatedUnderside: minimumBridgeUnderside },
      flatExitConstraint: { overhead: fortCanning.edgeId, merge: penang.edgeId, run: round(penang.start - fortCanning.end),
        maximumLinearDepth: round(linearDepth), requiredDepth: round(REQUIRED_DEPTH), shortfall: round(REQUIRED_DEPTH - linearDepth) },
      gate: { ready: blockers.length === 0 && linearDepth >= REQUIRED_DEPTH && onwardEdges.length > 0, blockers },
    },
    approaches: { entry: path.slice(0, firstRampSample + 1), exit: [path.at(-1)] },
    fragments: fragmentsOf(path.slice(firstRampSample)),
    crossings,
  };
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  console.log(JSON.stringify(await readFortCanningIntegration()));
}
