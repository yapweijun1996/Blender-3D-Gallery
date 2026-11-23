import { createBuildingPassageMesh } from "./building-passage.js";
import { pavementPanel } from "./pavement.js";
import { DECK_THICKNESS, bridgeRampSections, fragmentHeights, isBridge } from "./bridges.js";
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
function ribbon(batch, points, width, y, color, panels, walkFrom = 0, supportY = 0) {
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
  for (let i = 0; i < points.length - 1; i++) {
    const a = left[i], b = right[i], c = right[i + 1], d = left[i + 1];
    batch.quad(a, b, c, d, color);
    if (panels && i >= walkFrom) {
      const [pa, pb, pc, pd] = [a, b, c, d].map(([x, , z]) => [x, supportY, z]);
      panels.push(pavementPanel(pa, pb, pc), pavementPanel(pa, pc, pd));
    }
  }
}

/**
 * A raised road deck along a polyline: asphalt top, concrete slab and sides, parapets and columns to the ground.
 * Returns triangles (vertices XYZ and indices) of the drivable top and the parapet walls for the physics.
 */
function deck(batch, points, road, width, solids) {
  if (points.length < 2) return;
  const half = width / 2, sourceLeft = [], sourceRight = [];
  const sourceHeights = fragmentHeights(road);
  for (let i = 0; i < points.length; i++) {
    const a = points[Math.max(0, i - 1)], b = points[Math.min(points.length - 1, i + 1)];
    let dx = b[0] - a[0], dz = b[1] - a[1];
    const length = Math.hypot(dx, dz) || 1;
    dx /= length; dz /= length;
    sourceLeft.push([points[i][0] - dz * half, points[i][1] + dx * half]);
    sourceRight.push([points[i][0] + dz * half, points[i][1] - dx * half]);
  }
  // Interpolate the original strip borders. Recomputing tangents on added points would move bends and tile joins.
  const left = [], right = [], heights = [];
  const sections = bridgeRampSections(road);
  let next = sections.next();
  const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t];
  for (let i = 0; i < points.length; i++) {
    left.push(sourceLeft[i]); right.push(sourceRight[i]); heights.push(sourceHeights[i]);
    while (!next.done && next.value.segment === i) {
      const { fraction, height } = next.value;
      left.push(mix(sourceLeft[i], sourceLeft[i + 1], fraction));
      right.push(mix(sourceRight[i], sourceRight[i + 1], fraction));
      heights.push(height);
      next = sections.next();
    }
  }
  const at = (point, y) => [point[0], y, point[1]];
  const vertices = [], indices = [];
  function colliderQuad(a, b, c, d) {
    if (!solids) return;
    const first = vertices.length / 3;
    vertices.push(...a, ...b, ...c, ...d);
    indices.push(first, first + 1, first + 2, first, first + 2, first + 3);
  }
  for (let i = 0; i < heights.length - 1; i++) {
    const l0 = left[i], r0 = right[i], l1 = left[i + 1], r1 = right[i + 1];
    const h0 = heights[i], h1 = heights[i + 1], u0 = h0 - DECK_THICKNESS, u1 = h1 - DECK_THICKNESS;
    function surface(a, b, c, d) {
      const top = [at(a, h0 + ROAD_Y), at(b, h0 + ROAD_Y), at(c, h1 + ROAD_Y), at(d, h1 + ROAD_Y)];
      batch?.quad(...top, ASPHALT);
      colliderQuad(...top);
      batch?.quad(at(a, u0), at(d, u1), at(c, u1), at(b, u0), CONCRETE);
    }
    // A twisted quad's centreline changes slope only where it crosses the l0–r1 diagonal.
    // The intersection's fractions along that diagonal and the centreline differ by turn / twiceArea.
    const vx = r0[0] - l0[0], vz = r0[1] - l0[1], wx = r1[0] - l1[0], wz = r1[1] - l1[1];
    const dx = (l1[0] - l0[0] + r1[0] - r0[0]) / 2, dz = (l1[1] - l0[1] + r1[1] - r0[1]) / 2;
    const turn = vx * wz - vz * wx, twiceArea = 2 * (dx * (vz + wz) - dz * (vx + wx));
    const maxCentreError = 0.0005; // metres of additional height error from the panel diagonal
    if (Math.abs((h1 - h0) * turn) > maxCentreError * Math.abs(twiceArea)) {
      // Keep the centre inside the faces rather than on a longitudinal collider seam.
      const halfBandMetres = 0.025;
      const band = Math.min(halfBandMetres / width, 0.25);
      const a0 = mix(l0, r0, 0.5 - band), a1 = mix(l1, r1, 0.5 - band);
      const b0 = mix(l0, r0, 0.5 + band), b1 = mix(l1, r1, 0.5 + band);
      surface(l0, a0, a1, l1);
      surface(a0, b0, b1, a1);
      surface(b0, r0, r1, b1);
    } else {
      surface(l0, r0, r1, l1);
    }
    for (const [a, b] of [[l0, l1], [r0, r1]]) {
      batch?.quad(at(a, u0), at(b, u1), at(b, h1), at(a, h0), CONCRETE);
      batch?.quad(at(a, h0), at(b, h1), at(b, h1 + 0.9), at(a, h0 + 0.9), PARAPET);
      colliderQuad(at(a, h0 + ROAD_Y), at(b, h1 + ROAD_Y), at(b, h1 + ROAD_Y + 0.9), at(a, h0 + ROAD_Y + 0.9));
    }
  }
  if (solids) solids.push({ vertices, indices });
  if (batch) {
    // Columns every 30 m where the deck is well above the ground.
    let sinceColumn = 28;
    for (let i = 0; i < points.length; i++) {
      if (i) sinceColumn += Math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1]);
      if (sinceColumn < 30 || sourceHeights[i] < 3) continue;
      sinceColumn = 0;
      const [cx, cz] = points[i], size = 0.9, top = sourceHeights[i] - DECK_THICKNESS;
      const corners = [[cx - size, cz - size], [cx + size, cz - size], [cx + size, cz + size], [cx - size, cz + size]];
      for (let k = 0; k < 4; k++) batch.quad(at(corners[k], 0), at(corners[(k + 1) % 4], 0), at(corners[(k + 1) % 4], top), at(corners[k], top), CONCRETE);
    }
  }
}

/** Triangulate a closed ring (the last point repeats the first) lying on the ground. */
function triangulate(ring, clockwise = false) {
  const points = ring.slice(0, -1).map(([x, z]) => new Vector2(x, z));
  if (points.length < 3) return { points, triangles: [] };
  if (clockwise && !ShapeUtils.isClockWise(points)) points.reverse();
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

function extrude(batch, ring, height, wall, roof, { bay = BAY, floor = FLOOR, base = 0 } = {}) {
  const { points, triangles } = triangulate(ring, base > 0);
  const top = base + height;
  const floors = Math.max(1, Math.round(height / floor));
  let along = 0;
  for (let i = 0; i < points.length; i++) {
    const a = points[i], b = points[(i + 1) % points.length];
    const length = Math.hypot(b.x - a.x, b.y - a.y), u0 = along / bay, u1 = (along + length) / bay;
    batch.quad([a.x, base, a.y], [b.x, base, b.y], [b.x, top, b.y], [a.x, top, a.y], wall, [u0, 0], [u1, 0], [u1, floors], [u0, floors]);
    along += length;
  }
  for (const [a, b, c] of triangles) {
    batch.triangle([points[a].x, top, points[a].y], [points[c].x, top, points[c].y], [points[b].x, top, points[b].y], roof, PLAIN, PLAIN, PLAIN);
    if (base > 0) {
      batch.triangle([points[a].x, base, points[a].y], [points[b].x, base, points[b].y], [points[c].x, base, points[c].y], roof, PLAIN, PLAIN, PLAIN);
    }
  }
}

function drawBuildingPassage(batch, mesh, wall, roof) {
  const { vertices, indices, facadeUV } = mesh;
  for (let i = 0; i < indices.length; i += 3) {
    const [a, b, c] = [indices[i], indices[i + 1], indices[i + 2]].map(index => vertices.subarray(3 * index, 3 * index + 3));
    if (2 * i < facadeUV.length) {
      batch.triangle(a, b, c, wall, facadeUV.slice(2 * i, 2 * i + 2),
        facadeUV.slice(2 * i + 2, 2 * i + 4), facadeUV.slice(2 * i + 4, 2 * i + 6));
    } else batch.triangle(a, b, c, roof, PLAIN, PLAIN, PLAIN);
  }
}

const hash = value => { let h = Number(value) % 2147483647 || 1; h = (h * 48271) % 2147483647; return h; };

/** White bars across the carriageway at a mapped crossing: the bars run along the road, repeated across it. */
function zebra(batch, roads, point, ox, oz, roadId) {
  let best = null;
  for (const road of roads ?? []) {
    if (road.tunnel || (road.width ?? 0) < 5 || (roadId != null && road.id !== roadId)) continue;
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

/** Physics walls and roof, with an underside for buildings raised above ground. */
export function buildingMesh(ring, height, base = 0) {
  const { points, triangles } = triangulate(ring, base > 0);
  const vertices = [], indices = [];
  for (const point of points) vertices.push(point.x, base, point.y);
  for (const point of points) vertices.push(point.x, base + height, point.y);
  const count = points.length;
  for (let i = 0; i < count; i++) {
    const j = (i + 1) % count;
    indices.push(i, j, count + j, i, count + j, count + i);
  }
  for (const [a, b, c] of triangles) {
    if (base > 0) indices.push(count + a, count + c, count + b, a, b, c);
    else indices.push(count + a, count + b, count + c);
  }
  return { vertices, indices };
}

/**
 * Builds the meshes of one tile. Returns geometries in world coordinates (the tile origin is already added) plus
 * the point features and the buildings, which the page uses for colliders and instanced props.
 * An optional buildingBase callback declares an elevated underside in world metres.
 * Paint masks suppress ribbons by ID while keeping their data available for crossings.
 * Visual-only roads and kerbs contribute geometry without becoming crossing references or collision solids.
 */
export function buildTile(tile, { hide = () => false, buildingBase, paint, visualOnly } = {}) {
  const [ox, oz] = origin(tile);
  const shift = points => points.map(([x, z]) => [x + ox, z + oz]);
  const ground = createBatch(), buildings = createBatch({ uv: true }), towers = createBatch({ uv: true });

  for (const park of tile.parks ?? []) fillPolygon(ground, shift(park.geometry), PARK_Y, PARK);
  for (const water of tile.water ?? []) fillPolygon(ground, shift(water.geometry), WATER_Y, WATER);
  const walkwaySolids = [];
  const maskedPaths = paint?.pedestrian && new Set(paint.pedestrian);
  for (const path of tile.pedestrian ?? []) {
    if (maskedPaths?.has(path.id)) continue;
    if (path.indoorLevel > 0) {
      if (Number.isFinite(path.floorHeight) && path.floorHeight > 0) {
        ribbon(ground, shift(path.deckGeometry ?? path.geometry), 2.2, path.floorHeight, PATH, walkwaySolids, 0, path.floorHeight);
      }
      continue;
    }
    const alongside = path.besideCarriageway;
    ribbon(ground, shift(path.geometry), 2.2, alongside ? ROAD_Y - .01 : PATH_Y, PATH,
      alongside ? walkwaySolids : undefined, path.walkFrom);
  }

  const bridgeSolids = [];
  const maskedRoads = new Set(paint?.roads);
  const maskedKerbs = new Set(paint?.kerbs);
  for (const surface of tile.roadSurfaces ?? []) {
    fillPolygon(ground, shift(surface.geometry), ROAD_Y, ASPHALT);
    for (const id of surface.edges) maskedRoads.add(id);
    for (const id of surface.subsurfaceKerbs ?? []) maskedKerbs.add(id);
  }
  function drawRoads(roads, solids) {
    for (const road of roads ?? []) {
      if (road.tunnel) continue;
      const visible = !maskedRoads.has(road.id);
      const width = road.width ?? Math.max(3.4, (road.lanes ?? 2) * 3.4);
      if (isBridge(road)) deck(visible ? ground : null, shift(road.geometry), road, width, solids);
      else if (visible) ribbon(ground, shift(road.geometry), width, ROAD_Y, ASPHALT);
    }
  }
  drawRoads(tile.roads, bridgeSolids);
  drawRoads(visualOnly?.roads);
  for (const junction of tile.junctions ?? []) {
    if (junction.geometry?.length > 3) fillPolygon(ground, shift(junction.geometry), ROAD_Y + 0.002, ASPHALT);
  }

  function drawKerbs(kerbs) {
    for (const kerb of kerbs ?? []) {
      if (kerb.layer > 0 || maskedKerbs.has(kerb.road)) continue;
      for (const line of kerb.surfaceGeometry ?? [kerb.geometry]) ribbon(ground, shift(line), 0.3, KERB_Y, KERB);
    }
  }
  drawKerbs(tile.kerbs);
  drawKerbs(visualOnly?.kerbs);

  for (const crossing of tile.crossings ?? []) {
    if (crossing.markings === false) continue;
    // A crossing is a point marker or a walkable line; a line is marked at its middle.
    const line = crossing.geometry;
    const point = crossing.point ?? (line?.length ? line[line.length >> 1] : null);
    if (point) zebra(ground, tile.roads, point, ox, oz, crossing.roadId);
  }

  const solids = [];
  for (const building of tile.buildings ?? []) {
    const ring = shift(building.geometry);
    if (ring.length < 4) continue;
    const mappedBase = building.minHeight;
    const base = buildingBase?.(building) ?? mappedBase ?? 0;
    const height = mappedBase == null ? Math.max(3, building.height ?? 9) : building.height - base;
    if (!(height > 0) || !Number.isFinite(height)) throw new RangeError(`Invalid height for building ${building.id}`);
    if (!Number.isFinite(base) || base < 0) throw new RangeError(`Invalid base height for building ${building.id}`);
    const seed = hash(building.id);
    const solid = { id: building.id, name: building.name, ring, height };
    if (base > 0) solid.base = base;
    const tower = height >= TOWER_HEIGHT;
    if (building.passages?.length) {
      if (base !== 0 || building.passages.length !== 1) throw new RangeError("Expected one ground-level building passage");
      const passage = building.passages[0];
      solid.mesh = createBuildingPassageMesh(ring, height, { ...passage, geometry: shift(passage.geometry) },
        tower ? { bay: 2.4, storey: 4 } : { bay: BAY, storey: FLOOR });
    }
    if (!hide(building.name)) {
      const roof = ROOFS[(seed >> 3) % ROOFS.length];
      if (solid.mesh) {
        const walls = tower ? GLASS : WALLS;
        drawBuildingPassage(tower ? towers : buildings, solid.mesh, walls[seed % walls.length], roof);
      } else if (tower) extrude(towers, ring, height, GLASS[seed % GLASS.length], roof, { bay: 2.4, floor: 4, base });
      else extrude(buildings, ring, height, WALLS[seed % WALLS.length], roof, { base });
    }
    solids.push(solid);
  }
  return {
    ground: ground.empty ? null : ground.build(),
    buildings: buildings.empty ? null : buildings.build(),
    towers: towers.empty ? null : towers.build(),
    solids,
    bridgeSolids, walkwaySolids,
    trees: shift((tile.trees ?? []).map(tree => tree.point)),
    lamps: shift((tile.streetLamps ?? []).map(lamp => lamp.point)),
    busStops: shift((tile.busStops ?? []).map(stop => stop.point)),
    entrances: (tile.subwayEntrances ?? []).map(entrance => ({ name: entrance.name ?? "", x: entrance.point[0] + ox, z: entrance.point[1] + oz })),
  };
}
