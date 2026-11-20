import { sampleEdge } from "./traffic.js";

// Street furniture placed along the mapped roads: street lamps on the verge, bus shelters and stop flags at the mapped bus stops.
// Pure placement (no rendering). Poses are { x, z, yaw }, the model's +Z axis pointing towards the road.
const LIGHT_SPACING = 50, LIGHT_CLASSES = new Set(["motorway", "trunk", "primary", "secondary", "tertiary"]);

const towards = (dx, dz) => Math.atan2(dx, dz);

export function lampPlacements(graph) {
  const lamps = [];
  for (const edge of graph.edges.values()) {
    if (!LIGHT_CLASSES.has(edge.class) || edge.length < 60) continue;
    let flip = false;
    for (let s = 24; s <= edge.length - 24; s += LIGHT_SPACING) {
      const at = sampleEdge(edge, s, 1);
      // Left of travel is (dz, -dx); one-way carriageways get lamps on the left verge, two-way roads alternate sides.
      const side = edge.oneway ? 1 : flip ? -1 : 1;
      flip = !flip;
      const offset = edge.width / 2 + 1.1;
      const x = at.x + side * at.dz * offset, z = at.z - side * at.dx * offset;
      // Face back across the road: the opposite of the offset direction.
      lamps.push({ x, z, yaw: towards(-side * at.dz, side * at.dx) });
    }
  }
  return lamps;
}

/** Nearest point on any edge to (x, z): { distance, x, z, dx, dz } with (dx, dz) the road direction there. */
export function nearestRoad(graph, x, z) {
  let best = null;
  for (const edge of graph.edges.values()) {
    for (let i = 1; i < edge.points.length; i++) {
      const a = edge.points[i - 1], b = edge.points[i];
      const sx = b[0] - a[0], sz = b[1] - a[1], span = sx * sx + sz * sz || 1;
      const t = Math.max(0, Math.min(1, ((x - a[0]) * sx + (z - a[1]) * sz) / span));
      const px = a[0] + sx * t, pz = a[1] + sz * t, distance = Math.hypot(x - px, z - pz);
      if (!best || distance < best.distance) { const length = Math.sqrt(span); best = { distance, x: px, z: pz, dx: sx / length, dz: sz / length, edge }; }
    }
  }
  return best;
}

export function busStopPlacements(graph, stops) {
  const shelters = [], flags = [];
  for (const [x, z] of stops) {
    const road = nearestRoad(graph, x, z);
    if (!road || road.distance > 14) continue;
    // Unit vector from the road to the stop, and the pose that faces the road.
    const away = road.distance > 0.01 ? [(x - road.x) / road.distance, (z - road.z) / road.distance] : [road.dz, -road.dx];
    const yaw = towards(-away[0], -away[1]);
    // Keep the shelter clear of the carriageway.
    const clear = Math.max(road.distance, road.edge.width / 2 + 2.2);
    shelters.push({ x: road.x + away[0] * clear, z: road.z + away[1] * clear, yaw });
    flags.push({ x: road.x + away[0] * clear + road.dx * 5, z: road.z + away[1] * clear + road.dz * 5, yaw });
  }
  return { shelters, flags };
}
