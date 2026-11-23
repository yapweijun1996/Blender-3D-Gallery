import { Matrix4 } from 'three';
import { createPassengerTimeline, treadStance } from './escalator-passenger.js';
import { createContactRig } from './escalator-contact-rig.js';
import { lowerBoarding, lowerDeckPoleZ, sampleLowerBoarding } from './escalator-lower-boarding.js';
import { sampleUpperExit, upperExit } from './escalator-upper-exit.js';
import { createTerminalWalks } from './escalator-terminal-walks.js';

export function createEscalatorRoute(options, direction = 'up') {
  if (direction !== 'up' && direction !== 'down')
    throw new RangeError('Unknown escalator direction: ' + direction);
  const descending = direction === 'down';
  function createPath({ visual, machine, step }) {
    const rig = createContactRig(visual, machine);
    const stance = treadStance.clone();
    if (descending) {
      // Turning the original avatar moves each sole pole across the root. Keep
      // the poles on the same steel crests, preserving the neighbouring tread clearance.
      stance.z -= 2 * rig.feet[0].poleFromRoot.z;
    }
    const polesOnTread = rig.feet.map((foot) => foot.poleFromRoot.clone().add(stance));
    const walk = createTerminalWalks(rig, machine, lowerDeckPoleZ, lowerBoarding.prepare);
    const stepInMachine = new Matrix4();
    const localStep = { localToWorld: (p) => p.applyMatrix4(stepInMachine) };

    function sample(nativeTime, carry) {
      if (nativeTime < lowerBoarding.prepare) {
        rig.pose(walk.lower.sample(nativeTime));
        return descending ? 'depart' : 'approach';
      }
      if (nativeTime > upperExit.finish) {
        rig.pose(walk.upper.sample(nativeTime));
        return descending ? 'approach' : 'depart';
      }
      if (nativeTime > lowerBoarding.finish && nativeTime < upperExit.prepare) {
        // AnimationMixer may skip rewriting a constant channel. Restore the
        // six native idle joints after an IK sample, including backwards seeks.
        rig.restoreLegs();
        carry(stance);
        return 'ride';
      }
      stepInMachine.copy(machine.matrixWorld).invert().multiply(step.matrixWorld);
      if (nativeTime <= lowerBoarding.finish) {
        rig.pose(sampleLowerBoarding(nativeTime, localStep, polesOnTread));
        return descending ? 'alight' : 'board';
      }
      rig.pose(sampleUpperExit(nativeTime, localStep, polesOnTread));
      return descending ? 'board' : 'alight';
    }
    return {
      start: descending ? walk.upper.end : walk.lower.start,
      end: descending ? walk.lower.start : walk.upper.end,
      sample,
    };
  }
  return createPassengerTimeline(options, createPath, descending ? 0 : Math.PI);
}
