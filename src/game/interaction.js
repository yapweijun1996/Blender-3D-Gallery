export const PULL = Object.freeze({ min: 0.05, curve: 1.5, distance: 0.12, strikeSeconds: 0.11 });
export const pullRatio = (start, current, distance) => distance > 0 ? Math.min(1, Math.max(0, (current - start) / distance)) : 0;
// Pointer coordinates are float32 in some browsers; allow less than a thousandth of a pixel at normal controller sizes.
export const meetsPullThreshold = (ratio) => ratio >= PULL.min - 1e-6;
export const shotStrength = (ratio) => Math.max(0, Math.min(1, ratio)) ** PULL.curve;
export const CUE = Object.freeze({ length: 1.47, grabRadius: 0.05 });
// Pointing: the cue aims at the pointer.
export function aimAngle(cue, point, previous) {
  return Math.hypot(point.x - cue.x, point.z - cue.z) > 1e-6 ? Math.atan2(point.z - cue.z, point.x - cue.x) : previous;
}
// Dragging the cue itself: the cue butt follows the pointer, so the shot goes the other way.
export function dragAngle(cue, point, previous) {
  return Math.hypot(cue.x - point.x, cue.z - point.z) > 1e-6 ? Math.atan2(cue.z - point.z, cue.x - point.x) : previous;
}
// True when the point lies on the visible cue shaft behind the white ball.
export function hitsCue(cue, angle, point, radius, pullOffset = 0, grab = CUE.grabRadius) {
  const dx = Math.cos(angle), dz = Math.sin(angle), start = radius + pullOffset;
  const along = -((point.x - cue.x) * dx + (point.z - cue.z) * dz);
  const across = Math.abs((point.x - cue.x) * -dz + (point.z - cue.z) * dx);
  return along >= start - grab && along <= start + CUE.length && across <= grab;
}
export function strikeOffset(ratio, elapsed) {
  return ratio * PULL.distance * Math.max(0, 1 - elapsed / PULL.strikeSeconds);
}
