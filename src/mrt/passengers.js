import { CYCLE, CYCLE_SECONDS } from "./schedule.js";

// Passengers at the platform, a pure function of the clock. At each of three doorways one person waits and boards while another
// gets off; the two swap roles every cycle. Positions are metres: x along the platform, z across it (the track is at +z).
export const DOORWAYS = [-3.4, 3.4, 17.3];
const SPEED = 1.4;
const WAIT_Z = 1.2, THRESHOLD_Z = 3.3, INSIDE_Z = 3.6, EXIT_Z = 0.6;
const BOARD_AT = CYCLE.arrive + CYCLE.open;               // doors fully open
const WALK_OFF_UNTIL = BOARD_AT + 10;                     // an alighter walks along the platform until this moment, then is gone

/** Who is waiting and who is getting off in the given cycle: person i is a boarder when (i + cycle) is even. */
export const roleOf = (index, cycle) => ((index % 2) + cycle) % 2 === 0 ? "boarding" : "alighting";

/** { visible, x, z, heading, clip } for person `index` at clock time `clock`. */
export function passengerPose(index, clock) {
  const cycle = Math.floor(clock / CYCLE_SECONDS), local = clock - cycle * CYCLE_SECONDS;
  const door = DOORWAYS[index >> 1], role = roleOf(index, cycle);
  if (role === "boarding") {
    const x = door - 0.5;
    if (local < BOARD_AT + 0.3) return { visible: true, x, z: WAIT_Z, heading: 0, clip: "idle" };
    const walked = (local - BOARD_AT - 0.3) * SPEED;
    if (WAIT_Z + walked >= THRESHOLD_Z) return { visible: false, x, z: THRESHOLD_Z, heading: 0, clip: "idle" };
    return { visible: true, x, z: WAIT_Z + walked, heading: 0, clip: "walk" };
  }
  const x = door + 0.5;
  if (local < BOARD_AT || local > WALK_OFF_UNTIL) return { visible: false, x, z: INSIDE_Z, heading: Math.PI, clip: "idle" };
  const walked = (local - BOARD_AT) * SPEED, toPlatform = INSIDE_Z - EXIT_Z;
  if (walked < toPlatform) return { visible: true, x, z: INSIDE_Z - walked, heading: Math.PI, clip: "walk" };
  // On the platform: turn towards the fare gates (-x) and walk.
  return { visible: true, x: x - (walked - toPlatform), z: EXIT_Z, heading: -Math.PI / 2, clip: "walk" };
}
