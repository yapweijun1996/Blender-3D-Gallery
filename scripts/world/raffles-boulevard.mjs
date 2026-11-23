import { offsetPolyline } from '../../src/world/network/geometry.js';

// This at-grade simulation is limited to the pinned map records assessed in docs/verification.
const ROOF = 393090492;
const PASSAGE = 479745478;
const CHAIN = ['649944021:0', '479745478:0', '479745478:1', '479745479:0', '479745479:1'];
const FOOTWAYS = new Set(['749001558:4', '749001558:7']);

export function applyRafflesPassage(tiles, elements) {
  const tile = tiles.get('-1_-4');
  if (!tile) return;
  const road = elements.find(item => item.type === 'way' && item.id === PASSAGE);
  const roof = elements.find(item => item.type === 'way' && item.id === ROOF);
  if (road?.tags?.tunnel !== 'building_passage' || road.tags.maxheight !== '4.5' ||
      roof?.tags?.min_height !== '4.5' || roof.tags.height !== '6' || !tile.buildings.some(item => item.id === ROOF)) return;
  const chain = CHAIN.map(id => tile.roads.find(item => item.id === id));
  if (!chain.every((edge, i) => edge?.oneway && edge.width === 17 && edge.lanes === 5 &&
      (!i || chain[i - 1].to === edge.from))) return;

  const points = chain.flatMap((edge, i) => i ? edge.geometry.slice(1) : edge.geometry);
  const halfWidth = chain[0].width / 2;
  const left = offsetPolyline(points, halfWidth), right = offsetPolyline(points, -halfWidth);
  tile.roadSurfaces = [{ edges: CHAIN, geometry: [...left, ...right.reverse(), left[0]]
    .map(point => point.map(value => Math.round(value * 1000) / 1000)) }];
  for (const edge of chain) {
    if (edge.wayId === PASSAGE) edge.passageRoof = ROOF;
    const tags = elements.find(item => item.type === 'way' && item.id === edge.wayId)?.tags;
    if (tags?.['busway:left'] === 'lane' && tags['lanes:bus'] === '1') edge.leftBusLane = true;
  }
  for (const path of tile.pedestrian) {
    if (!FOOTWAYS.has(path.id)) continue;
    path.besideCarriageway = true;
    // The first leg of :4 enters the Millenia Walk solid. Walkers start at the next mapped vertex outside it.
    if (path.id === '749001558:4') path.walkFrom = 1;
  }
  for (const fragment of tiles.values()) {
    for (const building of fragment.buildings) {
      if (building.id === ROOF) building.minHeight = Number(roof.tags.min_height);
    }
  }
}
