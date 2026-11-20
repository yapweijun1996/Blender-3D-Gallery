import { DECK_THICKNESS, fragmentHeights, isBridge } from "./bridges.js";
import { BufferAttribute, BufferGeometry, Color, ShapeUtils, Vector2 } from "three";

// Turns one map tile (models/world/tiles/<x>_<z>.json) into flat-coloured geometry. Coordinates are metres: x east, z south, y up.
export const TILE_SIZE = 250;
const ZEBRA_Y = 0.06, ROAD_Y = 0.03, KERB_Y = 0.12, PATH_Y = 0.05, WATER_Y = 0.02, PARK_Y = 0.01;
const ZEBRA = new Color(0xe9e9e1), ASPHALT = new Color(0x3b3e43), KERB = new Color(0xb9b9b2), PATH = new Color(0x9c9a90), WATER = new Color(0x2f7391), PARK = new Color(0x5f8f4a);
const CONCRETE = new Color(0xa9a9a3), PARAPET = new Color(0xc4c4bd);
const GLASS = [0x7f98a6, 0x6f8ea0, 0x88a0ad, 0x7890a0].map(hex => new Color(hex));
export const TOWER_HEIGHT = 55; // taller buildings get the glass curtain-wall facade
const WALLS = [0xd9d4c8, 0xc9cfd3, 0xe0d2b8, 0xb9c4c9, 0xcfc5c0, 0xd6dad0].map(hex => new Color(hex));
const ROOFS = [0x8e8f91, 0x7b8085, 0x9a8f86].map(hex => new Color(hex));

/** Collects triangles with a colour each, then builds one non-indexed geometry. */
function createBatch({ uv = false } = {}) {
  const positions = [], colors = [], uvs = [];
  return {
    get empty() { return positions.length === 0; },
    /** Optional texture coordinates [u, v] per corner (only kept when the batch was made with uv: true). */
    triangle(a, b, c, color, uva = [0, 0], uvb = [0, 0], uvc = [0, 0]) {
      positions.push(...a, ...b, ...c);
      for (let i = 0; i < 3; i++) colors.push(color.r, color.g, color.b);
      if (uv) uvs.push(...uva, ...uvb, ...uvc);
    },
    quad(a, b, c, d, color, uva, uvb, uvc, uvd) { this.triangle(a, b, c, color, uva, uvb, uvc); this.triangle(a, c, d, color, uva, uvc, uvd); },
    build() {
      const geometry = new BufferGeometry();
      geometry.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
      geometry.setAttribute("color", new BufferAttribute(new Float32Array(colors), 3));
      if (uv) geometry.setAttribute("uv", new BufferAttribute(new Float32Array(uvs), 2));
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

/**
 * A raised road deck along a polyline: asphalt top, concrete slab and sides, parapets and columns to the ground.
 * Returns triangles (vertices XYZ and indices) of the drivable top and the parapet walls for the physics.
 */
function deck(batch, points, heights, width, solids) {
  if (points.length < 2) return;
  const half = width / 2, left = [], right = [];
  for (let i = 0; i < points.length; i++) {
    const a = points[Math.max(0, i - 1)], b = points[Math.min(points.length - 1, i + 1)];
    let dx = b[0] - a[0], dz = b[1] - a[1];
    const length = Math.hypot(dx, dz) || 1;
    dx /= length; dz /= length;
    left.push([points[i][0] - dz * half, points[i][1] + dx * half]);
    right.push([points[i][0] + dz * half, points[i][1] - dx * half]);
  }
  const at = (point, y) => [point[0], y, point[1]];
  for (let i = 0; i < points.length - 1; i++) {
    const h0 = heights[i], h1 = heights[i + 1], u0 = h0 - DECK_THICKNESS, u1 = h1 - DECK_THICKNESS;
    batch.quad(at(left[i], h0 + ROAD_Y), at(right[i], h0 + ROAD_Y), at(right[i + 1], h1 + ROAD_Y), at(left[i + 1], h1 + ROAD_Y), ASPHALT);
    batch.quad(at(left[i], u0), at(left[i + 1], u1), at(right[i + 1], u1), at(right[i], u0), CONCRETE);
    batch.quad(at(left[i], u0), at(left[i + 1], u1), at(left[i + 1], h1), at(left[i], h0), CONCRETE);
    batch.quad(at(right[i], u0), at(right[i + 1], u1), at(right[i + 1], h1), at(right[i], h0), CONCRETE);
    // Parapets 0.9 m high on both edges.
    for (const side of [left, right]) batch.quad(at(side[i], h0), at(side[i + 1], h1), at(side[i + 1], h1 + 0.9), at(side[i], h0 + 0.9), PARAPET);
  }
  // Columns every 30 m where the deck is well above the ground.
  let sinceColumn = 28;
  for (let i = 0; i < points.length; i++) {
    if (i) sinceColumn += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
    if (sinceColumn < 30 || heights[i] < 3) continue;
    sinceColumn = 0;
    const [cx, cz] = points[i], size = 0.9, top = heights[i] - DECK_THICKNESS;
    const corners = [[cx - size, cz - size], [cx + size, cz - size], [cx + size, cz + size], [cx - size, cz + size]];
    for (let k = 0; k < 4; k++) batch.quad(at(corners[k], 0), at(corners[(k + 1) % 4], 0), at(corners[(k + 1) % 4], top), at(corners[k], top), CONCRETE);
  }
  // Physics: the drivable top and the parapet walls.
  const vertices = [], indices = [];
  const push = point => { vertices.push(...point); return vertices.length / 3 - 1; };
  for (let i = 0; i < points.length - 1; i++) {
    const h0 = heights[i] + ROAD_Y, h1 = heights[i + 1] + ROAD_Y;
    const a = push(at(left[i], h0)), b = push(at(right[i], h0)), c = push(at(right[i + 1], h1)), d = push(at(left[i + 1], h1));
    indices.push(a, b, c, a, c, d);
    for (const side of [left, right]) {
      const w0 = push(at(side[i], h0)), w1 = push(at(side[i + 1], h1)), w2 = push(at(side[i + 1], h1 + 0.9)), w3 = push(at(side[i], h0 + 0.9));
      indices.push(w0, w1, w2, w0, w2, w3);
    }
  }
  solids.push({ vertices, indices });
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

// Facade texture coordinates: one window bay is BAY metres wide and one storey FLOOR metres high; u runs along the wall, v up it.
// The roof samples a plain corner of the facade texture (see facadeTexture in page.js).
export const BAY = 3.6, FLOOR = 3.2;
const PLAIN = [0.03, 0.03];

function extrude(batch, ring, height, wall, roof, { bay = BAY, floor = FLOOR } = {}) {
  const { points, triangles } = triangulate(ring);
  const floors = Math.max(1, Math.round(height / floor));
  let along = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    const length = Math.hypot(b.x - a.x, b.y - a.y), u0 = along / bay, u1 = (along + length) / bay;
    batch.quad([a.x, 0, a.y], [b.x, 0, b.y], [b.x, height, b.y], [a.x, height, a.y], wall, [u0, 0], [u1, 0], [u1, floors], [u0, floors]);
    along += length;
  }
  for (const [a, b, c] of triangles) {
    batch.triangle([points[a].x, height, points[a].y], [points[c].x, height, points[c].y], [points[b].x, height, points[b].y], roof, PLAIN, PLAIN, PLAIN);
  }
}

const hash = value => { let h = Number(value) % 2147483647 || 1; h = (h * 48271) % 2147483647; return h; };

/** White bars across the carriageway at a mapped crossing: the bars run along the road, repeated across it. */
function zebra(batch, tile, point, ox, oz) {
  let best = null;
  for (const road of tile.roads ?? []) {
    if (road.tunnel || (road.width ?? 0) < 5) continue;
    for (let i = 1; i < road.geometry.length; i++) {
      const a = road.geometry[i - 1], b = road.geometry[i];
      const sx = b[0] - a[0], sz = b[1] - a[1], span = sx * sx + sz * sz || 1;
      const t = Math.max(0, Math.min(1, ((point[0] - a[0]) * sx + (point[1] - a[1]) * sz) / span));
      const px = a[0] + sx * t, pz = a[1] + sz * t, distance = Math.hypot(point[0] - px, point[1] - pz);
      if (distance < 4 && (!best || distance < best.distance)) { const length = Math.sqrt(span); best = { distance, x: px, z: pz, tx: sx / length, tz: sz / length, width: road.width }; }
    }
  }
  if (!best) return;
  // Along the road: (tx, tz), across it: (nx, nz). Bars 3 m long, 0.5 m wide, every 1 m across the carriageway.
  const nx = -best.tz, nz = best.tx, half = best.width / 2;
  for (let across = -half + 0.7; across <= half - 0.7; across += 1) {
    const cx = best.x + ox + nx * across, cz = best.z + oz + nz * across;
    const corner = (along, side) => [cx + best.tx * along + nx * side, ZEBRA_Y, cz + best.tz * along + nz * side];
    batch.quad(corner(-1.5, -0.25), corner(1.5, -0.25), corner(1.5, 0.25), corner(-1.5, 0.25), ZEBRA);
  }
}

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
export function buildTile(tile, { hide = () => false } = {}) {
  const [ox, oz] = origin(tile);
  const shift = points => points.map(([x, z]) => [x + ox, z + oz]);
  const ground = createBatch(), buildings = createBatch({ uv: true }), towers = createBatch({ uv: true });

  for (const park of tile.parks ?? []) fillPolygon(ground, shift(park.geometry), PARK_Y, PARK);
  for (const water of tile.water ?? []) fillPolygon(ground, shift(water.geometry), WATER_Y, WATER);
  for (const path of tile.pedestrian ?? []) ribbon(ground, shift(path.geometry), 2.2, PATH_Y, PATH);
  const bridgeSolids = [];
  for (const road of tile.roads ?? []) {
    if (road.tunnel) continue;
    if (isBridge(road)) { deck(ground, shift(road.geometry), fragmentHeights(road), road.width ?? Math.max(3.4, (road.lanes ?? 2) * 3.4), bridgeSolids); continue; }
    ribbon(ground, shift(road.geometry), road.width ?? Math.max(3.4, (road.lanes ?? 2) * 3.4), ROAD_Y, ASPHALT);
  }
  for (const junction of tile.junctions ?? []) {
    if (junction.geometry?.length > 3) fillPolygon(ground, shift(junction.geometry), ROAD_Y + 0.002, ASPHALT);
  }
  for (const kerb of tile.kerbs ?? []) if (!(kerb.layer > 0)) ribbon(ground, shift(kerb.geometry), 0.3, KERB_Y, KERB);

  for (const crossing of tile.crossings ?? []) {
    // A crossing is a point marker or a walkable line; a line is marked at its middle.
    const line = crossing.geometry;
    const point = crossing.point ?? (line?.length ? line[line.length >> 1] : null);
    if (point) zebra(ground, tile, point, ox, oz);
  }

  const solids = [];
  for (const building of tile.buildings ?? []) {
    const ring = shift(building.geometry);
    if (ring.length < 4) continue;
    const height = Math.max(3, building.height ?? 9);
    const seed = hash(building.id);
    if (!hide(building.name)) {
      if (height >= TOWER_HEIGHT) extrude(towers, ring, height, GLASS[seed % GLASS.length], ROOFS[(seed >> 3) % ROOFS.length], { bay: 2.4, floor: 4 });
      else extrude(buildings, ring, height, WALLS[seed % WALLS.length], ROOFS[(seed >> 3) % ROOFS.length]);
    }
    solids.push({ id: building.id, name: building.name, ring, height });
  }
  return {
    ground: ground.empty ? null : ground.build(),
    buildings: buildings.empty ? null : buildings.build(),
    towers: towers.empty ? null : towers.build(),
    solids,
    bridgeSolids,
    trees: shift((tile.trees ?? []).map(tree => tree.point)),
    lamps: shift((tile.streetLamps ?? []).map(lamp => lamp.point)),
    busStops: shift((tile.busStops ?? []).map(stop => stop.point)),
    entrances: (tile.subwayEntrances ?? []).map(entrance => ({ name: entrance.name ?? "", x: entrance.point[0] + ox, z: entrance.point[1] + oz })),
  };
}
