// The passport stamp game at the checkpoint: show the passport, then stop a marker that sweeps along a bar inside the green zone.
export const STAMP_ZONE = [0.4, 0.62];
const SWEEP_SPEED = 0.75; // bar lengths per second

export function createStamp() {
  const state = { phase: "show", value: 0, direction: 1 };
  return {
    state,
    /** Advance the sweeping marker (only while stamping). */
    update(dt) {
      if (state.phase !== "stamp") return;
      state.value += state.direction * dt * SWEEP_SPEED;
      if (state.value > 1) { state.value = 1; state.direction = -1; }
      if (state.value < 0) { state.value = 0; state.direction = 1; }
    },
    /** The one button: "show" passport, then "stamp" (hit or miss), a hit ends the game as "done". */
    press() {
      if (state.phase === "show") { state.phase = "stamp"; state.value = 0; state.direction = 1; return "shown"; }
      if (state.phase === "stamp") {
        if (state.value >= STAMP_ZONE[0] && state.value <= STAMP_ZONE[1]) { state.phase = "done"; return "hit"; }
        return "miss";
      }
      return "ignored";
    },
  };
}
