import { AnimationMixer, Group, MathUtils, Vector3 } from 'three';

// Both ends are flat, inside the sampled support interval for the original STEP_00.
const startOnLowerFlat = 0.3;
const endOnUpperFlat = 18.1;
const duration = endOnUpperFlat - startOnLowerFlat;

// Expressed in the native step's coordinates. The added Z offset puts both
// stationary shoe soles on ribs, clear of the next tread throughout the incline.
const stanceOnStep = new Vector3(0, 0.2, 0.24);

export function createEscalatorPassenger({ machine, clips, avatar, avatarClips }) {
  const step = machine.getObjectByName('STEP_00');
  const idle = avatarClips.find((clip) => clip.name === 'idle');
  const stepClips = clips.filter((clip) => clip.name.startsWith('StepCirculation_'));
  const handrailClips = clips.filter((clip) => clip.name.startsWith('HandrailTravel_'));
  if (
    !step?.getObjectByName('STEP_BODY_00') ||
    stepClips.length !== 58 ||
    handrailClips.length !== 2
  ) {
    throw new Error(
      'The passenger ride needs the native escalator, 58 step clips and both handrail clips.',
    );
  }
  if (!idle || !avatar.getObjectByName('LeftFoot') || !avatar.getObjectByName('RightFoot')) {
    throw new Error('The passenger ride needs the original mall visitor and its idle clip.');
  }

  // The native visitor uses rigid named parts. Cloning preserves the caller's
  // cached pose and shares the original geometry and materials.
  const passenger = avatar.clone(true);
  const visual = new Group();
  visual.name = 'Guided escalator passenger';
  visual.rotation.y = Math.PI;
  visual.add(passenger);
  machine.add(visual);

  const machineMixer = new AnimationMixer(machine);
  for (const clip of [...stepClips, ...handrailClips]) machineMixer.clipAction(clip).play();
  const passengerMixer = new AnimationMixer(passenger);
  passengerMixer.clipAction(idle).play();

  let elapsed = 0;
  let playing = false;
  let disposed = false;

  function sample(seconds) {
    elapsed = MathUtils.clamp(seconds, 0, duration);
    machineMixer.setTime(startOnLowerFlat + elapsed);
    passengerMixer.setTime(elapsed);
    visual.position.copy(stanceOnStep);
    step.localToWorld(visual.position);
    machine.worldToLocal(visual.position);
    machine.updateMatrixWorld(true);
  }
  sample(0);

  function seek(seconds) {
    if (disposed) return;
    if (!Number.isFinite(seconds)) throw new RangeError('Ride time must be finite.');
    playing = false;
    sample(seconds);
  }
  function play() {
    if (disposed) return;
    if (elapsed === duration) sample(0);
    playing = true;
  }
  function pause() {
    playing = false;
  }
  function update(deltaSeconds) {
    if (!playing) return;
    if (!Number.isFinite(deltaSeconds) || deltaSeconds < 0) {
      throw new RangeError('Ride update needs a nonnegative finite duration.');
    }
    sample(elapsed + deltaSeconds);
    if (elapsed === duration) pause();
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    pause();
    // Stopping the last action restores each binding's pre-ride transform.
    machineMixer.stopAllAction();
    machineMixer.uncacheRoot(machine);
    passengerMixer.stopAllAction();
    passengerMixer.uncacheRoot(passenger);
    visual.removeFromParent();
    machine.updateMatrixWorld(true);
  }

  return {
    visual,
    duration,
    play,
    pause,
    seek,
    update,
    dispose,
    restart() {
      seek(0);
    },
    get time() {
      return elapsed;
    },
    get playing() {
      return playing;
    },
  };
}
