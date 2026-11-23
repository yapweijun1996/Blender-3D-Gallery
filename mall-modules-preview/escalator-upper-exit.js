import { MathUtils, Vector3 } from 'three';

// Continuous with the original stationary-on-STEP_00 ride on the upper flat.
export const upperExit = {
  prepare: 17.37,
  start: 17.55,
  leftLands: 18.24,
  rightLifts: 18.29,
  rightLands: 18.96,
  finish: 19.16,
  landingY: 3,
  // 73 mm beyond the pitched native pose's landing witness. A level shoe has a longer heel projection.
  deckPoleZ: -4.665,
};
const smoother = (n) => n * n * n * (n * (n * 6 - 15) + 10);
function swing(from, to, t, begin, end, clearance) {
  const u = MathUtils.clamp((t - begin) / (end - begin), 0, 1);
  return from
    .clone()
    .lerp(to, smoother(u))
    .add(new Vector3(0, 16 * clearance * u * u * (1 - u) * (1 - u), 0));
}
export function sampleUpperExit(time, step, localPoles) {
  const { start, leftLands, rightLifts, rightLands, landingY, deckPoleZ } = upperExit;
  const [leftOnStep, rightOnStep] = localPoles.map((p) => step.localToWorld(p.clone()));
  const deckLeft = new Vector3(localPoles[0].x, landingY, deckPoleZ);
  const deckRight = new Vector3(localPoles[1].x, landingY, deckPoleZ);
  const left =
    time <= start
      ? leftOnStep
      : time >= leftLands
        ? deckLeft
        : swing(leftOnStep, deckLeft, time, start, leftLands, 0.125);
  const right =
    time <= rightLifts
      ? rightOnStep
      : time >= rightLands
        ? deckRight
        : swing(rightOnStep, deckRight, time, rightLifts, rightLands, 0.12);
  return {
    left,
    right,
    stretch:
      time < start
        ? -1 + 2 * smoother(MathUtils.clamp((time - upperExit.prepare) / (start - upperExit.prepare), 0, 1))
        : time > rightLands
          ? 1 - 2 * smoother(MathUtils.clamp((time - rightLands) / (upperExit.finish - rightLands), 0, 1))
          : 1,
    leftSupport: time <= start ? 'STEP_BODY_00' : time >= leftLands ? 'LANDING_Upper' : null,
    rightSupport: time <= rightLifts ? 'STEP_BODY_00' : time >= rightLands ? 'LANDING_Upper' : null,
  };
}
