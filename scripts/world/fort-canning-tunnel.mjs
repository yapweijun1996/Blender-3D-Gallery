import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { gunzipSync } from 'node:zlib';
import { buildRoadGraph, LANE_WIDTH } from '../../src/world/network/graph.js';
import { TILE_SIZE } from './build-tiles.mjs';
import { polylineLength } from './tile-geometry.mjs';

const FORT_CANNING_WAY = 159677768;
const FIXTURE = new URL('./fixtures/marina-bay-2026-11-20.json.gz', import.meta.url);
const FIXTURE_SHA256 = '297a9877428e2cf9714cf414f414f07586d383d1bd17dfec7fd2749a9bfaa998';
const GAME_DEPTH = 5.5;
const MAX_GRADE = 0.08;
const SAMPLE_METRES = 1;
const EPSILON = 1e-9;
const round = value => Math.round(value * 1e6) / 1e6 || 0;

function tileCuts(from, to) {
  const cuts = [];
  for (let axis = 0; axis < 2; axis++) {
    const min = Math.min(from[axis], to[axis]);
    const max = Math.max(from[axis], to[axis]);
    for (let boundary = (Math.floor(min / TILE_SIZE) + 1) * TILE_SIZE; boundary < max; boundary += TILE_SIZE) {
      cuts.push((boundary - from[axis]) / (to[axis] - from[axis]));
    }
  }
  return cuts;
}

// Keep every OSM bend, tile seam and grade transition in the sampled path.
function samplePath(points, station, elevation = () => 0, extraStations = []) {
  const [x, z] = points[0];
  const samples = [{ x: round(x), y: round(elevation(station)), z: round(z), s: round(station) }];
  for (let i = 1; i < points.length; i++) {
    const from = points[i - 1], to = points[i];
    const [dx, dz] = [to[0] - from[0], to[1] - from[1]];
    const length = Math.hypot(dx, dz);
    const count = Math.ceil(length / SAMPLE_METRES);
    const fractions = [...tileCuts(from, to), ...Array.from({ length: count }, (_, n) => (n + 1) / count)];
    for (const marker of extraStations) {
      if (marker > station && marker < station + length) fractions.push((marker - station) / length);
    }
    fractions.sort((a, b) => a - b);
    let previous = 0;
    for (const t of fractions) {
      if (t - previous <= EPSILON) continue;
      const s = station + length * t;
      samples.push({ x: round(from[0] + dx * t), y: round(elevation(s)), z: round(from[1] + dz * t), s: round(s) });
      previous = t;
    }
    station += length;
  }
  return samples;
}

function tileFragments(points) {
  const fragments = [];
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i];
    const x = Math.floor((a.x + b.x) / 2 / TILE_SIZE);
    const z = Math.floor((a.z + b.z) / 2 / TILE_SIZE);
    const previous = fragments.at(-1);
    if (previous?.tile[0] === x && previous.tile[1] === z) previous.points.push(b);
    else fragments.push({ tile: [x, z], points: [a, b] });
  }
  return fragments;
}

function surfaceConnection(graph, tunnel, entry) {
  const node = entry ? tunnel.from : tunnel.to;
  const matches = graph.edges.filter(edge =>
    (entry ? edge.to : edge.from) === node && edge.name === tunnel.name && edge.layer === 0 &&
    !edge.bridge && !edge.tunnel && edge.oneway && edge.width === tunnel.width);
  if (matches.length !== 1) throw new Error(`Expected one aligned surface connection at node ${node}`);
  return matches[0];
}

export function buildFortCanningTunnel(osm, fixtureSha256) {
  const way = osm.elements.find(element => element.type === 'way' && element.id === FORT_CANNING_WAY);
  // The network's broad tunnel boolean includes building passages and covered roads.
  if (way?.tags?.tunnel !== 'yes' || way.tags.layer !== '-1' || way.tags.covered === 'yes') {
    throw new Error(`Way ${FORT_CANNING_WAY} is not the pinned underground road`);
  }
  const graph = buildRoadGraph(osm.elements);
  const edges = graph.edges.filter(edge => edge.wayId === FORT_CANNING_WAY);
  const [edge] = edges;
  if (edges.length !== 1 || edge.class !== 'primary' || edge.lanes !== 3 || !edge.oneway ||
      edge.from !== way.nodes[0] || edge.to !== way.nodes.at(-1)) {
    throw new Error(`Way ${FORT_CANNING_WAY} does not match the pinned road topology`);
  }
  const entry = surfaceConnection(graph, edge, true);
  const exit = surfaceConnection(graph, edge, false);
  const length = polylineLength(edge.points);
  const rampLength = 1.5 * GAME_DEPTH / MAX_GRADE;
  if (length <= 2 * rampLength) throw new Error('Pinned road is too short for the prototype ramps');

  function elevation(station) {
    const t = Math.max(0, Math.min(1, station / rampLength, (length - station) / rampLength));
    return -GAME_DEPTH * t * t * (3 - 2 * t);
  }

  const points = samplePath(edge.points, 0, elevation, [rampLength, length - rampLength]);
  const approaches = {
    entry: samplePath(entry.points, -polylineLength(entry.points)),
    exit: samplePath(exit.points, length),
  };
  return {
    source: {
      osmWayId: way.id,
      edgeId: edge.id,
      tunnelTag: way.tags.tunnel,
      osmLayer: edge.layer,
      locationNote: way.tags.note,
      timestamp: osm.osm3s.timestamp_osm_base,
      attribution: '© OpenStreetMap contributors (ODbL)',
      fixtureSha256,
    },
    name: edge.name,
    width: edge.width,
    lanes: edge.lanes,
    laneWidth: LANE_WIDTH,
    oneway: edge.oneway,
    tileSize: TILE_SIZE,
    length: round(length),
    depth: GAME_DEPTH, // Prototype game depth. The OSM layer only describes vertical ordering.
    maxGrade: MAX_GRADE,
    rampLength: round(rampLength),
    portals: [
      { nodeId: edge.from, surfaceWayId: entry.wayId, point: points[0] },
      { nodeId: edge.to, surfaceWayId: exit.wayId, point: points.at(-1) },
    ],
    approaches,
    fragments: tileFragments(points),
  };
}

export async function readPinnedFortCanningTunnel() {
  const bytes = gunzipSync(await readFile(FIXTURE));
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  if (sha256 !== FIXTURE_SHA256) throw new Error('The pinned Marina Bay fixture SHA-256 changed');
  return buildFortCanningTunnel(JSON.parse(bytes), sha256);
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const route = await readPinnedFortCanningTunnel();
  console.log(JSON.stringify(route));
}
