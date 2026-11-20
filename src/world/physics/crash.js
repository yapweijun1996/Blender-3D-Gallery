export const CRASH_TUNING = Object.freeze({
  impactThreshold: 4, // Impulse per unit vehicle mass, in m/s.
  fullDamageImpact: 40, // Excess impulse per unit mass for one full damage point.
  flippedUpDot: 0.2,
  flippedSeconds: 1.5,
});

export function uprightRotation(heading) {
  return { x: 0, y: Math.sin(heading / 2), z: 0, w: Math.cos(heading / 2) };
}

export function upDot({ x, z }) {
  return 1 - 2 * (x * x + z * z);
}

export function createCrashState(body, mass) {
  let damage = 0;
  let timeTilted = 0;
  let flipped = false;

  return {
    get damage() { return damage; },
    get flipped() { return flipped; },

    addImpact(impulse) {
      const excess = impulse / mass - CRASH_TUNING.impactThreshold;
      if (excess > 0) damage = Math.min(1, damage + excess / CRASH_TUNING.fullDamageImpact);
    },

    step(dt) {
      timeTilted = upDot(body.rotation()) < CRASH_TUNING.flippedUpDot ? timeTilted + dt : 0;
      flipped ||= timeTilted + 1e-9 >= CRASH_TUNING.flippedSeconds;
    },

    reset({ position, heading, repair }) {
      const zero = { x: 0, y: 0, z: 0 };
      body.setTranslation(position, true);
      body.setRotation(uprightRotation(heading), true);
      body.setLinvel(zero, true);
      body.setAngvel(zero, true);
      body.resetForces(true);
      body.resetTorques(true);
      timeTilted = 0;
      flipped = false;
      if (repair) damage = 0;
    },
  };
}

/** Rapier's contact-force events report force averaged over the solver step. */
export function drainCrashEvents(queue, dt, crashStates) {
  queue.drainContactForceEvents((event) => {
    const first = crashStates.get(event.collider1());
    const second = crashStates.get(event.collider2());
    const impulse = event.totalForceMagnitude() * dt;
    first?.addImpact(impulse);
    second?.addImpact(impulse);
  });
}
