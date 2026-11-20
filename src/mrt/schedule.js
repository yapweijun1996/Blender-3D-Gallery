// The train cycle at a platform, as pure functions of time: arrive, stop, doors open, dwell, doors close, depart.
// Positions are metres along the platform (x); the middle of the train stops at x = 0.
export const CYCLE = { arrive: 14, open: 2, dwell: 12, close: 2, depart: 14, gap: 4 };
export const CYCLE_SECONDS = CYCLE.arrive + CYCLE.open + CYCLE.dwell + CYCLE.close + CYCLE.depart + CYCLE.gap;
const RUN = 140; // metres of approach and of departure (out of the station tunnel)

/** { x, speed, doors, phase, remaining } at time t (seconds, any value): doors is 0 (shut) to 1 (open). */
export function trainState(t) {
  const time = ((t % CYCLE_SECONDS) + CYCLE_SECONDS) % CYCLE_SECONDS;
  const stopped = CYCLE.arrive;
  if (time < CYCLE.arrive) {
    // Constant braking from the approach speed down to zero at the stop.
    const v0 = 2 * RUN / CYCLE.arrive, a = v0 / CYCLE.arrive;
    return { x: -RUN + v0 * time - 0.5 * a * time * time, speed: v0 - a * time, doors: 0, phase: "arriving", remaining: CYCLE.arrive - time };
  }
  const afterStop = time - stopped;
  if (afterStop < CYCLE.open) return { x: 0, speed: 0, doors: afterStop / CYCLE.open, phase: "opening", remaining: CYCLE.open - afterStop };
  const afterOpen = afterStop - CYCLE.open;
  if (afterOpen < CYCLE.dwell) return { x: 0, speed: 0, doors: 1, phase: "boarding", remaining: CYCLE.dwell - afterOpen };
  const afterDwell = afterOpen - CYCLE.dwell;
  if (afterDwell < CYCLE.close) return { x: 0, speed: 0, doors: 1 - afterDwell / CYCLE.close, phase: "closing", remaining: CYCLE.close - afterDwell };
  const afterClose = afterDwell - CYCLE.close;
  if (afterClose < CYCLE.depart) {
    const a = 2 * RUN / (CYCLE.depart * CYCLE.depart);
    return { x: 0.5 * a * afterClose * afterClose, speed: a * afterClose, doors: 0, phase: "departing", remaining: CYCLE.depart - afterClose };
  }
  // The train is out of sight; the next one waits in the tunnel before it comes in.
  return { x: RUN * 2, speed: 0, doors: 0, phase: "waiting", remaining: CYCLE_SECONDS - time };
}
