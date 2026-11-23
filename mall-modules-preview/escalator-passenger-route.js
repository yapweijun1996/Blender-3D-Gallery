import { Matrix4 } from 'three';
import { createPassengerTimeline, treadStance } from './escalator-passenger.js';
import { createContactRig } from './escalator-contact-rig.js';
import { lowerBoarding, lowerDeckPoleZ, sampleLowerBoarding } from './escalator-lower-boarding.js';
import { sampleUpperExit, upperExit } from './escalator-upper-exit.js';
import { createTerminalWalks } from './escalator-terminal-walks.js';

export function createEscalatorRoute(options) {
  return createPassengerTimeline(options, ({ visual, machine, step }) => {
    const rig = createContactRig(visual, machine);
    const polesOnTread = rig.feet.map((foot) => foot.poleFromRoot.clone().add(treadStance));
    const walk = createTerminalWalks(rig, machine, lowerDeckPoleZ, lowerBoarding.prepare);
    const stepInMachine = new Matrix4();
    const localStep = { localToWorld: (p) => p.applyMatrix4(stepInMachine) };

    function sample(nativeTime, carry) {
      if (nativeTime < lowerBoarding.prepare) {
        rig.pose(walk.lower.sample(nativeTime));
        return 'approach';
      }
      if (nativeTime > upperExit.finish) {
        rig.pose(walk.upper.sample(nativeTime));
        return 'depart';
      }
      if (nativeTime > lowerBoarding.finish && nativeTime < upperExit.prepare) {
        // AnimationMixer may skip rewriting a constant channel. Restore the
        // six native idle joints after an IK sample, including backwards seeks.
        rig.restoreLegs();
        carry();
        return 'ride';
      }
      stepInMachine.copy(machine.matrixWorld).invert().multiply(step.matrixWorld);
      if (nativeTime <= lowerBoarding.finish) {
        rig.pose(sampleLowerBoarding(nativeTime, localStep, polesOnTread));
        return 'board';
      }
      rig.pose(sampleUpperExit(nativeTime, localStep, polesOnTread));
      return 'alight';
    }
    return { start: walk.lower.start, end: walk.upper.end, sample };
  });
}
