import { AnimationMixer, Group, MathUtils, Vector3 } from 'three';

// The original visitor's measured stance on STEP_00 puts each sole pole over a rib.
export const treadStance = Object.freeze(new Vector3(0, 0.2, 0.24));

function validateSources(machine, clips, avatar, avatarClips) {
  const step = machine.getObjectByName('STEP_00');
  const idle = avatarClips.find((clip) => clip.name === 'idle');
  const steps = clips.filter((clip) => clip.name.startsWith('StepCirculation_'));
  const handrails = clips.filter((clip) => clip.name.startsWith('HandrailTravel_'));
  if (!step?.getObjectByName('STEP_BODY_00') || steps.length !== 58 || handrails.length !== 2)
    throw new Error('The passenger ride needs the native escalator, 58 step clips and both handrail clips.');
  if (!idle || !avatar.getObjectByName('LeftFoot') || !avatar.getObjectByName('RightFoot'))
    throw new Error('The passenger ride needs the original mall visitor and its idle clip.');
  return { step, idle, nativeClips: [...steps, ...handrails] };
}

export function createPassengerTimeline({ machine, clips, avatar, avatarClips }, createPath) {
  const { step, idle, nativeClips } = validateSources(machine, clips, avatar, avatarClips);
  const visual = new Group();
  visual.name = 'Guided escalator passenger';
  visual.rotation.y = Math.PI;
  const passenger = avatar.clone(true);
  visual.add(passenger);
  machine.add(visual);

  const machineMixer = new AnimationMixer(machine);
  const actions = nativeClips.map((clip) => machineMixer.clipAction(clip).play());
  const visitorMixer = new AnimationMixer(passenger);
  visitorMixer.clipAction(idle).play();
  visitorMixer.setTime(0);
  machine.updateWorldMatrix(true, true);
  let path;
  let duration;
  let elapsed = 0;
  let playing = false;
  let disposed = false;
  let phase;

  function carry() {
    visual.position.copy(treadStance);
    step.localToWorld(visual.position);
    machine.worldToLocal(visual.position);
  }
  function sample(seconds) {
    elapsed = MathUtils.clamp(seconds, 0, duration);
    const nativeTime = path.start + elapsed;
    // Negative approach time crosses each clip's own loop boundary. Handrail
    // and step periods differ, so wrapping the entire mixer breaks continuity.
    for (const action of actions) {
      const period = action.getClip().duration;
      action.time =
        nativeTime >= 0 && nativeTime < period ? nativeTime : MathUtils.euclideanModulo(nativeTime, period);
    }
    machineMixer.update(0);
    visitorMixer.setTime(elapsed);
    machine.updateWorldMatrix(true, true);
    phase = path.sample(nativeTime, carry);
    visual.updateWorldMatrix(true, true);
  }
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
    if (!Number.isFinite(deltaSeconds) || deltaSeconds < 0)
      throw new RangeError('Ride update needs a nonnegative finite duration.');
    sample(elapsed + deltaSeconds);
    if (elapsed === duration) pause();
  }
  function dispose() {
    if (disposed) return;
    disposed = true;
    pause();
    machineMixer.stopAllAction();
    machineMixer.uncacheRoot(machine);
    visitorMixer.stopAllAction();
    visitorMixer.uncacheRoot(passenger);
    visual.removeFromParent();
    machine.updateWorldMatrix(true, true);
  }
  try {
    path = createPath({ machine, step, visual, passenger });
    duration = path.end - path.start;
    sample(0);
  } catch (error) {
    dispose();
    throw error;
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
    get phase() {
      return phase;
    },
  };
}

export function createEscalatorPassenger(options) {
  return createPassengerTimeline(options, () => ({
    start: 0.3,
    end: 18.1,
    sample(_time, carry) {
      carry();
      return 'ride';
    },
  }));
}
