import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { resolve, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';
import { applyRafflesPassage } from './raffles-boulevard.mjs';
import { applyMarinaSquarePassage } from './marina-square-passage.mjs';
import { applyTemasekPassages } from './temasek-boulevard.mjs';
import { buildRoadGraph, junctionArmDepth, offsetPolyline, simplifyPolyline } from '../../src/world/network/graph.js';
import { distinctPoints, samePoint } from '../../src/world/network/geometry.js';
import { ORIGIN, projectOsm } from '../../src/world/network/project.js';
import { alongPolyline, clipLine, clipRing, polylineLength, ringArea } from './tile-geometry.mjs';

export const TILE_SIZE = 250;
export const MAX_TILE_BYTES = 120_000;
const DEFAULT_INPUT = fileURLToPath(new URL('../../output/osm/marina_bay.json', import.meta.url));
const DEFAULT_OUTPUT = fileURLToPath(new URL('../../models/world/tiles/', import.meta.url));
const LAYERS = ['roads', 'junctions', 'kerbs', 'pedestrian', 'buildings', 'water', 'parks', 'trees',
  'streetLamps', 'crossings', 'busStops', 'subwayEntrances'];

const DEFAULT_BUILDING_HEIGHTS = {
  apartments: 16, residential: 12, house: 6.4, detached: 6.4, terrace: 6.4,
  commercial: 16, office: 20, hotel: 20, retail: 9.6, industrial: 8, warehouse: 8,
  school: 9.6, hospital: 16, parking: 9.6, roof: 3.2, shed: 3.2, garage: 3.2, garages: 3.2,
};

export function buildingHeight(tags) {
  const height = /^(\d+(?:\.\d+)?)\s*(m|ft|feet)?$/i.exec(tags.height?.trim() ?? '');
  if (height && Number(height[1]) > 0) {
    return Number(height[1]) * (['ft', 'feet'].includes(height[2]?.toLowerCase()) ? 0.3048 : 1);
  }
  const levels = /^\d+(?:\.\d+)?$/.test(tags['building:levels']?.trim() ?? '') ? Number(tags['building:levels']) : 0;
  if (levels > 0) return levels * 3.2;
  return Object.hasOwn(DEFAULT_BUILDING_HEIGHTS, tags.building) ? DEFAULT_BUILDING_HEIGHTS[tags.building] : 9.6;
}

function footprint(way) {
  const geometry = way.geometry ?? [];
  if (geometry.length < 4 || !geometry.every(point => Number.isFinite(point?.lon) && Number.isFinite(point?.lat))) return [];
  const points = distinctPoints(geometry.map(projectOsm));
  if (points.length < 4 || !samePoint(points[0], points.at(-1))) return [];
  const simplified = simplifyPolyline(points);
  return simplified.length >= 4 && Math.abs(ringArea(simplified)) > 1e-6 ? simplified : points;
}

function surfaceLayers(tags) {
  const layers = [];
  if (tags.building && tags.building !== 'no') layers.push('buildings');
  if (tags.natural === 'water' || tags.water || tags.waterway === 'riverbank' || tags.landuse === 'reservoir') layers.push('water');
  if (['park', 'garden', 'nature_reserve'].includes(tags.leisure) || tags.natural === 'park') layers.push('parks');
  return layers;
}

function tileGeometry() {
  const tiles = new Map();

  function add(x, z, layer, feature) {
    const key = `${x}_${z}`;
    if (!tiles.has(key)) {
      tiles.set(key, { x, z, ...Object.fromEntries(LAYERS.map(name => [name, []])) });
    }
    tiles.get(key)[layer].push(feature);
  }

  function tilePoint([x, z], origin) {
    return [x, z].map((value, axis) => Math.max(0, Math.min(TILE_SIZE, round(value - origin[axis]))));
  }

  function addPoint(layer, feature, point) {
    const [x, z] = point.map(value => Math.floor(value / TILE_SIZE));
    add(x, z, layer, { ...feature, point: tilePoint(point, [x * TILE_SIZE, z * TILE_SIZE]) });
  }

  function addShape(layer, feature, points, polygon, makeFeature = (base, geometry) => ({ ...base, geometry })) {
    if (points.length < (polygon ? 4 : 2)) return;
    const min = [Infinity, Infinity];
    const max = [-Infinity, -Infinity];
    for (const point of points) {
      for (let axis = 0; axis < 2; axis++) {
        min[axis] = Math.min(min[axis], Math.floor(point[axis] / TILE_SIZE));
        max[axis] = Math.max(max[axis], Math.floor(point[axis] / TILE_SIZE));
      }
    }
    for (let x = min[0]; x <= max[0]; x++) {
      for (let z = min[1]; z <= max[1]; z++) {
        const origin = [x * TILE_SIZE, z * TILE_SIZE];
        const bounds = { min: origin, max: origin.map(value => value + TILE_SIZE) };
        const pieces = polygon ? [clipRing(points, bounds)] : clipLine(points, bounds);
        for (const piece of pieces) {
          const geometry = distinctPoints(piece.map(point => tilePoint(point, origin)));
          if (polygon ? geometry.length < 4 || !ringArea(geometry) : geometry.length < 2) continue;
          add(x, z, layer, makeFeature(feature, geometry, origin, piece));
        }
      }
    }
  }

  return { tiles, addPoint, addShape, tilePoint };
}

const round = value => Math.round(value * 100) / 100;

function kerbCenterline(points, width, trimStart, trimEnd) {
  function trim(point, neighbour) {
    const length = Math.hypot(neighbour[0] - point[0], neighbour[1] - point[1]);
    const fraction = junctionArmDepth(width, length) / length;
    return point.map((value, axis) => value + fraction * (neighbour[axis] - value));
  }
  const trimmed = points.slice();
  if (trimStart) trimmed[0] = trim(points[0], points[1]);
  if (trimEnd) trimmed[trimmed.length - 1] = trim(points.at(-1), points.at(-2));
  return trimmed;
}

export function buildTileFiles(input) {
  const elements = (Array.isArray(input) ? input : input.elements).slice().sort((a, b) => a.id - b.id);
  const graph = buildRoadGraph(elements);
  const { tiles, addPoint, addShape, tilePoint } = tileGeometry();

  const patchedNodes = new Set(graph.junctions.filter(junction => junction.polygon.length).map(junction => junction.nodeId));
  for (const { points, laneCenterlines, width, ...edge } of graph.edges) {
    if (edge.bridge && edge.layer > 0) {
      // A bridge is raised at run time (src/world/bridges.js): each fragment records where it starts along the whole edge.
      const edgeLength = polylineLength(points);
      addShape('roads', { ...edge, width: round(width), edgeLength: round(edgeLength) }, points, false,
        (base, geometry, origin, piece) => ({ ...base, geometry, edgeStart: round(alongPolyline(points, piece[0])) }));
    } else addShape('roads', { ...edge, width: round(width) }, points, false);
    const kerbLine = kerbCenterline(points, width, patchedNodes.has(edge.from), patchedNodes.has(edge.to));
    for (const [side, factor] of [['left', 1], ['right', -1]]) {
      addShape('kerbs', { road: edge.id, side, layer: edge.layer }, offsetPolyline(kerbLine, factor * width / 2), false);
    }
  }

  for (const { point, polygon, ...junction } of graph.junctions) {
    // Marker ownership follows the junction point, while the patch can span tile boundaries.
    const owner = point.map(value => Math.floor(value / TILE_SIZE) * TILE_SIZE);
    let placedMarker = false;
    addShape('junctions', junction, polygon, true, (base, geometry, origin) => {
      if (!samePoint(owner, origin)) return { ...base, geometry };
      placedMarker = true;
      return { ...base, geometry, point: tilePoint(point, origin) };
    });
    if (!placedMarker) addPoint('junctions', junction, point);
  }

  for (const { points, ...edge } of graph.pedestrian.edges) {
    addShape(edge.class === 'crossing' ? 'crossings' : 'pedestrian', edge, points, false);
  }

  for (const { point, ...crossing } of graph.pedestrian.crossings) addPoint('crossings', crossing, point);

  for (const element of elements) {
    const tags = element.tags ?? {};
    const feature = { id: element.id, ...(tags.name ? { name: tags.name } : {}) };
    if (element.type === 'way') {
      const layers = surfaceLayers(tags);
      if (!layers.length) continue;
      const ring = footprint(element);
      for (const layer of layers) {
        const attributes = layer === 'buildings'
          ? { ...feature, class: tags.building, height: round(buildingHeight(tags)) }
          : feature;
        addShape(layer, attributes, ring, true);
      }
    } else if (element.type === 'node' && Number.isFinite(element.lat) && Number.isFinite(element.lon)) {
      const point = projectOsm(element);
      if (tags.natural === 'tree') addPoint('trees', feature, point);
      if (tags.highway === 'street_lamp' || tags.man_made === 'street_lamp') addPoint('streetLamps', feature, point);
      if (tags.highway === 'bus_stop') addPoint('busStops', feature, point);
      if (tags.railway === 'subway_entrance') addPoint('subwayEntrances', feature, point);
    }
  }

  applyRafflesPassage(tiles, elements);
  applyMarinaSquarePassage(tiles, elements);
  applyTemasekPassages(tiles, elements);
  const files = new Map();
  const entries = [];
  for (const tile of [...tiles.values()].sort((a, b) => a.x - b.x || a.z - b.z)) {
    const file = `${tile.x}_${tile.z}.json`;
    const json = JSON.stringify(tile);
    const bytes = Buffer.byteLength(json);
    if (bytes >= MAX_TILE_BYTES) throw new Error(`Tile ${file} is ${bytes} bytes (limit: <${MAX_TILE_BYTES})`);
    entries.push({ x: tile.x, z: tile.z, file, bytes });
    files.set(file, json);
  }

  const index = {
    version: 1,
    origin: ORIGIN,
    tileSize: TILE_SIZE,
    units: 'metres',
    axes: ['east', 'south'],
    attribution: '© OpenStreetMap contributors (ODbL)',
    tiles: entries,
  };
  files.set('index.json', JSON.stringify(index));
  return { files, index };
}

async function replaceFile(directory, name, contents) {
  const temporary = join(directory, `.${name}.${randomUUID()}.tmp`);
  try {
    await writeFile(temporary, contents, { flag: 'wx' });
    await rename(temporary, join(directory, name));
  } finally {
    await rm(temporary, { force: true });
  }
}

export async function writeTiles({ input = DEFAULT_INPUT, output = DEFAULT_OUTPUT } = {}) {
  const { files, index } = buildTileFiles(JSON.parse(await readFile(input, 'utf8')));
  await mkdir(output, { recursive: true });
  // buildTileFiles validates every byte count before the writer touches any destination.
  for (const [name, json] of files) await replaceFile(output, name, json);
  return index;
}

if (process.argv[1] && import.meta.url === pathToFileURL(resolve(process.argv[1])).href) {
  const { values } = parseArgs({ options: { input: { type: 'string' }, output: { type: 'string' } } });
  const index = await writeTiles(values);
  const maxBytes = Math.max(0, ...index.tiles.map(tile => tile.bytes));
  console.log(`${index.tiles.length} tiles, largest ${maxBytes} bytes`);
}
