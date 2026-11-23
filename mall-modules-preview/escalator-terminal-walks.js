import { Box3, MathUtils, Vector3 } from 'three';
import { upperExit } from './escalator-upper-exit.js';

const smooth = (n) => n * n * n * (10 + n * (-15 + 6 * n));
const unit = (t, a, b) => MathUtils.clamp((t - a) / (b - a), 0, 1);
const prepare = 0.18,
  settle = 0.18,
  bothPlanted = 0.055;

// Each transfer owns its fixed-deck splice. Landing-edge coordinates are measured
// on the installed model instead of using a nominal escalator length.
export function createTerminalWalks(rig, machine, lowerDeckPoleZ, lowerEnd) {
  const xs = rig.feet.map((f) => f.poleFromRoot.x);
  const localBox = (name) => {
    const node = machine.getObjectByName(name);
    if (!node) throw new Error('The terminal walk requires the native deck ' + name);
    const bounds = new Box3();
    machine.updateWorldMatrix(true, true);
    const inverse = machine.matrixWorld.clone().invert(),
      p = new Vector3();
    node.traverse((o) => {
      if (!o.isMesh) return;
      const matrix = inverse.clone().multiply(o.matrixWorld),
        a = o.geometry.getAttribute('position');
      for (let i = 0; i < a.count; i++)
        bounds.expandByPoint(p.fromBufferAttribute(a, i).applyMatrix4(matrix));
    });
    return bounds;
  };
  const lowerDeck = localBox('LANDING_Lower'),
    upperDeck = localBox('LANDING_Upper');
  function sequence({ name, startPole, fixedTime, alignEnd, height, stops }) {
    const initialOwner = name === 'lower' ? 'floor2m' : 'LANDING_Upper';
    const previous = [
        [startPole, initialOwner],
        [startPole, initialOwner],
      ],
      steps = [];
    let clock = prepare;
    stops.forEach(([z, owner], index) => {
      const leg = index % 2,
        change = Math.abs(z - previous[leg][0]),
        duration = 0.16 + 0.7 * change;
      const step = { index: leg, start: clock, end: clock + duration, from: previous[leg], to: [z, owner] };
      steps.push(step);
      previous[leg] = step.to;
      clock = step.end + (index === stops.length - 1 ? 0 : bothPlanted);
    });
    const length = clock + settle,
      start = alignEnd ? fixedTime - length : fixedTime,
      end = alignEnd ? fixedTime : fixedTime + length;
    function sample(time) {
      const local = time - start,
        placement = [
          [startPole, initialOwner],
          [startPole, initialOwner],
        ],
        lift = [0, 0];
      for (const move of steps) {
        if (local < move.start - 1e-9) break;
        const leg = move.index;
        if (local >= move.end - 1e-9) {
          placement[leg] = move.to;
          continue;
        }
        if (local <= move.start + 1e-9) break;
        const u = unit(local, move.start, move.end),
          z = MathUtils.lerp(move.from[0], move.to[0], smooth(u));
        const heightM = Math.min(0.092, 0.045 + 0.085 * Math.abs(move.to[0] - move.from[0]));
        placement[leg] = [z, null];
        lift[leg] = 16 * heightM * u * u * (1 - u) * (1 - u);
        break;
      }
      const stretch =
        -1 + 2 * smooth(unit(local, 0, prepare)) - 2 * smooth(unit(local, length - settle, length));
      const targets = placement.map(([z], i) => new Vector3(xs[i], height + lift[i], z));
      return {
        left: targets[0],
        right: targets[1],
        leftSupport: placement[0][1],
        rightSupport: placement[1][1],
        stretch,
      };
    }
    return {
      start,
      end,
      sample,
      events: steps.map((s) => ({
        foot: s.index === 0 ? 'left' : 'right',
        liftOff: start + s.start,
        touchDown: start + s.end,
        fromZ: s.from[0],
        toZ: s.to[0],
        landsOn: s.to[1],
      })),
    };
  }
  const lowerSlab = 6 + rig.feet[0].poleFromRoot.z,
    upperSlab = -6 + rig.feet[0].poleFromRoot.z;
  return {
    lower: sequence({
      name: 'lower',
      startPole: lowerSlab,
      fixedTime: lowerEnd,
      alignEnd: true,
      height: lowerDeck.max.y,
      stops: [
        [lowerDeck.max.z + 0.255, 'floor2m'],
        [lowerDeck.max.z + 0.06, 'escalatorTransition2m'],
        [lowerDeck.max.z - 0.192, 'LANDING_Lower'],
        [lowerDeckPoleZ, 'LANDING_Lower'],
        [lowerDeckPoleZ, 'LANDING_Lower'],
      ],
    }),
    upper: sequence({
      name: 'upper',
      startPole: upperExit.deckPoleZ,
      fixedTime: upperExit.finish,
      alignEnd: false,
      height: upperDeck.max.y,
      stops: [
        [upperDeck.min.z + 0.51, 'LANDING_Upper'],
        [upperDeck.min.z + 0.255, 'LANDING_Upper'],
        [upperDeck.min.z - 0.06, 'escalatorTransition2m'],
        [upperDeck.min.z - 0.354, 'floor2m'],
        [upperSlab, 'floor2m'],
        [upperSlab, 'floor2m'],
      ],
    }),
  };
}
