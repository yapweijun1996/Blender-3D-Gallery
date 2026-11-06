export const PULL = Object.freeze({ min: 0.05, curve: 1.5, distance: 0.12, strikeSeconds: 0.11 });
export const pullRatio = (start, current, distance) => distance > 0 ? Math.min(1, Math.max(0, (current - start) / distance)) : 0;
export const shotStrength = (ratio) => Math.max(0, Math.min(1, ratio)) ** PULL.curve;
export function aimAngle(cue, point, previous) {
  return Math.hypot(cue.x - point.x, cue.z - point.z) > 1e-6 ? Math.atan2(cue.z - point.z, cue.x - point.x) : previous;
}
export function strikeOffset(ratio, elapsed) {
  return ratio * PULL.distance * Math.max(0, 1 - elapsed / PULL.strikeSeconds);
}
