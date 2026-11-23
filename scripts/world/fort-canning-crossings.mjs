import { cross, distinctPoints, offsetPolyline, samePoint } from '../../src/world/network/geometry.js';
import { LANE_WIDTH } from '../../src/world/network/graph.js';
import { polylineLength, ringArea } from './tile-geometry.mjs';
import { TILE_SIZE } from './build-tiles.mjs';

const EPSILON = 1e-7;
const round = value => Math.round(value * 1e6) / 1e6 || 0;
const mix = (a, b, fraction) => a.map((value, axis) => value + (b[axis] - value) * fraction);

// Match the averaged end tangents used for the flat ribbons in world/tile-mesh.js.
function ribbon(points, width) {
  const offsets = points.map((point, index) => {
    const a = points[Math.max(0, index - 1)], b = points[Math.min(points.length - 1, index + 1)];
    const dx = b[0] - a[0], dz = b[1] - a[1];
    const factor = width / (2 * (Math.hypot(dx, dz) || 1));
    return [[point[0] - dz * factor, point[1] + dx * factor], [point[0] + dz * factor, point[1] - dx * factor]];
  });
  return offsets.slice(1).flatMap(([left, right], index) => {
    const [previousLeft, previousRight] = offsets[index];
    return [[previousLeft, previousRight, right], [previousLeft, right, left]];
  });
}

// Crosswalk records carry a point or mapped line. Rendering aligns the zebra bars with the closest road.
function zebra(tile, point, toWorld) {
  let best = null;
  for (const road of tile.roads) {
    if (road.tunnel || (road.width ?? 0) < 5) continue;
    for (let index = 1; index < road.geometry.length; index++) {
      const [x, z] = road.geometry[index - 1], [nx, nz] = road.geometry[index];
      const dx = nx - x, dz = nz - z, length = Math.hypot(dx, dz) || 1;
      const tx = dx / length, tz = dz / length;
      const along = Math.max(0, Math.min(length, (point[0] - x) * tx + (point[1] - z) * tz));
      const px = x + tx * along, pz = z + tz * along;
      const distance = Math.hypot(point[0] - px, point[1] - pz);
      if (distance < 4 && distance < (best?.distance ?? Infinity)) best = { px, pz, tx, tz, distance, width: road.width };
    }
  }
  if (!best) return [];
  const { px, pz, tx, tz, width } = best;
  const stripes = [];
  for (let across = -width / 2 + 0.7; across <= width / 2 - 0.7; across++) {
    const corner = (along, side) => toWorld([px + tx * along - tz * (across + side), pz + tz * along + tx * (across + side)]);
    stripes.push([corner(-1.5, -0.25), corner(1.5, -0.25), corner(1.5, 0.25), corner(-1.5, 0.25)]);
  }
  return stripes;
}

function clipPolygon(points, triangle) {
  const winding = Math.sign(cross(...triangle));
  if (!winding) return [];
  for (const [index, corner] of triangle.entries()) {
    const next = triangle[(index + 1) % 3];
    const side = point => winding * cross(corner, next, point);
    const clipped = [];
    if (!points.length) return clipped;
    let previous = points.at(-1), u = side(previous);
    for (const point of points) {
      const v = side(point);
      if ((u >= 0) !== (v >= 0)) clipped.push(mix(previous, point, u / (u - v)));
      if (v >= 0) clipped.push(point);
      previous = point;
      u = v;
    }
    points = clipped;
  }
  return points;
}

function bounds(points) {
  const x = points.map(point => point[0]), z = points.map(point => point[1]);
  return [Math.min(...x), Math.max(...x), Math.min(...z), Math.max(...z)];
}

function overlaps(a, b) {
  return a[0] <= b[1] && a[1] >= b[0] && a[2] <= b[3] && a[3] >= b[2];
}

function segmentIntersection(a, b, c, d) {
  const ab = [b[0] - a[0], b[1] - a[1]], cd = [d[0] - c[0], d[1] - c[1]];
  const divisor = ab[0] * cd[1] - ab[1] * cd[0];
  if (Math.abs(divisor) < EPSILON) return null;
  const t = cross(c, d, a) / divisor, u = cross(a, c, b) / divisor;
  return t >= -EPSILON && t <= 1 + EPSILON && u >= -EPSILON && u <= 1 + EPSILON ? t : null;
}

function mergedRanges(ranges) {
  const merged = [];
  for (const [start, end] of ranges.toSorted((a, b) => a[0] - b[0])) {
    const last = merged.at(-1);
    if (last && start <= last[1] + EPSILON) last[1] = Math.max(last[1], end);
    else merged.push([start, end]);
  }
  return merged;
}

function joinedLines(fragments) {
  const lines = [];
  for (const fragment of fragments) {
    const previous = lines.findIndex(line => samePoint(line.at(-1), fragment[0]));
    let line = fragment;
    if (previous >= 0) line = [...lines.splice(previous, 1)[0], ...fragment.slice(1)];
    const next = lines.findIndex(other => samePoint(line.at(-1), other[0]));
    if (next >= 0) line = [...line, ...lines.splice(next, 1)[0].slice(1)];
    lines.push(line);
  }
  return lines.sort((a, b) => polylineLength(b) - polylineLength(a));
}

function footprint(path, width) {
  const points = path.map(point => [point.x, point.z]);
  const left = offsetPolyline(points, width / 2), right = offsetPolyline(points, -width / 2);
  if (left.length !== points.length || right.length !== points.length) throw new Error('The Link footprint has an unexpected bevel');
  return points.slice(1).flatMap((end, index) => {
    const start = points[index], s = path[index].s, next = path[index + 1].s;
    const variants = [
      { triangle: [left[index], right[index], left[index + 1]], stations: [s, s, next] },
      { triangle: [right[index], right[index + 1], left[index + 1]], stations: [s, next, next] },
    ];
    return variants.map(({ triangle, stations }, side) => ({ triangle, stations, aabb: bounds(triangle),
      ...(side === 0 ? { center: { start, end, s, next } } : {}) }));
  });
}

export function corridorBounds(path, width) {
  return bounds(footprint(path, width).flatMap(({ triangle }) => triangle));
}

function overlapStation(corners, stations, point) {
  const [a, b, c] = corners;
  const divisor = cross(a, b, c);
  const weights = [cross(point, b, c), cross(a, point, c), cross(a, b, point)];
  return weights.reduce((station, weight, index) => station + weight * stations[index] / divisor, 0);
}

const SOURCES = {
  roads: 'road', pedestrian: 'pedestrian', crossings: 'crosswalk', junctions: 'junction', parks: 'park', water: 'water', buildings: 'building',
};

export function scanCorridorCrossings({ path, tiles, ways, width, routeIds, length, roof }) {
  const strips = footprint(path, width);
  const results = new Map();
  for (const tile of tiles) {
    const tileKey = `${tile.x}_${tile.z}`;
    const toWorld = ([x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];
    const tileStrips = strips.filter(({ aabb }) => overlaps(aabb, [tile.x * TILE_SIZE, (tile.x + 1) * TILE_SIZE, tile.z * TILE_SIZE, (tile.z + 1) * TILE_SIZE]));
    for (const [layer, kind] of Object.entries(SOURCES)) {
      for (const feature of tile[layer]) {
        if (kind === 'road' && (routeIds.has(feature.id) || feature.tunnel || feature.bridge && feature.layer > 0)) continue;
        const geometry = feature.geometry ?? [];
        const marker = kind === 'crosswalk' ? feature.point ?? geometry[geometry.length >> 1] : null;
        const points = distinctPoints((geometry.length ? geometry : marker ? [marker] : []).map(toWorld));
        if (!marker && points.length < 2) continue;
        const edgeId = String(feature.id ?? feature.nodeId);
        const width = kind === 'road' ? feature.width ?? Math.max(LANE_WIDTH, (feature.lanes ?? 2) * LANE_WIDTH)
          : kind === 'pedestrian' ? 2.2 : null;
        const shapes = marker ? zebra(tile, marker, toWorld) : width ? ribbon(points, width) : [points.slice(0, -1)];
        const ranges = [], crossings = [];
        for (const shape of shapes) {
          const shapeBounds = bounds(shape);
          for (const { triangle, stations, aabb } of tileStrips) {
            if (!overlaps(aabb, shapeBounds)) continue;
            const clipped = clipPolygon(shape, triangle);
            if (clipped.length < 3 || Math.abs(ringArea(clipped)) < EPSILON) continue;
            const values = clipped.map(point => overlapStation(triangle, stations, point));
            ranges.push([Math.min(...values), Math.max(...values)]);
          }
        }
        if (!ranges.length) continue;
        if (width) for (const { center } of tileStrips) {
          if (!center) continue;
          const { start, end, s, next } = center;
          for (let index = 1; index < points.length; index++) {
            const t = segmentIntersection(start, end, points[index - 1], points[index]);
            if (t === null) continue;
            const [x, z] = mix(start, end, t).map(round);
            crossings.push({ s: round(s + t * (next - s)), x, z });
          }
        }
        const id = `${kind}:${edgeId}`;
        const source = ways.get(feature.wayId ?? feature.id)?.tags ?? {};
        const entry = results.get(id) ?? { edgeId, kind, name: feature.name ?? source.name ?? null, width,
          osmLayer: Number(source.layer ?? feature.layer ?? 0), bridge: source.bridge ?? null,
          minHeight: source.min_height ?? null, pieces: [], ranges: [], crossings: [], tiles: [] };
        entry.pieces.push(points);
        entry.tiles.push(tileKey);
        entry.ranges.push(...ranges);
        entry.crossings.push(...crossings);
        results.set(id, entry);
      }
    }
  }
  return [...results.values()].map(({ pieces, ranges, crossings, tiles, ...entry }) => {
    const merged = mergedRanges(ranges);
    const cut = merged.flatMap(([a, b]) => [[Math.max(0, a), Math.min(roof.start, b)], [Math.max(roof.end, a), Math.min(length, b)]])
      .filter(([a, b]) => b - a > EPSILON).map(interval => interval.map(round));
    const centers = [...new Map(crossings.map(point => [point.s, point])).values()].sort((a, b) => a.s - b.s);
    const lines = entry.width ? joinedLines(pieces) : pieces;
    return { ...entry, tiles: [...new Set(tiles)].sort(), points: lines[0].map(point => point.map(round)),
      start: round(merged[0][0]), end: round(merged.at(-1)[1]), at: centers[0] ?? null,
      ranges: merged.map(interval => interval.map(round)), openCut: cut,
      roofCovered: merged.every(([a, b]) => a + EPSILON >= roof.start && b - EPSILON <= roof.end) };
  }).sort((a, b) => a.start - b.start || a.kind.localeCompare(b.kind) || a.edgeId.localeCompare(b.edgeId));
}
