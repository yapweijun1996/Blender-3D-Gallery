// One local demonstration; no route booking, network state, or storage.
export const APPROACH_METRES = 0.8;
export const APPROACH_SECONDS = 1.8;

export function pickupPhase(state, action) {
  if (action === "reset") return "ready";
  if (action === "select" && (state === "ready" || state === "failed")) return "loading";
  if (action === "loaded" && state === "loading") return "approaching";
  if (action === "arrive" && (state === "loading" || state === "approaching")) return "stopped";
  if (action === "fail" && state === "loading") return "failed";
  if (action === "board" && state === "stopped") return "boarded";
  return state;
}

export function pickupOffset(time) {
  const t = Math.max(0, Math.min(1, time / APPROACH_SECONDS));
  const movement = t * t * (3 - 2 * t);
  return APPROACH_METRES * (movement - 1);
}
