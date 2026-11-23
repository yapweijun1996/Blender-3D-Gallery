import { samePoint } from '../../src/world/network/geometry.js';
import { clipSurfaceKerb, passageRibbon } from './passage-geometry.mjs';
import { applyTemasekWalkways } from './temasek-walkways.mjs';

const TILE = '-1_-6';
const ROOF = 393210509;
const PUBLIC_ACCESS = new Set([null, undefined, 'yes', 'designated', 'permissive']);
const ROUTES = [
  { ids: ['21702431:4', '395443687:0', '750875319:0'], nodes: [6114355475, 3983027171, 3983027173, 13283123167],
    turnLanes: 'left;through|through' },
  { ids: ['21701084:0', '395443688:0', '750875316:0'], nodes: [1188762706, 3983027172, 3983027170, 7020175148],
    turnLanes: 'left|left' },
];

function clipApproachKerbs(tile, north, south) {
  const downstream = tile.roads.find(road => road.id === '1447712292:0');
  const northRing = downstream?.from === 13283123167 && downstream.width === 6.8 && downstream.layer === 0 &&
    !downstream.tunnel && samePoint(north.at(-1), downstream.geometry[0])
    ? passageRibbon([...north, ...downstream.geometry.slice(1)], 3.4).slice(0, -1)
    : passageRibbon(north, 3.4).slice(0, -1);
  const southRing = passageRibbon(south, 3.4).slice(0, -1);
  for (const kerb of tile.kerbs) {
    if (kerb.layer !== 0) continue;
    const road = tile.roads.find(edge => edge.id === kerb.road);
    if (!road || road.tunnel || road.layer !== 0) continue;
    if ((road.id === '753843011:0' && road.from === 3983027173) ||
        (road.id === '1447712291:0' && road.to === 13283123167)) clipSurfaceKerb(kerb, northRing);
    if (road.id === '750875317:0' && road.to === 1188762706) clipSurfaceKerb(kerb, southRing);
  }
}

/** Fit the two modeled level carriageways beneath the mapped Suntec City roof. */
export function applyTemasekPassages(tiles, elements) {
  const tile = tiles.get(TILE);
  if (!tile) return;
  const ways = new Map(elements.filter(({ type }) => type === 'way').map(way => [way.id, way]));
  const roof = ways.get(ROOF)?.tags;
  if (roof?.name !== 'Suntec City' || roof.building !== 'yes' || roof.min_height !== '5' || roof.height !== '20' ||
      !tile.buildings.some(building => building.id === ROOF && building.height === 20)) return;

  const staged = structuredClone(tile);
  const centerlines = [];
  for (const { ids, nodes, turnLanes } of ROUTES) {
    const chain = ids.map(id => staged.roads.find(edge => edge.id === id));
    if (!chain.every((edge, i) => edge?.oneway && edge.lanes === 2 && edge.width === 6.8 && edge.geometry.length >= 2 &&
        PUBLIC_ACCESS.has(edge.access) && edge.from === nodes[i] && edge.to === nodes[i + 1] && !edge.bridge &&
        edge.tunnel === (i === 1) && (!i || samePoint(chain[i - 1].geometry.at(-1), edge.geometry[0])))) return;
    const tags = ways.get(chain[1].wayId)?.tags;
    if (tags?.tunnel !== 'building_passage' || tags['turn:lanes'] !== turnLanes || tags.level != null ||
        tags.layer != null || tags.ele != null || tags.incline != null) return;

    const points = chain.flatMap((edge, index) => edge.geometry.slice(index ? 1 : 0));
    centerlines.push(points);
    (staged.roadSurfaces ??= []).push({ edges: ids, geometry: passageRibbon(points, chain[1].width / 2) });
    chain[1].passageRoof = ROOF;
    chain[1].forwardConnector = { id: chain[2].id, lanes: [0, 1] };
    for (const edge of chain) {
      const source = ways.get(edge.wayId)?.tags;
      if (source?.['turn:lanes']) edge.turnLanes = source['turn:lanes'];
      if (source?.toll) edge.toll = source.toll;
    }
  }

  staged.buildings.find(building => building.id === ROOF).minHeight = Number(roof.min_height);
  if (!applyTemasekWalkways(staged, ways)) return;
  clipApproachKerbs(staged, ...centerlines);
  Object.assign(tile, staged);
  for (const fragment of tiles.values()) {
    for (const building of fragment.buildings) {
      if (building.id === ROOF) building.minHeight = Number(roof.min_height);
    }
  }
}
