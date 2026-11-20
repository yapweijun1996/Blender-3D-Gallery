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
