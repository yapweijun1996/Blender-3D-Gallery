// Drive-to missions across the map. Targets are world coordinates (x east, z south, metres); a mission is done when the car
// is within `radius` metres of it. Pure helpers, so they can be tested without the renderer.
export const MISSIONS = [
  { id: "artscience", name: "world.place.artscience", x: -27.8, z: -315.1, radius: 45 },
  { id: "esplanade", name: "world.place.esplanade", x: -539.8, z: -702.4, radius: 60 },
  { id: "merlion", name: "world.place.merlion", x: -694.5, z: -381.5, radius: 28 },
  { id: "bayfront", name: "world.place.bayfront", x: -70, z: 24, radius: 25 },
  { id: "gardens", name: "world.place.gardens", x: 270, z: 255, radius: 55 },
  // The long drive: the Woodlands checkpoint and Johor Bahru (the end of the route in models/drive/route-mbs-jb.json), about 30 km north.
  { id: "woodlands", name: "world.place.woodlands", x: -10428, z: -17863, radius: 80, checkpoint: true },
  { id: "johor", name: "world.place.johor", x: -9524, z: -23727, radius: 90 },
];

export const distanceTo = (position, mission) => Math.hypot(mission.x - position.x, mission.z - position.z);
export const arrived = (position, mission) => distanceTo(position, mission) <= mission.radius;

/** Angle of the target relative to the way the car faces, in radians: 0 straight ahead, positive to the left. */
export function relativeBearing(position, heading, mission) {
  const toTarget = Math.atan2(mission.x - position.x, mission.z - position.z);
  let angle = toTarget - heading;
  angle = Math.atan2(Math.sin(angle), Math.cos(angle));
  return angle;
}

/** The mission that follows the given index, skipping the one the car is already standing in. */
export function nextMission(index, position) {
  for (let step = 1; step <= MISSIONS.length; step++) {
    const candidate = (index + step) % MISSIONS.length;
    if (!arrived(position, MISSIONS[candidate])) return candidate;
  }
  return (index + 1) % MISSIONS.length;
}

const PAR_SPEED = 11; // m/s: the average speed that earns the full 1000 points on the road distance
const PAR_SLACK = 10; // seconds for junctions and turns
const BASE = 1000, FLOOR = 100;

/** Seconds a good run takes for a road distance in metres. */
export const parSeconds = roadDistance => roadDistance / PAR_SPEED + PAR_SLACK;

/** Road distance from a place (or the start) to a mission, from the generated table; a straight line times 1.3 when it is not known. */
export function roadDistance(table, fromId, toId, straight) {
  const known = table?.[fromId]?.[toId];
  return Number.isFinite(known) ? known : straight * 1.3;
}

/**
 * Points for one finished mission (`distance` is the road distance): up to 1.5 times the base for beating the par time, never below FLOOR, and the points
 * are cut by up to half for damage taken during the mission (`damage` is the extra damage, 0 to 1).
 */
export function missionScore({ distance, seconds, damage = 0 }) {
  const speed = Math.max(0, Math.min(1.5, parSeconds(distance) / Math.max(1, seconds)));
  const clean = 1 - 0.5 * Math.max(0, Math.min(1, damage));
  return Math.max(FLOOR, Math.round(BASE * speed * clean));
}

/** Best points per mission, kept in the browser. `record` is { best: { [missionId]: points } }; returns { record, improved }. */
export function recordScore(record, id, points) {
  const best = { ...(record?.best ?? {}) };
  const improved = !(best[id] >= points);
  if (improved) best[id] = points;
  return { record: { best }, improved };
}

/** A saved record read back from storage, whatever was stored: only finite, non-negative numbers for known missions survive. */
export function cleanRecord(raw) {
  const best = {};
  for (const mission of MISSIONS) {
    const value = raw?.best?.[mission.id];
    if (Number.isFinite(value) && value >= 0) best[mission.id] = Math.round(value);
  }
  return { best };
}
