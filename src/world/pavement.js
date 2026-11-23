// A planar ribbon catches rays but can lose capsule contact during sustained walking.
// Give its existing triangles a 120 mm backing while preserving the exact drawn top.
const DEPTH = .12;
const indices = Uint32Array.of(0, 1, 2, 3, 5, 4, 0, 3, 1, 1, 3, 4, 1, 4, 2, 2, 4, 5, 2, 5, 0, 0, 5, 3);

export function pavementPanel(a, b, c) {
  const up = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2]);
  const corners = up > 0 ? [a, b, c] : [a, c, b];
  const position = Float32Array.from([
    ...corners.flatMap(point => [...point]),
    ...corners.flatMap(([x, y, z]) => [x, y - DEPTH, z]),
  ]);
  return { id: "footway", position, indices, convex: true };
}
