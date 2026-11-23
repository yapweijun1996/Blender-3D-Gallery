import { samePoint } from '../../src/world/network/geometry.js';
import { splitByRing } from '../../src/world/network/polygon.js';
import { allowsAmbientTraffic } from '../../src/world/traffic.js';
import { clipSurfaceKerb, passageRibbon } from './passage-geometry.mjs';
import { applyRafflesLinkWalkway } from './raffles-link-walkway.mjs';

const TILE = '-3_-4';
const BUILDING = 620812487;
const CHAIN = ['684524081:0', '532351088:0', '159938518:0'];
const NODES = [6413515288, 5165958044, 1720065558, 6413515285];
const UPSTREAM = '710062599:1';
const OUTBOUND = '684524082:0';
const SERVICE_LOOP = '684523974:0';
const TURNS = 'left;through';
const FLOOR = 0;
// The map identifies the two mouths but provides no heights or road width.
const SOFFIT = 4.5;
const SHOULDER = .3;
const ROAD_GEOMETRY_TAGS = new Set(['layer', 'level', 'ele', 'incline', 'width', 'maxheight', 'maxwidth']);
const ACCESS_CONDITIONS = ['access:conditional', 'vehicle:conditional', 'motor_vehicle:conditional', 'motorcar:conditional'];
const BUILDING_HEIGHT_TAGS = ['height', 'min_height', 'building:levels', 'building:min_level', 'building:height'];

function sameSurface(road, lanes) {
  return road?.name === 'Raffles Link' && road.lanes === lanes && road.width === lanes * 3.4 &&
    !road.bridge && !road.tunnel && road.layer === 0 && allowsAmbientTraffic(road);
}

function reviewedChain(tile, ways) {
  const edges = CHAIN.map(id => tile.roads.find(road => road.id === id));
  if (!edges.every((edge, i) => {
    if (!edge?.oneway || edge.name !== 'Raffles Link' || edge.class !== 'residential' || edge.width !== 3.4 ||
        edge.lanes !== 1 || edge.bridge || !allowsAmbientTraffic(edge) || edge.geometry.length < 2 ||
        edge.from !== NODES[i] || edge.to !== NODES[i + 1] || edge.tunnel !== (i === 1) ||
        edge.layer !== (i === 1 ? -1 : 0) ||
        (i > 0 && !samePoint(edges[i - 1].geometry.at(-1), edge.geometry[0]))) return false;
    const tags = ways.get(edge.wayId)?.tags;
    return tags?.['turn:lanes'] === TURNS && tags.sidewalk === 'right' && tags.surface === 'asphalt' &&
      (i === 1 ? tags.tunnel === 'building_passage' : tags.tunnel == null) &&
      Object.keys(tags).every(tag => !ROAD_GEOMETRY_TAGS.has(tag.split(':')[0])) &&
      !ACCESS_CONDITIONS.some(tag => tags[tag] != null);
  })) return null;

  const incoming = tile.roads.find(road => road.id === UPSTREAM);
  const outgoing = tile.roads.find(road => road.id === OUTBOUND);
  if (!sameSurface(incoming, 2) || incoming.oneway || incoming.to !== NODES[0] ||
      !samePoint(incoming.geometry.at(-1), edges[0].geometry[0]) ||
      !sameSurface(outgoing, 1) || !outgoing.oneway || outgoing.from !== NODES.at(-1) ||
      !samePoint(outgoing.geometry[0], edges.at(-1).geometry.at(-1))) return null;

  return edges;
}

function clipServiceKerb(tile, ways, surface) {
  const loop = tile.roads.find(road => road.id === SERVICE_LOOP);
  const tags = ways.get(loop?.wayId)?.tags;
  if (!loop?.oneway || !loop.tunnel || loop.layer !== -1 || loop.from !== NODES.at(-1) || loop.to !== NODES[0] ||
      tags?.highway !== 'service' || tags.service !== 'driveway' || tags.tunnel !== 'building_passage') return;
  for (const kerb of tile.kerbs) {
    if (kerb.road === SERVICE_LOOP && kerb.layer === loop.layer) clipSurfaceKerb(kerb, surface.slice(0, -1));
  }
}

function hasOpenMouths(opening, points, building) {
  const ring = building.geometry.slice(0, -1);
  const crossesInterior = line => line.slice(1).some((point, i) =>
    splitByRing(line[i], point, ring).some(span => span.inside));
  const left = opening.slice(0, points);
  const right = opening.slice(points, -1);
  return crossesInterior(left) && crossesInterior(right) &&
    !crossesInterior([right.at(-1), left[0]]) && !crossesInterior([left.at(-1), right[0]]);
}

/** Fit one simulated road opening at the two mapped facade nodes. */
export function applyRafflesLinkPassage(tiles, elements) {
  const tile = tiles.get(TILE);
  if (!tile) return;

  const ways = new Map(elements.filter(({ type }) => type === 'way').map(way => [way.id, way]));
  const roof = ways.get(BUILDING);
  const building = tile.buildings.find(({ id }) => id === BUILDING);
  if (roof?.tags?.building !== 'yes' || BUILDING_HEIGHT_TAGS.some(tag => roof.tags[tag] != null) ||
      !roof.nodes?.includes(NODES[1]) || !roof.nodes?.includes(NODES[2]) ||
      building?.height !== 9.6 || building.minHeight != null ||
      [...tiles.values()].some(fragment => fragment !== tile && fragment.buildings.some(({ id }) => id === BUILDING))) return;

  const staged = structuredClone(tile);
  const edges = reviewedChain(staged, ways);
  if (!edges) return;

  const centerline = edges.flatMap((edge, i) => edge.geometry.slice(i ? 1 : 0));
  const halfWidth = edges[1].width / 2;
  const surface = passageRibbon(centerline, halfWidth);
  const opening = passageRibbon(centerline, halfWidth + SHOULDER);
  if (!hasOpenMouths(opening, centerline.length, building)) return;
  (staged.roadSurfaces ??= []).push({ edges: CHAIN, geometry: surface });
  staged.buildings.find(({ id }) => id === BUILDING).passages = [{ floor: FLOOR, soffit: SOFFIT, geometry: opening }];
  edges[1].passageRoof = BUILDING;
  edges[2].retainShortTraffic = true;
  edges[2].forwardConnector = { id: OUTBOUND, lanes: [0] };
  for (const edge of edges) edge.turnLanes = TURNS;
  clipServiceKerb(staged, ways, surface);
  if (!applyRafflesLinkWalkway(staged, ways)) return;
  Object.assign(tile, staged);
}
