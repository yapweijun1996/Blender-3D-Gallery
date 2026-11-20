import { BufferAttribute, BufferGeometry, Color, ShapeUtils, Vector2 } from "three";

// Turns one map tile (models/world/tiles/<x>_<z>.json) into flat-coloured geometry. Coordinates are metres: x east, z south, y up.
export const TILE_SIZE = 250;
const ROAD_Y = 0.03, KERB_Y = 0.12, PATH_Y = 0.05, WATER_Y = 0.02, PARK_Y = 0.01;
const ASPHALT = new Color(0x3b3e43), KERB = new Color(0xb9b9b2), PATH = new Color(0x9c9a90), WATER = new Color(0x2f7391), PARK = new Color(0x5f8f4a);
const WALLS = [0xd9d4c8, 0xc9cfd3, 0xe0d2b8, 0xb9c4c9, 0xcfc5c0, 0xd6dad0].map(hex => new Color(hex));
const ROOFS = [0x8e8f91, 0x7b8085, 0x9a8f86].map(hex => new Color(hex));

/** Collects triangles with a colour each, then builds one non-indexed geometry. */
function createBatch() {
  const positions = [], colors = [];
  return {
    get empty() { return positions.length === 0; },
    triangle(a, b, c, color) {
      positions.push(...a, ...b, ...c);
      for (let i = 0; i < 3; i++) colors.push(color.r, color.g, color.b);
    },
    quad(a, b, c, d, color) { this.triangle(a, b, c, color); this.triangle(a, c, d, color); },
    build() {
      const geometry = new BufferGeometry();
      geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
      geometry.setAttribute("color", new BufferAttribute(new Float32Array(colors), 3));
      geometry.computeVertexNormals();
      geometry.computeBoundingSphere();
      return geometry;
    },
  };
}

const origin = tile => [tile.x * TILE_SIZE, tile.z * TILE_SIZE];
const world = (tile, [x, z]) => [x + tile.x * TILE_SIZE, z + tile.z * TILE_SIZE];

/** A flat strip along a polyline. */
function ribbon(batch, points, width, y, color) {
  if (points.length < 2) return;
  const half = width / 2, left = [], right = [];
  for (let i = 0; i < points.length; i++) {
    const a = points[Math.max(0, i - 1)], b = points[Math.min(points.length - 1, i + 1)];
    let dx = b[0] - a[0], dz = b[1] - a[1];
    const length = Math.hypot(dx, dz) || 1;
    dx /= length; dz /= length;
    left.push([points[i][0] - dz * half, y, points[i][1] + dx * half]);
    right.push([points[i][0] + dz * half, y, points[i][1] - dx * half]);
  }
  for (let i = 0; i < points.length - 1; i++) batch.quad(left[i], right[i], right[i + 1], left[i + 1], color);
}

/** Triangulate a closed ring (the last point repeats the first) lying on the ground. */
function triangulate(ring) {
  const points = ring.slice(0, -1).map(([x, z]) => new Vector2(x, z));
  if (points.length < 3) return { points, triangles: [] };
  return { points, triangles: ShapeUtils.triangulateShape(points, []) };
}

function fillPolygon(batch, ring, y, color) {
  const { points, triangles } = triangulate(ring);
  for (const [a, b, c] of triangles) {
    batch.triangle([points[a].x, y, points[a].y], [points[c].x, y, points[c].y], [points[b].x, y, points[b].y], color);
  }
}

function extrude(batch, ring, height, wall, roof) {
  const { points, triangles } = triangulate(ring);
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    batch.quad([a.x, 0, a.y], [b.x, 0, b.y], [b.x, height, b.y], [a.x, height, a.y], wall);
  }
  for (const [a, b, c] of triangles) {
    batch.triangle([points[a].x, height, points[a].y], [points[c].x, height, points[c].y], [points[b].x, height, points[b].y], roof);
  }
}

const hash = value => { let h = Number(value) % 2147483647 || 1; h = (h * 48271) % 2147483647; return h; };

/** Triangle list of a building for the physics collider: walls and roof, vertices XYZ and indices. */
export function buildingMesh(ring, height) {
  const { points, triangles } = triangulate(ring);
  const vertices = [], indices = [];
  for (const point of points) vertices.push(point.x, 0, point.y);
  for (const point of points) vertices.push(point.x, height, point.y);
  const count = points.length;
  for (let i = 0; i < count; i++) {
    const j = (i + 1) % count;
    indices.push(i, j, count + j, i, count + j, count + i);
  }
  for (const [a, b, c] of triangles) indices.push(count + a, count + b, count + c);
  return { vertices, indices };
}

/**
 * Builds the meshes of one tile. Returns geometries in world coordinates (the tile origin is already added) plus
 * the point features and the buildings, which the page uses for colliders and instanced props.
 */
export function buildTile(tile) {
  const [ox, oz] = origin(tile);
  const shift = points => points.map(([x, z]) => [x + ox, z + oz]);
  const ground = createBatch(), buildings = createBatch();

  for (const park of tile.parks ?? []) fillPolygon(ground, shift(park.geometry), PARK_Y, PARK);
  for (const water of tile.water ?? []) fillPolygon(ground, shift(water.geometry), WATER_Y, WATER);
  for (const path of tile.pedestrian ?? []) ribbon(ground, shift(path.geometry), 2.2, PATH_Y, PATH);
  for (const road of tile.roads ?? []) {
    if (road.tunnel) continue;
    ribbon(ground, shift(road.geometry), road.width ?? Math.max(3.4, (road.lanes ?? 2) * 3.4), ROAD_Y, ASPHALT);
  }
  for (const junction of tile.junctions ?? []) {
    if (junction.geometry?.length > 3) fillPolygon(ground, shift(junction.geometry), ROAD_Y + 0.002, ASPHALT);
  }
  for (const kerb of tile.kerbs ?? []) ribbon(ground, shift(kerb.geometry), 0.3, KERB_Y, KERB);

  const solids = [];
  for (const building of tile.buildings ?? []) {
    const ring = shift(building.geometry);
    if (ring.length < 4) continue;
    const height = Math.max(3, building.height ?? 9);
    const seed = hash(building.id);
    extrude(buildings, ring, height, WALLS[seed % WALLS.length], ROOFS[(seed >> 3) % ROOFS.length]);
    solids.push({ id: building.id, name: building.name, ring, height });
  }
  return {
    ground: ground.empty ? null : ground.build(),
    buildings: buildings.empty ? null : buildings.build(),
    solids,
    trees: shift((tile.trees ?? []).map(tree => tree.point)),
    lamps: shift((tile.streetLamps ?? []).map(lamp => lamp.point)),
    busStops: shift((tile.busStops ?? []).map(stop => stop.point)),
  };
}
