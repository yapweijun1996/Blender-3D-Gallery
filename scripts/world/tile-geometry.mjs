import { distinctPoints, samePoint } from '../../src/world/network/geometry.js';

const mix = (a, b, t) => a + (b - a) * t;

function clipSegment(a, b, bounds) {
  let enter = 0;
  let exit = 1;
  for (let axis = 0; axis < 2; axis++) {
    const delta = b[axis] - a[axis];
    const minimum = bounds.min[axis];
    const maximum = bounds.max[axis];
    if (delta === 0) {
      if (a[axis] < minimum || a[axis] > maximum) return null;
      continue;
    }
    const low = (minimum - a[axis]) / delta;
    const high = (maximum - a[axis]) / delta;
    enter = Math.max(enter, Math.min(low, high));
    exit = Math.min(exit, Math.max(low, high));
    if (enter >= exit) return null;
  }
  return [enter === 0 ? a : a.map((value, i) => mix(value, b[i], enter)),
    exit === 1 ? b : a.map((value, i) => mix(value, b[i], exit))];
}

export function clipLine(points, bounds) {
  const fragments = [];
  let current;
  for (let i = 1; i < points.length; i++) {
    const segment = clipSegment(points[i - 1], points[i], bounds);
    if (!segment) {
      current = undefined;
      continue;
    }
    const [start, end] = segment;
    if (current && samePoint(current.at(-1), start)) {
      current.push(end);
    } else {
      current = [start, end];
      fragments.push(current);
    }
  }
  return fragments;
}

export function ringArea(ring) {
  if (!ring.length) return 0;
  const [x, z] = ring[0];
  let area = 0;
  for (let i = 1; i < ring.length - 1; i++) {
    const [ax, az] = ring[i];
    const [bx, bz] = ring[i + 1];
    area += (ax - x) * (bz - z) - (az - z) * (bx - x);
  }
  return area / 2;
}

export function clipRing(ring, bounds) {
  let points = ring.slice(0, -1);
  for (let axis = 0; axis < 2; axis++) {
    for (const side of ['min', 'max']) {
      if (points.length < 3) return [];
      const limit = bounds[side][axis];
      const inside = point => side === 'min' ? point[axis] >= limit : point[axis] <= limit;
      const clipped = [];
      let previous = points.at(-1);
      for (const point of points) {
        if (inside(point) !== inside(previous)) {
          const t = (limit - previous[axis]) / (point[axis] - previous[axis]);
          clipped.push(point.map((value, i) => i === axis ? limit : mix(previous[i], value, t)));
        }
        if (inside(point)) clipped.push(point);
        previous = point;
      }
      points = distinctPoints(clipped);
    }
  }
  return Math.abs(ringArea(points)) > 1e-6 ? [...points, points[0]] : [];
}

/** Distance along a polyline to the point on it nearest to `point` (used to place a clipped fragment on its full edge). */
export function alongPolyline(points, point) {
  let best = { distance: Infinity, along: 0 }, travelled = 0;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], sx = b[0] - a[0], sz = b[1] - a[1], span = sx * sx + sz * sz;
    const length = Math.sqrt(span);
    const t = span === 0 ? 0 : Math.max(0, Math.min(1, ((point[0] - a[0]) * sx + (point[1] - a[1]) * sz) / span));
    const distance = Math.hypot(point[0] - (a[0] + sx * t), point[1] - (a[1] + sz * t));
    if (distance < best.distance) best = { distance, along: travelled + t * length };
    travelled += length;
  }
  return best.along;
}

export function polylineLength(points) {
  let total = 0;
  for (let i = 1; i < points.length; i++) total += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
  return total;
}
