import { offsetPolyline, samePoint } from '../../src/world/network/geometry.js';
import { between, splitByRing } from '../../src/world/network/polygon.js';

export function passageRibbon(points, halfWidth) {
  const left = offsetPolyline(points, halfWidth), right = offsetPolyline(points, -halfWidth);
  return [...left, ...right.reverse(), left[0]].map(point => point.map(value => Math.round(value * 1000) / 1000));
}

export function clipSurfaceKerb(kerb, ring) {
  const pieces = [];
  let current = null;
  for (let i = 1; i < kerb.geometry.length; i++) {
    const a = kerb.geometry[i - 1], b = kerb.geometry[i];
    const at = t => t === 0 ? a : t === 1 ? b : between(a, b, t);
    for (const { start, end, inside } of splitByRing(a, b, ring)) {
      if (inside) {
        current = null;
      } else if (current) {
        current.push(at(end));
      } else {
        current = [at(start), at(end)];
        pieces.push(current);
      }
    }
  }
  if (pieces.length !== 1 || pieces[0].length !== kerb.geometry.length ||
      pieces[0].some((point, index) => !samePoint(point, kerb.geometry[index]))) kerb.surfaceGeometry = pieces;
}
