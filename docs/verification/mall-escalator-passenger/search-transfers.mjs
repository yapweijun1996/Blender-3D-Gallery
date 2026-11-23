import fs from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import * as T from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const v = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z);
const read = async (file) => {
  const bytes = await fs.readFile(file);
  return new GLTFLoader().parseAsync(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    '',
  );
};
const [esc, person] = await Promise.all([
  read('models/escalator/exports/optimized.glb'),
  read('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb'),
]);
const es = esc.scene, ps = person.scene;
const mx = new T.AnimationMixer(es), vm = new T.AnimationMixer(ps);
for (const clip of esc.animations) mx.clipAction(clip).play();
const still = vm.clipAction(person.animations.find((c) => c.name === 'idle')).play(),
  moving = vm.clipAction(person.animations.find((c) => c.name === 'walk')).play();
const cycle = moving.getClip().duration;
ps.rotation.y = Math.PI;
const feet = ['LeftFoot', 'RightFoot'].map((n) => {
  const node = ps.getObjectByName(n), result = [];
  node.traverse((o) => {
    if (o.isMesh) result.push(o);
  });
  return result;
});
const temp = v();
function state(phase, w) {
  still.time = 0;
  moving.time = phase;
  still.setEffectiveWeight(1 - w);
  moving.setEffectiveWeight(w);
  vm.update(0);
  ps.updateMatrixWorld(true);
  const f = feet.map((meshes) => {
    let lo = Infinity, px = 0, pz = 0;
    for (const mesh of meshes) {
      const a = mesh.geometry.attributes.position;
      for (let i = 0; i < a.count; i++) {
        temp.fromBufferAttribute(a, i).applyMatrix4(mesh.matrixWorld);
        if (temp.y < lo) {
          lo = temp.y;
          px = temp.x;
          pz = temp.z;
        }
      }
    }
    return { y: lo, x: px, z: pz };
  });
  const ground = Math.min(f[0].y, f[1].y);
  return f.map((o) => ({ ...o, y: o.y - ground }));
}
// Quantize phase and blend weight for ranking only. Re-evaluate 60 finalists with exact native poses.
const NW = 20, NP = 128;
const lut = Array.from(
  { length: NW + 1 },
  (_, w) => Array.from({ length: NP }, (_, k) => state(k / NP * cycle, w / NW)),
);
const step = es.getObjectByName('STEP_00');
const hz = 120;
mx.setTime(0);
es.updateMatrixWorld(true);
const inverseStep = step.matrixWorld.clone().invert();
const bounds = new T.Box3();
es.getObjectByName('STEP_BODY_00').traverse((node) => {
  if (!node.isMesh) return;
  const local = new T.Matrix4().multiplyMatrices(inverseStep, node.matrixWorld);
  const positions = node.geometry.getAttribute('position');
  for (let i = 0; i < positions.count; i++) {
    bounds.expandByPoint(v().fromBufferAttribute(positions, i).applyMatrix4(local));
  }
});
const period = esc.animations.find((clip) => clip.name === 'StepCirculation_STEP_00').duration;
const span = { min: bounds.min.toArray(), max: bounds.max.toArray() };
function prepare(count, start) {
  return Array.from({ length: count }, (_, i) => {
    const t = start + i / hz;
    mx.setTime(T.MathUtils.euclideanModulo(t, period));
    es.updateMatrixWorld(true);
    return {
      t,
      z: step.position.z,
      height: step.position.y + span.max[1],
      level: step.quaternion.angleTo(new T.Quaternion()) < 1e-5,
    };
  });
}
const samples = { lower: prepare(4 * hz + 1, -1.5), upper: prepare(5 * hz + 1, 16.0) };
const box = (node) => new T.Box3().setFromObject(es.getObjectByName(node), true);
const fixed = { lower: box('LANDING_Lower'), upper: box('LANDING_Upper') };
const clip01 = (n) => Math.min(1, Math.max(0, n)), smooth = (n) => n * n * (3 - 2 * n);
function path(config, t) {
  const { time, length, z0, z1, v0, v1, phase } = config,
    u = clip01((t - time) / length),
    u2 = u * u,
    u3 = u2 * u;
  // Continuous position and surface-matched endpoint velocities.
  const z = (2 * u3 - 3 * u2 + 1) * z0 + (u3 - 2 * u2 + u) * length * v0 + (-2 * u3 + 3 * u2) * z1 +
    (u3 - u2) * length * v1;
  const speed = (6 * u2 - 6 * u) * (z0 - z1) / length + (3 * u2 - 4 * u + 1) * v0 + (3 * u2 - 2 * u) * v1;
  const w = smooth(Math.min(1, (t - time) / .13, (time + length - t) / .13));
  const gaitPhase = T.MathUtils.euclideanModulo(t - time + phase, cycle);
  return { z, speed, w: clip01(w), phase: gaitPhase };
}
function score(config, kind, stride = 3, exact = false) {
  let margin = Infinity, maxSpeed = 0, nearSurface = 0, failed = 0, grounded = 0, longest = 0, run = 0;
  const data = samples[kind], de = fixed[kind], datum = kind === 'lower' ? 0 : 3;
  const frames = Math.round(config.length * hz), base = Math.round((config.time - data[0].t) * hz);
  for (let i = 0; i <= frames; i += stride) {
    const obj = data[base + i],
      p = path(config, obj.t),
      f = exact ? state(p.phase, p.w) : lut[Math.round(p.w * NW)][Math.round(p.phase / cycle * NP) % NP];
    const lo = obj.z + span.min[2], hi = obj.z + span.max[2];
    maxSpeed = Math.max(maxSpeed, Math.abs(p.speed));
    for (const foot of f) {
      if (foot.y > .0007) continue;
      grounded++;
      const z = p.z + foot.z, deckMargin = Math.min(z - de.min.z - .001, de.max.z - .001 - z);
      const stepMargin = obj.level && Math.abs(obj.height - datum) < .00001
        ? Math.min(z - lo, hi - z)
        : -10;
      const edge = Math.max(deckMargin, stepMargin);
      if (edge < 0) {
        failed++;
        run++;
        longest = Math.max(longest, run);
      } else run = 0;
      margin = Math.min(margin, edge);
      if (edge < .004) nearSurface++;
    }
  }
  return { margin, maxSpeed, nearSurface, failed, grounded, longest };
}
// The screen admits the swept step below the comb. The full mesh replay verifies actual
// interleaving teeth, grooves, adjacent steps and the complete near-ground sole patch.
const latest = {};
for (const kind of ['lower', 'upper']) {
  const data = samples[kind];
  const options = [];
  for (const length of [1.0, 1.2, 1.4, 1.6, 1.8, 2.0]) {
    for (const fixedZ of (kind === 'lower' ? [4.99, 5.05, 5.12, 5.20] : [-4.64, -4.72, -4.80, -4.88])) {
      for (let j = 0; j < 23; j++) {
        const attach = kind === 'lower' ? .3 + j * .05 : 17 + j * .05;
        const time = kind === 'lower' ? attach - length : attach;
        const base = Math.round((time - data[0].t) * hz);
        if (base < 0 || base + Math.round(length * hz) >= data.length) {
          continue;
        }
        const movingZ = data[base + (kind === 'lower' ? Math.round(length * hz) : 0)].z + .240;
        const config = {
          time,
          length,
          z0: kind === 'lower' ? fixedZ : movingZ,
          z1: kind === 'lower' ? movingZ : fixedZ,
          v0: kind === 'lower' ? 0 : -.4998,
          v1: kind === 'lower' ? -.4998 : 0,
        };
        for (let k = 0; k < 32; k++) {
          const c = { ...config, phase: k * cycle / 32 }, s = score(c, kind);
          if (s.maxSpeed < 1.2) options.push({ c, s });
        }
      }
    }
  }
  options.sort((a, b) => a.s.failed - b.s.failed || b.s.margin - a.s.margin);
  const exact = options.slice(0, 60).map(({ c }) => ({ c, s: score(c, kind, 1, true) }));
  exact.sort((a, b) => a.s.failed - b.s.failed || b.s.margin - a.s.margin);
  latest[kind] = { tested: options.length, candidatesAt120Hz: exact.slice(0, 3) };
}
await fs.writeFile(
  fileURLToPath(new URL('transfer-open-ribs.json', import.meta.url)),
  JSON.stringify(latest, null, 2) + '\n',
);
console.log(JSON.stringify(latest, null, 2));
