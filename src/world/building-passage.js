import { ShapeUtils, Vector2 } from "three";
import { cross } from "./network/geometry.js";
import { between, splitByRing } from "./network/polygon.js";

const EPSILON = 1e-7;

function shape(ring) {
  if (!Array.isArray(ring) || ring.length < 4 ||
      !ring.every(point => Array.isArray(point) && point.length === 2 && point.every(Number.isFinite)) ||
      ring[0].some((value, index) => value !== ring.at(-1)[index])) {
    throw new RangeError("A building and its passage need closed finite rings");
  }
  const points = ring.slice(0, -1).map(point => point.slice());
  const vectors = points.map(point => new Vector2(...point));
  const triangles = ShapeUtils.triangulateShape(vectors, []);
  if (!triangles.length) throw new RangeError("A building passage footprint needs a nonempty interior");
  return { points, clockwise: ShapeUtils.isClockWise(vectors), triangles: triangles.map(face => face.map(i => points[i])) };
}

function clipToTriangle(polygon, triangle) {
  const orientation = Math.sign(cross(...triangle));
  if (!orientation) return [];
  for (let i = 0; i < 3 && polygon.length; i++) {
    const a = triangle[i], b = triangle[(i + 1) % 3];
    const clipped = [];
    let previous = polygon.at(-1), previousSide = orientation * cross(a, b, previous);
    for (const point of polygon) {
      const side = orientation * cross(a, b, point);
      if ((side >= 0) !== (previousSide >= 0)) clipped.push(between(previous, point, previousSide / (previousSide - side)));
      if (side >= 0) clipped.push(point);
      previous = point;
      previousSide = side;
    }
    polygon = clipped;
  }
  return polygon;
}

/** The exterior shell and the cavity share one mesh for the visible building and its static collider. */
export function createBuildingPassageMesh(buildingRing, height, { floor, soffit, geometry }, { bay, storey }) {
  if (floor !== 0 || !Number.isFinite(soffit) || !Number.isFinite(height) || soffit <= floor || height <= soffit) {
    throw new RangeError("A ground-level building passage needs a soffit below the building roof");
  }
  const building = shape(buildingRing), passage = shape(geometry);
  const vertices = [], indices = [], facadeUV = [], byPoint = new Map();
  function vertex(point, y) {
    const [x, z] = point, key = [x, y, z].map(Math.fround).join(",");
    if (!byPoint.has(key)) {
      byPoint.set(key, vertices.length / 3);
      vertices.push(x, y, z);
    }
    return byPoint.get(key);
  }
  function wall(a, b, low, high, reverse, u0, u1) {
    const corners = [vertex(a, low), vertex(b, low), vertex(b, high), vertex(a, high)];
    const order = reverse ? [0, 2, 1, 0, 3, 2] : [0, 1, 2, 0, 2, 3];
    for (const i of order) indices.push(corners[i]);
    if (u0 === undefined) return;
    const levels = Math.max(1, Math.round(height / storey));
    const uv = [[u0, low / height * levels], [u1, low / height * levels], [u1, high / height * levels], [u0, high / height * levels]];
    for (const i of order) facadeUV.push(...uv[i]);
  }
  function horizontal(a, b, c, y, facesUp) {
    const area = cross(a, b, c);
    if (Math.abs(area) <= EPSILON) return;
    if ((area < 0) !== facesUp) [b, c] = [c, b];
    indices.push(vertex(a, y), vertex(b, y), vertex(c, y));
  }

  let distance = 0;
  for (const [i, a] of building.points.entries()) {
    const b = building.points[(i + 1) % building.points.length];
    const length = Math.hypot(b[0] - a[0], b[1] - a[1]);
    for (const span of splitByRing(a, b, passage.points)) {
      wall(between(a, b, span.start), between(a, b, span.end), span.inside ? soffit : 0, height,
        !building.clockwise, (distance + span.start * length) / bay, (distance + span.end * length) / bay);
    }
    distance += length;
  }

  for (const [i, a] of passage.points.entries()) {
    const b = passage.points[(i + 1) % passage.points.length];
    for (const span of splitByRing(a, b, building.points)) {
      if (span.inside) wall(between(a, b, span.start), between(a, b, span.end), floor, soffit, passage.clockwise);
    }
  }

  for (const triangle of building.triangles) horizontal(...triangle, height, true);
  const soffitStart = indices.length;
  for (const triangle of building.triangles) {
    for (const cutter of passage.triangles) {
      const polygon = clipToTriangle(triangle, cutter);
      for (let i = 2; i < polygon.length; i++) horizontal(polygon[0], polygon[i - 1], polygon[i], soffit, false);
    }
  }
  if (indices.length === soffitStart) throw new RangeError("The passage does not intersect its associated building");
  return { vertices: Float32Array.from(vertices), indices: Uint32Array.from(indices), facadeUV };
}
