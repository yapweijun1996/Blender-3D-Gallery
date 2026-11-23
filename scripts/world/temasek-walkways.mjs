import { cross, offsetPolyline } from '../../src/world/network/geometry.js';
import { ringArea } from './tile-geometry.mjs';

const NORTH_APPROACH = '1321783357:1';
const NORTH_COVERED = '1321783356:0';
const SOUTH = '1321783027:0';
const CORRIDOR = '460300678:6';
const BUILDING = 393210509;
const THROUGH = ['395443687:0', '395443688:0'];
const WALK_OFFSET = .55;
const WALK_TAPER = 8;
const UPPER_INSET = 1.5;
const UPPER_FLOOR = 5.3; // Game datum: 0.3 m above the soffit. The source floor label has no elevation.

const round = number => Math.round(number * 1000) / 1000;
const interpolate = (a, b, t) => a.map((x, axis) => x + (b[axis] - x) * t);
const pairs = path => path.slice(1).map((b, i) => [path[i], b]);
const samePoint = (a, b) => a?.every((value, axis) => value === b?.[axis]);
const distance = (a, b) => Math.hypot(b[0] - a[0], b[1] - a[1]);

function finiteLine(line) {
  return Array.isArray(line) && line.length >= 2 && Array.from(line).every((point, i) =>
    Array.isArray(point) && point.length === 2 && Number.isFinite(point[0]) && Number.isFinite(point[1]) &&
    (!i || !samePoint(point, line[i - 1])));
}

function convexRoof(geometry) {
  if (!finiteLine(geometry) || geometry.length !== 5 || !samePoint(geometry[0], geometry.at(-1))) return false;
  const ring = geometry.slice(0, -1), winding = Math.sign(ringArea(geometry));
  return winding !== 0 && ring.every((a, i) =>
    winding * cross(a, ring[(i + 1) % ring.length], ring[(i + 2) % ring.length]) > 0);
}

function sidewalk(path, ways) {
  const tags = ways.get(path?.wayId)?.tags;
  return path?.class === 'footway' && finiteLine(path.geometry) && tags?.highway === 'footway' &&
    tags.footway === 'sidewalk' && tags.indoor !== 'yes' && tags.layer == null && tags.level == null &&
    tags.ele == null && tags.incline == null;
}

function shiftedWalk(points, side) {
  const shifted = offsetPolyline(points, side * WALK_OFFSET);
  if (shifted.length !== points.length) return;
  const stations = [0];
  for (const [a, b] of pairs(points)) stations.push(stations.at(-1) + distance(a, b));
  const length = stations.at(-1);
  if (length <= 2 * WALK_TAPER || stations.some((s, i) => i > 0 && s <= stations[i - 1])) return;

  // The safe offsets cover the conflict area. Start and end on the original mapped connections.
  const breaks = [...new Set([...stations, WALK_TAPER, length - WALK_TAPER])].sort((a, b) => a - b);
  return breaks.map(s => {
    const next = stations.findIndex(station => station > s);
    const i = next === -1 ? stations.length - 2 : next - 1;
    const t = (s - stations[i]) / (stations[i + 1] - stations[i]);
    const spine = interpolate(points[i], points[i + 1], t);
    const outer = interpolate(shifted[i], shifted[i + 1], t);
    const blend = Math.min(1, s / WALK_TAPER, (length - s) / WALK_TAPER);
    return interpolate(spine, outer, blend).map(round);
  });
}

function clipToRoof(a, b, footprint) {
  const winding = Math.sign(ringArea(footprint));
  let low = 0, high = 1;
  for (const [c, d] of pairs(footprint)) {
    const length = distance(c, d);
    if (length === 0) continue;
    const signed = point => winding * cross(c, d, point) / length - UPPER_INSET;
    const from = signed(a), to = signed(b);
    if (from < 0 && to < 0) return;
    if (from < 0 || to < 0) {
      const part = from / (from - to);
      if (from < 0) low = Math.max(low, part);
      else high = Math.min(high, part);
    }
  }
  if (low < high) return [interpolate(a, b, low).map(round), interpolate(a, b, high).map(round)];
}

function crosses(a, b, c, d) {
  return cross(a, b, c) * cross(a, b, d) < 0 && cross(c, d, a) * cross(c, d, b) < 0;
}

/** Annotate the audited walkways only after all inputs support the modeled floor and connections. */
export function applyTemasekWalkways(tile, ways) {
  if (!(ways instanceof Map) || ![tile?.pedestrian, tile?.buildings, tile?.roads].every(Array.isArray)) return false;
  const [approach, covered, south, upper] = [NORTH_APPROACH, NORTH_COVERED, SOUTH, CORRIDOR]
    .map(id => tile.pedestrian.find(path => path?.id === id));
  const roof = tile.buildings.find(building => building?.id === BUILDING);
  const roofTags = ways.get(BUILDING)?.tags;
  const tags = ways.get(upper?.wayId)?.tags;

  if (!roof || roof.minHeight !== 5 || roof.height !== 20 || !convexRoof(roof.geometry) ||
      roofTags?.min_height !== '5' || roofTags.height !== '20' ||
      ![approach, covered, south].every(path => sidewalk(path, ways)) ||
      ways.get(covered.wayId).tags.covered !== 'yes' ||
      approach.to !== covered.from || !samePoint(approach.geometry.at(-1), covered.geometry[0]) ||
      tags?.highway !== 'corridor' || tags.indoor !== 'yes' || tags.level !== '1' || tags.layer !== '-1' ||
      upper?.class !== 'corridor' || !finiteLine(upper.geometry)) return false;

  const northWalk = shiftedWalk([...approach.geometry, ...covered.geometry.slice(1)], 1);
  const southWalk = shiftedWalk(south.geometry, -1);
  // Only this continuous segment is supported by the modeled structure. Keep the raw indoor geometry for reference.
  const deckSections = pairs(upper.geometry).flatMap(([a, b]) => {
    const clipped = clipToRoof(a, b, roof.geometry);
    return clipped ? [clipped] : [];
  });
  if (!northWalk || !southWalk || deckSections.length !== 1) return false;
  const deckGeometry = deckSections[0];
  if (!THROUGH.every(id => {
    const road = tile.roads.find(edge => edge?.id === id);
    return finiteLine(road?.geometry) && pairs(road.geometry).some(([a, b]) => crosses(...deckGeometry, a, b));
  })) return false;

  Object.assign(approach, { besideCarriageway: true, walkGeometry: northWalk });
  Object.assign(covered, { besideCarriageway: true, walkGeometry: [] });
  Object.assign(south, { besideCarriageway: true, walkGeometry: southWalk });
  Object.assign(upper, { indoorLevel: Number(tags.level), floorHeight: UPPER_FLOOR, deckGeometry });
  return true;
}
