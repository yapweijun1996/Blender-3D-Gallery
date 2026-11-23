import { MathUtils, Vector3 } from 'three';

// The flat deck anchor comes from the original rig's lower handoff.
export const lowerDeckPoleZ = 4.974816146366282;
export const lowerBoarding = {
  prepare: -0.8,
  leftLifts: -0.6,
  leftLands: 0.18,
  rightLifts: 0.22,
  rightLands: 1.0,
  finish: 1.2,
};
const smoother = (u) => u * u * u * (10 + u * (-15 + 6 * u));
const phase = (time, start, end) => MathUtils.clamp((time - start) / (end - start), 0, 1);

function boardFoot(time, step, localPole, lifts, lands) {
  const fraction = phase(time, lifts, lands);
  const deck = new Vector3(localPole.x, 0, lowerDeckPoleZ);
  const tread = step.localToWorld(localPole.clone());
  if (fraction === 0) return { target: deck, owner: 'LANDING_Lower' };
  if (fraction === 1) return { target: tread, owner: 'STEP_BODY_00' };
  const target = deck.lerp(tread, smoother(fraction));
  // The receiving tread is still rising below the floor at the start of this swing.
  target.y = 0.11 * 16 * fraction ** 2 * (1 - fraction) ** 2;
  return { target, owner: null };
}

export function sampleLowerBoarding(time, step, localPoles) {
  const { prepare, leftLifts, leftLands, rightLifts, rightLands, finish } = lowerBoarding;
  const left = boardFoot(time, step, localPoles[0], leftLifts, leftLands);
  const right = boardFoot(time, step, localPoles[1], rightLifts, rightLands);
  const stretch =
    -1 + 2 * smoother(phase(time, prepare, leftLifts)) - 2 * smoother(phase(time, rightLands, finish));
  return {
    left: left.target,
    right: right.target,
    stretch,
    leftSupport: left.owner,
    rightSupport: right.owner,
  };
}
