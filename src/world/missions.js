// Drive-to missions across the map. Targets are world coordinates (x east, z south, metres); a mission is done when the car
// is within `radius` metres of it. Pure helpers, so they can be tested without the renderer.
export const MISSIONS = [
  { id: "merlion", name: "world.place.merlion", x: -694.5, z: -381.5, radius: 28 },
  { id: "artscience", name: "world.place.artscience", x: -27.8, z: -315.1, radius: 45 },
  { id: "esplanade", name: "world.place.esplanade", x: -539.8, z: -702.4, radius: 60 },
  { id: "gardens", name: "world.place.gardens", x: 270, z: 255, radius: 55 },
  { id: "bayfront", name: "world.place.bayfront", x: -70, z: 24, radius: 25 },
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

const PAR_SPEED = 11; // m/s: the average speed that earns the full 1000 points on the road distance (straight-line distance times 1.3)
const BASE = 1000, FLOOR = 100;

/** Seconds a good run takes for a straight-line distance in metres. */
export const parSeconds = distance => (distance * 1.3) / PAR_SPEED;

/**
 * Points for one finished mission: up to 1.5 times the base for beating the par time, never below FLOOR, and the points
 * are cut by up to half for damage taken during the mission (`damage` is the extra damage, 0 to 1).
 */
export function missionScore({ distance, seconds, damage = 0 }) {
  const speed = Math.max(0, Math.min(1.5, parSeconds(distance) / Math.max(1, seconds)));
  const clean = 1 - 0.5 * Math.max(0, Math.min(1, damage));
  return Math.max(FLOOR, Math.round(BASE * speed * clean));
}
