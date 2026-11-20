export const samePoint = (a, b) => a[0] === b[0] && a[1] === b[1];
export const cross = (a, b, c) =>
  (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);

export function distinctPoints(points) {
  return points.filter((point, index) => index === 0 || !samePoint(point, points[index - 1]));
}

function distanceSquared(point, start, end) {
  const dx = end[0] - start[0];
  const dz = end[1] - start[1];
  const lengthSquared = dx * dx + dz * dz;
  const along = lengthSquared
    ? Math.max(0, Math.min(1, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dz) / lengthSquared))
    : 0;
  return (point[0] - start[0] - dx * along) ** 2 + (point[1] - start[1] - dz * along) ** 2;
}

/** Douglas–Peucker, preserving both endpoints, including the anchor of a closed ring. */
export function simplifyPolyline(points, tolerance = 0.5) {
  if (points.length <= 2) return points.slice();
  const end = points.length - 1;
  const keep = new Set([0, end]);
  const pending = [[0, end]];
  while (pending.length) {
    const [first, last] = pending.pop();
    let farthest = first;
    let limit = tolerance ** 2;
    for (let i = first + 1; i < last; i++) {
      const distance = distanceSquared(points[i], points[first], points[last]);
      if (distance > limit) {
        farthest = i;
        limit = distance;
      }
    }
    if (farthest === first) continue;
    keep.add(farthest);
    pending.push([first, farthest], [farthest, last]);
  }
  return points.filter((_, index) => keep.has(index));
}

function leftNormal(a, b) {
  const dx = b[0] - a[0];
  const dz = b[1] - a[1];
  const length = Math.hypot(dx, dz);
  return [dz / length, -dx / length];
}

/** Positive offset is geographical left of travel. Bevel tight bends to limit spikes. */
export function offsetPolyline(points, offset) {
  const line = distinctPoints(points);
  if (!offset || line.length < 2) return line;
  const normals = line.slice(1).map((point, i) => leftNormal(line[i], point));
  const shift = (point, normal, distance) =>
    [point[0] + normal[0] * distance, point[1] + normal[1] * distance];
  return line.flatMap((point, i) => {
    const before = normals[i - 1];
    const after = normals[i];
    if (!before || !after) return [shift(point, before ?? after, offset)];
    const dot = before[0] * after[0] + before[1] * after[1];
    if (1 + dot < 0.5) return [shift(point, before, offset), shift(point, after, offset)];
    return [shift(point, [before[0] + after[0], before[1] + after[1]], offset / (1 + dot))];
  });
}

export function convexHull(points) {
  const sorted = distinctPoints(points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]));
  function half(sequence) {
    const hull = [];
    for (const point of sequence) {
      while (hull.length >= 2 && cross(hull.at(-2), hull.at(-1), point) <= 0) hull.pop();
      hull.push(point);
    }
    return hull.slice(0, -1);
  }
  return [...half(sorted), ...half(sorted.reverse())];
}
