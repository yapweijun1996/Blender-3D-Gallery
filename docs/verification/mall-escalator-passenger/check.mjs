import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { AnimationMixer, Box3, Raycaster, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { BODY } from '../mall-corridor/collision.js';
import { checkShoeSupport } from './shoe-support.mjs';

const vector = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const near = (value, expected) => assert.ok(Math.abs(value - expected) < 1e-5);
const ray = new Raycaster();
function hit(objects, origin, direction) {
  ray.set(origin, direction);
  return ray.intersectObjects(objects, true)[0];
}

async function load(path) {
  const bytes = await readFile(new URL('../../../models/' + path, import.meta.url));
  const body = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const gltf = await new GLTFLoader().parseAsync(body, '');
  gltf.scene.updateMatrixWorld(true);
  return { ...gltf, sha256: createHash('sha256').update(bytes).digest('hex') };
}

// Intersect each triangle with the station plane. Each facet's inner X edge
// is linear between consecutive intersection heights.
function sectionHeights(mesh, z) {
  const geometry = mesh.geometry,
    position = geometry.getAttribute('position');
  const vertices = Array.from({ length: position.count }, (_, i) =>
    vector().fromBufferAttribute(position, i).applyMatrix4(mesh.matrixWorld),
  );
  const heights = new Set();
  const index = geometry.index;
  for (let start = 0; start < (index?.count ?? position.count); start += 3) {
    const points = [0, 1, 2].map((i) => vertices[index ? index.getX(start + i) : start + i]);
    for (let i = 0; i < 3; i++) {
      const a = points[i],
        b = points[(i + 1) % 3];
      if (a.z < z !== b.z < z) heights.add(a.y + ((b.y - a.y) * (z - a.z)) / (b.z - a.z));
    }
  }
  return [...heights];
}

function checkPassage(machine) {
  const component = (name) => {
    const node = machine.getObjectByName(name);
    return node.isMesh ? node : node.children.find((part) => part.isMesh);
  };
  const surfaces = [];
  machine.traverse((node) => {
    if (/^(LANDING_|COMB_|STEP_BODY_)/.test(node.name)) surfaces.push(node);
  });
  const parts = {
    skirt: ['SKIRT_L', 'SKIRT_R'],
    guard: ['GUARD_L', 'GUARD_R'],
    handrail: ['HANDRAIL_L', 'HANDRAIL_R'],
    seam: ['HANDRAIL_MaterialSeam_L', 'HANDRAIL_MaterialSeam_R'],
  };
  const seamZ = new Box3().setFromObject(component(parts.seam[1]), true).getCenter(vector()).z;
  const stations = [
    ['lower deck', 5.12],
    ['lower handrail return', 4.8],
    ['lower belt seam', seamZ],
    ['lower comb', 4.52],
    ['lower flat tread', 3.62],
    ['lower change of gradient', 2.4],
    ['incline lower', 1.04],
    ['incline middle', 0.037],
    ['incline upper', -1.3],
    ['upper flat tread', -3.2],
    ['upper handrail return', -3.95],
    ['upper comb', -4.3],
    ['upper deck', -5.12],
  ];
  let narrowest = { width: Infinity };
  const sections = stations.map(([station, z]) => {
    // A comb tooth and a tread rib alternate across the centreline.
    const floorY = Math.max(
      ...[0, 0.02].map((x) => hit(surfaces, vector(x, 5, z), vector(0, -1, 0)).point.y),
    );
    const widths = {};
    for (const [name, pair] of Object.entries(parts)) {
      const [left, right] = pair.map(component);
      const heights = sectionHeights(right, z);
      if (!heights.length) continue;
      const low = Math.max(floorY, Math.min(...heights));
      const high = Math.min(floorY + BODY.height, Math.max(...heights));
      if (high - low < 0.00001) continue;
      const samples = [
        low + 0.000001,
        high - 0.000001,
        (high + low) / 2,
        ...heights.filter((y) => y > low && y < high),
      ];
      let width = Infinity;
      for (const y of samples) {
        const origin = vector(0, y, z);
        const a = hit([left], origin, vector(-1, 0, 0)),
          b = hit([right], origin, vector(1, 0, 0));
        if (!a || !b) continue;
        const span = b.point.x - a.point.x;
        width = Math.min(width, span);
        if (span < narrowest.width)
          narrowest = { station, part: name, width: span, y, z, left: a.point.x, right: b.point.x };
      }
      assert.ok(Number.isFinite(width), station + ' ' + name);
      widths[name] = width;
    }
    return { station, z, floorY, widths };
  });
  near(sections[0].floorY, 0);
  near(sections.at(-1).floorY, 3);
  near(narrowest.width, 1.015);
  for (const index of [4, 7, 9]) {
    near(sections[index].widths.skirt, 1.065);
    near(sections[index].widths.guard, 1.08);
    near(sections[index].widths.handrail, 1.02);
  }
  return { sections, narrowest };
}

function checkVisitor(visitor, guard, halfWidth) {
  const result = {},
    diameter = 2 * BODY.radius;
  near(diameter, 1.12);
  const excessPerSide = BODY.radius - halfWidth;
  assert.ok(excessPerSide > 0.05);
  const controlZ = 3.62;
  function glassAt(p) {
    const left = hit([guard], vector(0, p.y, p.z), vector(1, 0, 0));
    const right = hit([guard], vector(0.8, p.y, p.z), vector(-1, 0, 0));
    if (left && right && left.point.x < p.x && p.x < right.point.x) return [left.point.x, right.point.x];
  }
  let shiftWitness, rotationWitness;
  for (const state of ['idle', 'walk']) {
    const scene = visitor.scene.clone(true),
      mixer = new AnimationMixer(scene);
    const clip = visitor.animations.find((clip) => clip.name === state);
    mixer.clipAction(clip).play();
    const envelope = new Box3(),
      farthest = vector(),
      p = vector();
    let maxRadius = 0;
    for (let frame = 0; frame <= 120; frame++) {
      mixer.setTime((clip.duration * frame) / 120);
      scene.updateMatrixWorld(true);
      scene.traverseVisible((mesh) => {
        if (!mesh.isMesh) return;
        for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
          mesh.getVertexPosition(i, p).applyMatrix4(mesh.matrixWorld);
          envelope.expandByPoint(p);
          const radius = Math.hypot(p.x, p.z);
          if (radius > maxRadius) {
            maxRadius = radius;
            farthest.copy(p);
          }
          if (state === 'idle' && !shiftWitness) {
            const x = 0.33 - p.x;
            if (x > 0.5403 && x < 0.5597 && p.y > 0.12 && p.y < 0.82) {
              const vertex = vector(x, p.y, controlZ - p.z),
                glass = glassAt(vertex);
              if (glass) shiftWitness = { rootX: 0.33, mesh: mesh.name, vertex: vertex.toArray(), glass };
            }
          }
        }
      });
    }
    const size = envelope.getSize(vector());
    result[state] = {
      samples: 121,
      width: size.x,
      depth: size.z,
      sideMargin: halfWidth - Math.max(-envelope.min.x, envelope.max.x),
    };
    if (state === 'walk') {
      const yaw = Math.atan2(farthest.z, farthest.x);
      const vertex = farthest
        .clone()
        .applyAxisAngle(vector(0, 1, 0), yaw)
        .add(vector(0, 0, controlZ));
      rotationWitness = { yaw, vertex: vertex.toArray(), glass: glassAt(vertex) };
      assert.ok(rotationWitness.glass && maxRadius < BODY.radius);
    }
    mixer.stopAllAction();
    mixer.uncacheRoot(scene);
  }
  assert.ok(shiftWitness && result.idle.sideMargin > 0.168 && result.walk.sideMargin > 0.172);
  return {
    diameter,
    height: BODY.height,
    excessPerSide,
    fixedHeadingYaw: Math.PI,
    body: result,
    shiftWitness,
    rotationWitness,
  };
}

const [machine, visitor] = await Promise.all([
  load('escalator/exports/optimized.glb'),
  load('gjh-mall-visitor/exports/gjh-mall-visitor.glb'),
]);
const passage = checkPassage(machine.scene);
const clearance = checkVisitor(
  visitor,
  machine.scene.getObjectByName('GUARD_R'),
  passage.narrowest.width / 2,
);
const carried = checkShoeSupport(machine, visitor);
const report = {
  units: 'metres and seconds',
  sha256: { machine: machine.sha256, visitor: visitor.sha256 },
  ...passage,
  clearance,
  carried,
};
console.log(JSON.stringify(report, (_, value) => (typeof value === 'number' ? +value.toFixed(9) : value), 2));
