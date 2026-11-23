import { cross } from "./geometry.js";

const EPSILON = 1e-7;

export const between = (a, b, t) => [a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])];
const crossVector = ([ax, az], [bx, bz]) => ax * bz - az * bx;
const subtract = (a, b) => [a[0] - b[0], a[1] - b[1]];

function inside(point, ring) {
  let result = false;
  const [x, z] = point;
  for (let i = 0; i < ring.length; i++) {
    const a = ring[i], b = ring[(i + 1) % ring.length];
    if (Math.abs(cross(a, b, point)) < EPSILON &&
        x >= Math.min(a[0], b[0]) - EPSILON && x <= Math.max(a[0], b[0]) + EPSILON &&
        z >= Math.min(a[1], b[1]) - EPSILON && z <= Math.max(a[1], b[1]) + EPSILON) return false;
    if ((a[1] > z) !== (b[1] > z) && x < a[0] + (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1])) result = !result;
  }
  return result;
}

/** Subdivide a segment at a footprint boundary. A segment on the boundary stays outside. */
export function splitByRing(a, b, ring) {
  const cuts = [0, 1], path = subtract(b, a), lengthSquared = path[0] ** 2 + path[1] ** 2;
  if (lengthSquared <= EPSILON ** 2) return [];
  for (let i = 0; i < ring.length; i++) {
    const c = ring[i], d = ring[(i + 1) % ring.length];
    const edge = subtract(d, c), offset = subtract(c, a), denominator = crossVector(path, edge);
    if (Math.abs(denominator) <= EPSILON) {
      if (Math.abs(crossVector(offset, path)) <= EPSILON) {
        for (const point of [c, d]) {
          const [x, z] = subtract(point, a);
          const t = (x * path[0] + z * path[1]) / lengthSquared;
          if (t > 0 && t < 1) cuts.push(t);
        }
      }
      continue;
    }
    const t = crossVector(offset, edge) / denominator, u = crossVector(offset, path) / denominator;
    if (t > 0 && t < 1 && u >= -EPSILON && u <= 1 + EPSILON) cuts.push(t);
  }
  cuts.sort((a, b) => a - b);
  const output = [];
  let start = cuts[0];
  for (const end of cuts.slice(1)) {
    if (end - start <= EPSILON) continue;
    output.push({ start, end, inside: inside(between(a, b, (start + end) / 2), ring) });
    start = end;
  }
  return output;
}
