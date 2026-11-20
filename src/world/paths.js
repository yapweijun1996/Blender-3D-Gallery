// Footway paths from the map tiles: world-space polylines people walk along (no rendering, no assets).
const WALKING = new Set(["footway", "pedestrian", "path"]);

/** Footways of the loaded tiles as world-space polylines with cumulative lengths. */
export function pedestrianPaths(tiles) {
  const paths = [];
  for (const tile of tiles) {
    for (const way of tile.pedestrian ?? []) {
      if (!WALKING.has(way.class) || way.geometry.length < 2) continue;
      const points = way.geometry.map(([x, z]) => [x + tile.x * 250, z + tile.z * 250]);
      const cumulative = [0];
      for (let i = 1; i < points.length; i++) cumulative.push(cumulative[i - 1] + Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]));
      const length = cumulative.at(-1);
      if (length < 12) continue;
      const middle = points[points.length >> 1];
      paths.push({ points, cumulative, length, x: middle[0], z: middle[1] });
    }
  }
  return paths;
}

/** Position and unit direction at distance s along a path. */
export function samplePath(path, s) {
  const d = Math.max(0, Math.min(path.length, s));
  let i = 1;
  while (i < path.cumulative.length - 1 && path.cumulative[i] < d) i++;
  const a = path.points[i - 1], b = path.points[i], span = path.cumulative[i] - path.cumulative[i - 1] || 1;
  const k = (d - path.cumulative[i - 1]) / span;
  return { x: a[0] + (b[0] - a[0]) * k, z: a[1] + (b[1] - a[1]) * k, dx: (b[0] - a[0]) / span, dz: (b[1] - a[1]) / span };
}

