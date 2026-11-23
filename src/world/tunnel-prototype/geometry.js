import { ShapeUtils, Vector2 } from "three";

const CLEARANCE = 4.7;
const MIN_ROOF_THICKNESS = 0.2;
const TERRAIN_MARGIN = 40;

function unitDirection(from, to) {
  const x = to.x - from.x, z = to.z - from.z;
  const length = Math.hypot(x, z);
  return [x / length, z / length];
}

function pointOffset(section, offset, y = section.y) {
  return [section.x + section.rx * offset, y, section.z + section.rz * offset];
}

function meshData(id, positions, indices) {
  return { id, position: new Float32Array(positions), indices: new Uint32Array(indices) };
}

function appendStrip(positions, indices, rows, left, right) {
  const start = positions.length / 3;
  for (const [index, row] of rows.entries()) {
    positions.push(...left(row), ...right(row));
    if (index === 0) continue;
    const a = start + 2 * (index - 1), b = a + 2;
    indices.push(a, a + 1, b, a + 1, b + 1, b);
  }
}

function strip(id, rows, left, right) {
  const positions = [], indices = [];
  appendStrip(positions, indices, rows, left, right);
  return meshData(id, positions, indices);
}

export function terrainSurfaceFromHole({ minX, maxX, minZ, maxZ }, boundary) {
  const outline = [[minX, minZ], [minX, maxZ], [maxX, maxZ], [maxX, minZ]].map(point => new Vector2(...point));
  const hole = boundary.map(point => new Vector2(...point));
  const triangles = ShapeUtils.triangulateShape(outline, [hole]);
  const points = [...outline, ...hole];
  const indices = triangles.flatMap(([a, b, c]) => {
    const p = points[a], q = points[b], r = points[c];
    const up = (q.y - p.y) * (r.x - p.x) - (q.x - p.x) * (r.y - p.y);
    return up >= 0 ? [a, b, c] : [a, c, b];
  });
  return meshData("terrain", points.flatMap(({ x, y }) => [x, 0, y]), indices);
}

function terrainSurface(sections, halfWidth) {
  const x = sections.map(section => section.x), z = sections.map(section => section.z);
  const bounds = {
    minX: Math.min(...x) - TERRAIN_MARGIN, maxX: Math.max(...x) + TERRAIN_MARGIN,
    minZ: Math.min(...z) - TERRAIN_MARGIN, maxZ: Math.max(...z) + TERRAIN_MARGIN,
  };
  // Cut one continuous opening across tile boundaries, including the flush surface approaches.
  const edge = (section, offset) => {
    const [x, , z] = pointOffset(section, offset);
    return [x, z];
  };
  return terrainSurfaceFromHole(bounds, [...sections.map(section => edge(section, -halfWidth)),
    ...sections.toReversed().map(section => edge(section, halfWidth))]);
}

function tunnelSections(profile) {
  const points = [...profile.approaches.entry, ...profile.fragments.flatMap(fragment => fragment.points), ...profile.approaches.exit]
    .filter((point, index, all) => index === 0 || point.s > all[index - 1].s);
  return points.map((point, index) => {
    const before = index > 0 ? unitDirection(points[index - 1], point) : unitDirection(point, points[1]);
    const after = index < points.length - 1 ? unitDirection(point, points[index + 1]) : before;
    const length = Math.hypot(before[0] + after[0], before[1] + after[1]);
    const tx = (before[0] + after[0]) / length, tz = (before[1] + after[1]) / length;
    const miter = tx * after[0] + tz * after[1];
    return { ...point, tx, tz, rx: -tz / miter, rz: tx / miter };
  });
}

/** Road, open cuts and enclosed tube. The renderer and Rapier use these same triangles. */
export function createTunnelGeometry(profile, { sections = tunnelSections(profile), includeTerrain = true } = {}) {
  const tunnel = sections.filter(({ s }) => s >= 0 && s <= profile.length);
  const covered = tunnel.filter(({ y }) => y + CLEARANCE + MIN_ROOF_THICKNESS <= 0);
  const half = profile.width / 2;
  const left = -half, right = half;
  const wallPositions = [], wallIndices = [];
  // Face both walls toward the carriageway for the vehicle's inside contacts.
  appendStrip(wallPositions, wallIndices, tunnel,
    row => pointOffset(row, left, 0), row => pointOffset(row, left));
  appendStrip(wallPositions, wallIndices, tunnel,
    row => pointOffset(row, right), row => pointOffset(row, right, 0));
  const portals = [covered[0], covered.at(-1)];
  const portalPositions = portals.flatMap(row => [pointOffset(row, left, row.y + CLEARANCE), pointOffset(row, right, row.y + CLEARANCE),
    pointOffset(row, left, 0), pointOffset(row, right, 0)]).flat();
  const surfaces = [
    strip("road", sections, row => pointOffset(row, left), row => pointOffset(row, right)),
    meshData("walls", wallPositions, wallIndices),
    strip("ceiling", covered, row => pointOffset(row, right, row.y + CLEARANCE), row => pointOffset(row, left, row.y + CLEARANCE)),
    ...(includeTerrain ? [terrainSurface(sections, half)] : []),
    strip("cover", covered, row => pointOffset(row, left, 0), row => pointOffset(row, right, 0)),
    meshData("portals", portalPositions, [0, 1, 2, 1, 3, 2, 4, 6, 5, 5, 6, 7]),
  ];
  return { sections, surfaces, coveredFrom: covered[0].s, coveredTo: covered.at(-1).s, clearance: CLEARANCE };
}

export function nearestTunnelSection(sections, { x, z }) {
  let nearest = null, best = Infinity;
  for (let index = 1; index < sections.length; index++) {
    const a = sections[index - 1], b = sections[index];
    const dx = b.x - a.x, dz = b.z - a.z, length = Math.hypot(dx, dz);
    const tx = dx / length, tz = dz / length;
    const offset = Math.max(0, Math.min(length, (x - a.x) * tx + (z - a.z) * tz));
    const ex = x - (a.x + tx * offset), ez = z - (a.z + tz * offset);
    const distance = ex * ex + ez * ez;
    if (distance >= best) continue;
    best = distance;
    const fraction = offset / length;
    nearest = { s: a.s + (b.s - a.s) * fraction, y: a.y + (b.y - a.y) * fraction, lateral: -ex * tz + ez * tx };
  }
  return nearest;
}

export function tunnelMarkings(profile, sections) {
  const positions = [], indices = [];
  for (const offset of [-profile.width / 2 + .22, profile.width / 2 - .22]) {
    appendStrip(positions, indices, sections,
      row => pointOffset(row, offset - .045, row.y + .014), row => pointOffset(row, offset + .045, row.y + .014));
  }
  for (let lane = 1; lane < profile.lanes; lane++) {
    const offset = profile.width * (lane / profile.lanes - .5);
    for (let start = 0; start + 1 < sections.length; start += 8) {
      const dash = sections.slice(start, start + 4);
      appendStrip(positions, indices, dash,
        row => pointOffset(row, offset - .055, row.y + .014), row => pointOffset(row, offset + .055, row.y + .014));
    }
  }
  return meshData("markings", positions, indices);
}

export { pointOffset, strip as roadStrip };
