import { between, splitByRing } from '../../src/world/network/polygon.js';
import { offsetPolyline, samePoint } from '../../src/world/network/geometry.js';

const TILE = '-2_-4';
const BUILDING = 303311927;
const SOFFIT = 4.5;
const UPPER_FLOOR_THICKNESS = .30;
const SHOULDER = .30;
const CHAIN = ['723073393:0', '545362402:0', '545362402:1', '545362402:2', '545362403:0', '635373148:0'];
const NODES = [6782303341, 5270981856, 12169571327, 12169568595, 1832823705, 5270981855, 6769049627];
const TUNNEL_WAYS = new Set([545362402, 545362403]);
const SHORT_EDGES = new Set(['723073393:0', '545362402:1', '545362403:0']);
const UPPER_WAY = 474174793;
const GARAGES = [[1314801325, 12169571327, 12169571328], [1314801304, 12169568594, 12169568595]];
const GARAGE_KERBS = ['1314801297:1', '1314801304:0', '1314801318:0', '1314801325:0', '1314816309:0', '1314816311:0'];
const BRANCH_KERBS = new Map([['172373834:0', NODES[0]], ['736307183:0', NODES.at(-1)], ['1424403063:0', NODES.at(-1)]]);
const PUBLIC_ACCESS = new Set([null, undefined, 'yes', 'designated', 'permissive']);

function ribbonRing(points, halfWidth) {
  const left = offsetPolyline(points, halfWidth), right = offsetPolyline(points, -halfWidth);
  return [...left, ...right.reverse(), left[0]].map(point => point.map(value => Math.round(value * 1000) / 1000));
}

function subsurfaceKerbs(tile, ways) {
  return GARAGE_KERBS.filter(id => {
    const road = tile.roads.find(edge => edge.id === id);
    const tags = ways.get(road?.wayId)?.tags;
    if (tags?.highway !== 'service' || !['driveway', 'parking_aisle'].includes(tags.service) || tags.tunnel !== 'yes') return false;
    return road.tunnel && road.layer < 0 && road.layer === Number(tags.layer) && road.access === 'destination' &&
      tile.kerbs.some(kerb => kerb.road === id && kerb.layer === road.layer);
  });
}

function outsidePolylines(points, ring) {
  const pieces = [];
  let current = null;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i];
    const at = t => t === 0 ? a : t === 1 ? b : between(a, b, t);
    for (const { start, end, inside } of splitByRing(a, b, ring)) {
      if (inside) {
        current = null;
      } else if (current) {
        current.push(at(end));
      } else {
        current = [at(start), at(end)];
        pieces.push(current);
      }
    }
  }
  return pieces;
}

function clipBranchKerbs(tile, passage, halfWidth) {
  const west = tile.roads.find(road => road.id === '173791997:0');
  const east = tile.roads.find(road => road.id === '635373148:1');
  if (west?.to !== NODES[0] || east?.from !== NODES.at(-1) || west.width !== halfWidth * 2 || east.width !== halfWidth * 2 ||
      west.tunnel || east.tunnel || west.layer !== 0 || east.layer !== 0 ||
      !samePoint(west.geometry.at(-1), passage[0]) || !samePoint(east.geometry[0], passage.at(-1))) return;

  // Both surface junctions extend beyond the passage's first and last centerline rows.
  const ring = ribbonRing([...west.geometry.slice(0, -1), ...passage, ...east.geometry.slice(1)], halfWidth).slice(0, -1);
  for (const kerb of tile.kerbs) {
    const node = BRANCH_KERBS.get(kerb.road);
    if (!node || kerb.layer !== 0) continue;
    const road = tile.roads.find(edge => edge.id === kerb.road);
    if (!road || road.tunnel || road.layer !== 0 || (road.from !== node && road.to !== node)) continue;
    const pieces = outsidePolylines(kerb.geometry, ring);
    if (pieces.length !== 1 || pieces[0].length !== kerb.geometry.length ||
        pieces[0].some((point, index) => !samePoint(point, kerb.geometry[index]))) kerb.surfaceGeometry = pieces;
  }
}

/** Compile the modeled through passage from the reviewed map topology and tagged height limit. */
export function applyMarinaSquarePassage(tiles, elements) {
  const tile = tiles.get(TILE);
  if (!tile) return;
  const ways = new Map(elements.filter(({ type }) => type === 'way').map(way => [way.id, way]));
  const mall = ways.get(BUILDING)?.tags;
  const building = tile.buildings.find(({ id }) => id === BUILDING);
  const upper = ways.get(UPPER_WAY)?.tags;
  const paths = tile.pedestrian.filter(({ wayId }) => wayId === UPPER_WAY);
  if (mall?.building !== 'retail' || mall.name !== 'Marina Square' || mall.height !== '0' || mall.min_height != null ||
      !building || upper?.highway !== 'corridor' || upper.indoor !== 'yes' || upper.level !== '1' || paths.length !== 2) return;

  for (const id of TUNNEL_WAYS) {
    const tags = ways.get(id)?.tags;
    if (tags?.tunnel !== 'building_passage' || tags.maxheight !== '4.5' || tags.layer != null || tags.level != null ||
        tags.ele != null || tags.incline != null) return;
  }
  for (const [id, from, to] of GARAGES) {
    const road = tile.roads.find(edge => edge.id === `${id}:0`);
    if (road?.from !== from || road.to !== to || !road.oneway || !road.tunnel || road.access !== 'destination') return;
  }
  const chain = CHAIN.map(id => tile.roads.find(road => road.id === id));
  if (!chain.every((edge, i) => edge?.oneway && PUBLIC_ACCESS.has(edge.access) && edge.width === 17 && edge.lanes === 5 && edge.geometry.length >= 2 &&
      edge.from === NODES[i] && edge.to === NODES[i + 1] && edge.tunnel === TUNNEL_WAYS.has(edge.wayId) &&
      (!i || chain[i - 1].geometry.at(-1).every((value, axis) => value === edge.geometry[0][axis])))) return;

  const points = chain.flatMap((edge, i) => edge.geometry.slice(i ? 1 : 0));
  const halfWidth = chain[0].width / 2;
  tile.roadSurfaces = [...(tile.roadSurfaces ?? []), {
    edges: CHAIN, geometry: ribbonRing(points, halfWidth), subsurfaceKerbs: subsurfaceKerbs(tile, ways),
  }];
  clipBranchKerbs(tile, points, halfWidth);
  building.passages = [{ floor: 0, soffit: SOFFIT, geometry: ribbonRing(points, halfWidth + SHOULDER) }];
  for (const edge of chain) {
    if (TUNNEL_WAYS.has(edge.wayId)) edge.passageRoof = BUILDING;
    if (SHORT_EDGES.has(edge.id)) edge.retainShortTraffic = true;
    const tags = ways.get(edge.wayId)?.tags;
    if (tags?.['busway:left'] === 'lane' && tags['lanes:bus'] === '1') edge.leftBusLane = true;
  }
  for (const path of paths) {
    path.indoorLevel = Number(upper.level);
    path.floorHeight = SOFFIT + UPPER_FLOOR_THICKNESS;
  }
}
