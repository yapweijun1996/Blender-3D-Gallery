import { samePoint } from '../../src/world/network/geometry.js';
import { between, splitByRing } from '../../src/world/network/polygon.js';

const BRIDGE = 460302684;
const BRIDGE_BUILDING = 620812487;
const ENDS = [
  { corridor: 460302683, building: 46594821, node: 4559764872 }, // One Raffles Link.
  { corridor: 460300683, building: 303311927, node: 4559780649 }, // Marina Square.
];
const WALL_INSET = 1.6;
const DECK_HALF_WIDTH = 1.1;
const WALKER_RADIUS = .32;
const SOFFIT = 4.5;
const FLOOR = 4.8; // Modeled height 0.3 m above the soffit. The source gives a level label.

const point = p => Array.isArray(p) && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1]);
const length = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);
const pairs = points => points.slice(1).map((end, i) => [points[i], end]);

function openRing(geometry) {
  if (!Array.isArray(geometry) || geometry.length < 4 || !Array.from(geometry).every(point) ||
      !samePoint(geometry[0], geometry.at(-1)) || pairs(geometry).some(([a, b]) => samePoint(a, b))) return null;
  return geometry.slice(0, -1);
}

function distanceToFacade(p, ring) {
  return Math.min(...ring.map((a, i) => {
    const b = ring[(i + 1) % ring.length];
    const dx = b[0] - a[0], dz = b[1] - a[1];
    const t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / (dx * dx + dz * dz);
    return length(p, between(a, b, Math.max(0, Math.min(1, t))));
  }));
}

function indoorCorridor(way) {
  const tags = way?.tags;
  return tags?.highway === 'corridor' && tags.indoor === 'yes' && tags.level === '1';
}

function corridor(tile, id) {
  const path = tile.pedestrian.find(item => item?.id === id + ':0');
  if (path?.wayId === id && path.class === 'corridor' && path.geometry?.length >= 2 &&
      Array.from(path.geometry).every(point)) return path;
}

function facadeAtEnd(tile, ways, end, pathPoint) {
  const source = ways.get(end.building);
  if (!source?.nodes?.includes(end.node)) return null;
  const footprints = tile.buildings.filter(item => item?.id === end.building)
    .map(item => openRing(item.geometry)).filter(Boolean);
  // The mapped shared node may lie a few centimeters off the simplified tile facade.
  return footprints.find(ring => distanceToFacade(pathPoint, ring) < .15);
}

function boundsDeck(a, b, width) {
  const span = length(a, b);
  const dx = (b[0] - a[0]) / span, dz = (b[1] - a[1]) / span;
  const side = (p, offset) => [p[0] - dz * offset, p[1] + dx * offset];
  return [side(a, width), side(b, width), side(b, -width), side(a, -width)];
}

/** Place the supported segment inside the bridge shell, between the two existing building walls. */
export function applyRafflesLinkWalkway(tile, ways) {
  if (tile?.x !== -3 || tile.z !== -4 || !(ways instanceof Map) ||
      !Array.isArray(tile.pedestrian) || !Array.isArray(tile.buildings)) return false;
  const crossing = corridor(tile, BRIDGE);
  const [west, east] = ENDS;
  const sources = ENDS.map(({ corridor }) => ways.get(corridor));
  const [before, after] = ENDS.map(({ corridor: id }) => corridor(tile, id));
  const way = ways.get(BRIDGE);
  if (!crossing || crossing.geometry.length !== 2 || !before || !after ||
      ![way, ...sources].every(indoorCorridor) || way.tags.bridge !== 'yes' || way.tags.layer !== '1' ||
      way.nodes?.length !== 2 || way.nodes[0] !== west.node || way.nodes[1] !== east.node ||
      sources[0].nodes?.at(-1) !== west.node || sources[1].nodes?.[0] !== east.node ||
      before.to !== west.node || crossing.from !== west.node || crossing.to !== east.node || after.from !== east.node) return false;
  const [a, b] = crossing.geometry;
  if (!samePoint(before.geometry.at(-1), a) || !samePoint(after.geometry[0], b)) return false;

  const bridge = tile.buildings.find(item => item?.id === BRIDGE_BUILDING);
  const roof = openRing(bridge?.geometry);
  const passage = bridge?.passages?.length === 1 ? bridge.passages[0] : null;
  const opening = openRing(passage?.geometry);
  const walls = [facadeAtEnd(tile, ways, west, a), facadeAtEnd(tile, ways, east, b)];
  const span = length(a, b);
  if (!roof || !opening || passage.floor !== 0 || passage.soffit !== SOFFIT ||
      !Number.isFinite(bridge.height) || bridge.height < FLOOR + 2 ||
      walls.some(wall => !wall) || span <= 2 * WALL_INSET) return false;

  const round = value => Math.round(value * 1000) / 1000;
  const deck = [between(a, b, WALL_INSET / span), between(a, b, 1 - WALL_INSET / span)].map(p => p.map(round));
  const safe = boundsDeck(...deck, DECK_HALF_WIDTH + WALKER_RADIUS);
  const staysInside = (a, b) => splitByRing(a, b, roof).every(span => span.inside);
  if (!pairs([...safe, safe[0]]).every(([a, b]) =>
    staysInside(a, b) && walls.every(wall => splitByRing(a, b, wall).every(span => !span.inside)))) return false;

  // Check both deck edges as well as the centerline span the full width of the passage.
  const strip = boundsDeck(...deck, DECK_HALF_WIDTH);
  if (![deck, strip.slice(0, 2), strip.slice(2)].every(([a, b]) => {
    const spans = splitByRing(a, b, opening);
    return spans.length === 3 && !spans[0].inside && spans[1].inside && !spans[2].inside;
  })) return false;

  Object.assign(crossing, { indoorLevel: 1, floorHeight: FLOOR, deckGeometry: deck });
  for (const approach of [before, after]) approach.indoorLevel = 1;
  return true;
}
