import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import * as T from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

async function load(path) {
  const b = await fs.readFile(path);
  return new GLTFLoader().parseAsync(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength), '');
}
const [machine, visitor] = await Promise.all([
  load('models/escalator/exports/optimized.glb'),
  load('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb'),
]);
const candidates = JSON.parse(await fs.readFile(new URL('transfer-open-ribs.json', import.meta.url)));
const mx = new T.AnimationMixer(machine.scene), vm = new T.AnimationMixer(visitor.scene);
for (const clip of machine.animations) mx.clipAction(clip).play();
const period = machine.animations.find((c) => c.name === 'StepCirculation_STEP_00').duration;
const idle = vm.clipAction(visitor.animations.find((c) => c.name === 'idle')).play();
const walk = vm.clipAction(visitor.animations.find((c) => c.name === 'walk')).play();
const cycle = walk.getClip().duration;
visitor.scene.rotation.y = Math.PI;
const down = new T.Vector3(0, -1, 0), ray = new T.Raycaster();
const footMeshes = ['LeftFoot', 'RightFoot'].map((name) => {
  const meshes = [];
  visitor.scene.getObjectByName(name).traverse((o) => {
    if (o.isMesh) meshes.push(o);
  });
  return meshes;
});
const machineMeshes = [];
machine.scene.traverse((o) => {
  if (o.isMesh) {
    o.geometry.computeBoundingBox();
    let p = o;
    while (p.parent && !/^(LANDING_|COMB_|STEP_BODY_)/.test(p.name)) p = p.parent;
    machineMeshes.push({ object: o, owner: p, box: new T.Box3() });
  }
});
function pose(phase, amount) {
  idle.time = 0;
  walk.time = T.MathUtils.euclideanModulo(phase, cycle);
  idle.setEffectiveWeight(1 - amount);
  walk.setEffectiveWeight(amount);
  vm.update(0);
  visitor.scene.updateMatrixWorld(true);
  return footMeshes.map((meshes) => {
    const vertices = [];
    for (const mesh of meshes) {
      const p = mesh.geometry.getAttribute('position');
      for (let i = 0; i < p.count; i++) {
        vertices.push(new T.Vector3().fromBufferAttribute(p, i).applyMatrix4(mesh.matrixWorld));
      }
    }
    const index = vertices.reduce((b, v, i) => v.y < vertices[b].y ? i : b, 0);
    return { vertices, index };
  });
}
function position(c, time) {
  const u = T.MathUtils.clamp((time - c.time) / c.length, 0, 1), u2 = u * u, u3 = u2 * u;
  const fade = T.MathUtils.clamp(Math.min(time - c.time, c.time + c.length - time) / .13, 0, 1);
  return {
    z: (2 * u3 - 3 * u2 + 1) * c.z0 + (u3 - 2 * u2 + u) * c.length * c.v0 + (-2 * u3 + 3 * u2) * c.z1 +
      (u3 - u2) * c.length * c.v1,
    phase: time - c.time + c.phase,
    weight: fade * fade * (3 - 2 * fade),
  };
}
function floorRay(x, z, level, nearby) {
  ray.set(new T.Vector3(x, level + .4, z), down);
  let nearest = null;
  for (const m of nearby) {
    if (
      x < m.box.min.x - 1e-7 || x > m.box.max.x + 1e-7 || z < m.box.min.z - 1e-7 || z > m.box.max.z + 1e-7
    ) continue;
    const hit = ray.intersectObject(m.object, false)[0];
    if (hit && (!nearest || hit.distance < nearest.distance)) nearest = { ...hit, owner: m.owner };
  }
  return nearest;
}
// The inclusive fallback intersects the actual clipped convex triangle patches in X/Z.
// It can accept two surfaces up to 1.4 mm apart. A rejection therefore proves that
// even this deliberately generous contact envelope has no matching machine surface.
function heightClip(poly, level, sign) {
  const result = [];
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i],
      b = poly[(i + 1) % poly.length],
      da = (a.y - level) * sign,
      db = (b.y - level) * sign;
    if (da >= 0) result.push(a);
    if ((da >= 0) !== (db >= 0)) result.push(a.clone().lerp(b, da / (da - db)));
  }
  return result;
}
function intersectsXZ(a, b) {
  for (const polygon of [a, b]) {
    for (let i = 0; i < polygon.length; i++) {
      const p = polygon[i], q = polygon[(i + 1) % polygon.length], nx = q.z - p.z, nz = p.x - q.x;
      const dots = (poly) => poly.map((v) => nx * v.x + nz * v.z), aa = dots(a), bb = dots(b);
      if (Math.max(...aa) < Math.min(...bb) - 1e-12 || Math.max(...bb) < Math.min(...aa) - 1e-12) {
        return false;
      }
    }
  }
  return true;
}
function generousSolePatchHit(foot, index, level, tol, near) {
  const soles = [];
  const box = new T.Box3();
  let offset = 0;
  for (const mesh of footMeshes[index]) {
    const g = mesh.geometry, ix = g.index;
    for (let i = 0; i < (ix?.count ?? g.attributes.position.count); i += 3) {
      const tri = [0, 1, 2].map((j) => foot.vertices[offset + (ix ? ix.getX(i + j) : i + j)]);
      if (tri.every((v) => v.y > level + tol)) continue;
      const cut = heightClip(tri, level + tol, -1);
      cut.forEach((v) => box.expandByPoint(v));
      if (cut.length) soles.push(cut);
    }
    offset += g.attributes.position.count;
  }
  for (const m of near) {
    if (
      m.box.max.y < level - tol || m.box.max.x < box.min.x || m.box.min.x > box.max.x ||
      m.box.max.z < box.min.z || m.box.min.z > box.max.z
    ) continue;
    const g = m.object.geometry, ix = g.index, p = g.attributes.position;
    for (let i = 0; i < (ix?.count ?? p.count); i += 3) {
      const tri = [0, 1, 2].map((j) =>
        new T.Vector3().fromBufferAttribute(p, ix ? ix.getX(i + j) : i + j).applyMatrix4(
          m.object.matrixWorld,
        )
      );
      if (
        tri.every((v) => v.y < level - tol) || tri.every((v) => v.x < box.min.x) || tri.every((v) =>
          v.x > box.max.x
        ) ||
        tri.every((v) => v.z < box.min.z) || tri.every((v) => v.z > box.max.z)
      ) continue;
      const cut = heightClip(tri, level - tol, 1);
      if (cut.length && soles.some((poly) => intersectsXZ(poly, cut))) return true;
    }
  }
  return false;
}
function evaluate(c, kind, hz, x = 0) {
  const level = kind === 'lower' ? 0 : 3;
  const frames = Math.round(c.length * hz), groundTolerance = .0007;
  let unsupportedWholePatchFeet = 0, unsupportedWholePatchFrames = 0;
  let previous,
    grounded = 0,
    unsupported = 0,
    distinctFeetUnsupported = 0,
    worstPoleDistance = 0,
    maxSurfaceAbovePlane = 0;
  let slide = 0, slideSteps = 0, maxSpeed = 0, overlapSamples = 0, otherSupports = 0;
  const owners = {}, badWitness = [];
  for (let i = 0; i <= frames; i++) {
    const time = c.time + c.length * i / frames, p = position(c, time);
    mx.setTime(T.MathUtils.euclideanModulo(time, period));
    machine.scene.updateMatrixWorld(true);
    const feet = pose(p.phase, p.weight);
    const sourceY = Math.min(...feet.map((f) => f.vertices[f.index].y));
    const groundOffset = level - sourceY;
    const shift = new T.Vector3(x, groundOffset, p.z);
    let shoeBounds = new T.Box3();
    for (const foot of feet) {
      for (const v of foot.vertices) {
        v.add(shift);
        shoeBounds.expandByPoint(v);
      }
    }
    const near = machineMeshes.filter((m) => {
      m.box.copy(m.object.geometry.boundingBox).applyMatrix4(m.object.matrixWorld);
      return m.box.max.x >= shoeBounds.min.x && m.box.min.x <= shoeBounds.max.x &&
        m.box.max.z >= shoeBounds.min.z && m.box.min.z <= shoeBounds.max.z &&
        m.box.max.y >= level - .32 && m.box.min.y <= shoeBounds.max.y + .001;
    });
    // For ambiguous rotated/enclosing bounds, use the maximum height of the actual triangles
    // clipped against the full X/Z rectangle around both shoes. With every shoe vertex at
    // or above the terminal level this certifies no mesh intrusion whenever the bound is zero.
    for (const m of near) {
      if (m.box.max.y <= level + 1e-6) continue;
      const g = m.object.geometry, idx = g.index, verts = g.attributes.position;
      let found = false;
      for (let k = 0; k < (idx?.count ?? verts.count); k += 3) {
        let poly = [0, 1, 2].map((j) =>
          new T.Vector3().fromBufferAttribute(verts, idx ? idx.getX(k + j) : k + j).applyMatrix4(
            m.object.matrixWorld,
          )
        );
        if (poly.every((v) => v.y <= level + 1e-6)) continue;
        for (
          const [axis, val, sense] of [['x', shoeBounds.min.x, 1], ['x', shoeBounds.max.x, -1], [
            'z',
            shoeBounds.min.z,
            1,
          ], ['z', shoeBounds.max.z, -1]]
        ) {
          const next = [];
          for (let j = 0; j < poly.length; j++) {
            const a = poly[j],
              b = poly[(j + 1) % poly.length],
              da = (a[axis] - val) * sense,
              db = (b[axis] - val) * sense;
            if (da >= 0) next.push(a);
            if ((da < 0) !== (db < 0)) next.push(a.clone().lerp(b, da / (da - db)));
          }
          poly = next;
        }
        if (poly.length) {
          found = true;
          maxSurfaceAbovePlane = Math.max(maxSurfaceAbovePlane, ...poly.map((v) => v.y - level));
        }
      }
      if (found) overlapSamples++;
    }
    for (const [index, foot] of feet.entries()) {
      const pole = foot.vertices[foot.index];
      if (pole.y - level > groundTolerance) continue;
      grounded++;
      const hit = floorRay(pole.x, pole.z, level, near);
      const distance = hit ? pole.y - hit.point.y : Infinity;
      worstPoleDistance = Math.max(worstPoleDistance, distance);
      // A slightly off-centre pole can bridge a small groove. Search every near-ground vertex.
      let acceptable = hit && Math.abs(distance) <= groundTolerance ? hit : null;
      if (!acceptable) {
        for (const v of foot.vertices) {
          if (v.y - level > groundTolerance) continue;
          const alt = floorRay(v.x, v.z, level, near);
          if (alt && Math.abs(v.y - alt.point.y) <= groundTolerance) {
            acceptable = alt;
            break;
          }
        }
      }
      if (!acceptable) {
        unsupported++;
        foot.generousHit = generousSolePatchHit(foot, index, level, groundTolerance, near);
        if (!foot.generousHit) unsupportedWholePatchFeet++;
        if (!foot.generousHit && badWitness.length < 5) {
          badWitness.push({
            time,
            foot: index,
            pole: pole.toArray(),
            below: hit?.owner.name ?? null,
            gapM: hit ? distance : null,
          });
        }
        continue;
      }
      foot.support = acceptable.owner;
      owners[foot.support.name] = (owners[foot.support.name] ?? 0) + 1;
      if (
        ![
          kind === 'lower' ? 'LANDING_Lower' : 'LANDING_Upper',
          kind === 'lower' ? 'COMB_Lower' : 'COMB_Upper',
          'STEP_BODY_00',
        ].includes(foot.support.name)
      ) otherSupports++;
      const prev = previous?.[index];
      if (prev?.support !== foot.support) continue;
      // Track the previous planted MATERIAL vertex on this shoe, avoiding the false
      // velocity obtained when the nearest sole vertex changes during heel/toe roll.
      const anchor = prev.localContact.clone().applyMatrix4(foot.support.matrixWorld);
      const displacement = foot.vertices[prev.index].distanceTo(anchor);
      slide += displacement;
      slideSteps++;
      maxSpeed = Math.max(maxSpeed, displacement * hz);
    }
    if (feet.every((f) => !f.support)) distinctFeetUnsupported++;
    if (feet.every((f) => !f.support && !f.generousHit)) unsupportedWholePatchFrames++;
    for (const foot of feet) {
      if (foot.support) {
        foot.localContact = foot.vertices[foot.index].clone().applyMatrix4(
          foot.support.matrixWorld.clone().invert(),
        );
      }
    }
    previous = feet;
  }
  return {
    frames: frames + 1,
    grounded,
    unsupported,
    unsupportedWholePatchFeet,
    unsupportedWholePatchFrames,
    framesWithoutEitherFootSupported: distinctFeetUnsupported,
    worstPoleDropM: Number.isFinite(worstPoleDistance) ? worstPoleDistance : null,
    otherStepOrFixtureSamples: otherSupports,
    owners,
    peakSurfaceAboveLevelM: maxSurfaceAbovePlane,
    ambiguousPenetrationTests: overlapSamples,
    trackedSlideSamples: slideSteps,
    cumulativePlantedMaterialTravelM: slide,
    peakPlantedMaterialSpeedMS: maxSpeed,
    badWitness,
  };
}
function anchorSeeds(kind, time, rootZ) {
  const lower = kind === 'lower', level = lower ? 0 : 3;
  const step = machine.scene.getObjectByName('STEP_00');
  const body = machine.scene.getObjectByName('STEP_BODY_00');
  const deck = machine.scene.getObjectByName(lower ? 'LANDING_Lower' : 'LANDING_Upper');
  const joint = (name) => visitor.scene.getObjectByName('Left' + name).getWorldPosition(new T.Vector3());
  const phase = 61 / 240 * cycle, sourceFeet = pose(phase, 1);
  const getMachine = (t) => {
    mx.setTime(t);
    machine.scene.updateMatrixWorld(true);
    for (const m of machineMeshes) {
      m.box.copy(m.object.geometry.boundingBox).applyMatrix4(m.object.matrixWorld);
    }
  };
  getMachine(time);
  const hip = joint('Hip'), knee = joint('Knee'), ankle = joint('Foot');
  const anchors = {};
  let onTread;
  for (const [i, f] of sourceFeet.entries()) {
    const moving = lower === (i === 0), parent = moving ? step : deck;
    const pole = f.vertices[f.index], hit = floorRay(pole.x, rootZ + pole.z, level, machineMeshes);
    assert.ok(hit && hit.owner === (moving ? body : deck) && Math.abs(hit.point.y - level) < 1e-6);
    const local = parent.worldToLocal(hit.point.clone());
    anchors[i === 0 ? 'Left' : 'Right'] = {
      surface: hit.owner.name,
      world: hit.point.toArray(),
      parent: parent.name,
      local: local.toArray(),
      nativeShoeLiftM: level + pole.y - hit.point.y,
    };
    if (moving) onTread = { f, local, pole };
  }
  const comb = machine.scene.getObjectByName(lower ? 'COMB_Lower' : 'COMB_Upper');
  const combBounds = new T.Box3().setFromObject(comb, true);
  const { f, local, pole } = onTread, box = new T.Box3().setFromPoints(f.vertices);
  const treadBounds = new T.Box3().setFromObject(body, true);
  const minZ = treadBounds.min.z - step.position.z, maxZ = treadBounds.max.z - step.position.z;
  const windows = [];
  for (let i = 0; i <= 2400; i++) {
    const t = i / 120;
    getMachine(t);
    const anchor = step.localToWorld(local.clone());
    if (step.quaternion.angleTo(new T.Quaternion()) > 1e-5 || Math.abs(anchor.y - level) > 1e-6) continue;
    const lo = anchor.z + box.min.z - pole.z, hi = anchor.z + box.max.z - pole.z;
    if (
      lo < step.position.z + minZ || hi > step.position.z + maxZ ||
      (lower ? hi > combBounds.min.z : lo < combBounds.max.z)
    ) continue;
    const hit = floorRay(anchor.x, anchor.z, level, machineMeshes);
    if (hit && hit.owner === body && Math.abs(hit.point.y - level) < 1e-6) windows.push(t);
  }
  assert.ok(windows.length > 100 && windows.every((t, i) => i === 0 || t - windows[i - 1] < .009));
  const left = anchors.Left.world, right = anchors.Right.world;
  return {
    machineTimeS: time,
    nativeWalkPhaseS: phase,
    worldRootM: [0, level, rootZ],
    anchors,
    longitudinalSpanM: Math.abs(left[2] - right[2]),
    horizontalSpanM: Math.hypot(left[0] - right[0], left[2] - right[2]),
    hipToKneeM: hip.distanceTo(knee),
    kneeToAnkleM: knee.distanceTo(ankle),
    hipToAnkleM: hip.distanceTo(ankle),
    wholeMovingShoeOnFlatS: [windows[0], windows.at(-1)],
  };
}
const report = {};
for (const kind of ['lower', 'upper']) {
  const config = candidates[kind].candidatesAt120Hz[0].c;
  report[kind] = {
    config,
    replay240Hz: evaluate(config, kind, 240),
    replay480Hz: evaluate(config, kind, 480),
  };
}
for (const result of Object.values(report)) {
  for (const replay of [result.replay240Hz, result.replay480Hz]) {
    assert.ok(replay.unsupportedWholePatchFrames > 0);
    assert.ok(replay.peakSurfaceAboveLevelM < 1e-6);
    assert.ok(replay.cumulativePlantedMaterialTravelM > 1.5);
  }
}
const stages = 240;
let previous = null, forward = 0, back = 0;
for (let i = 0; i <= stages; i++) {
  const feet = pose(i / stages * cycle, 1);
  if (previous) {
    const [f, v] = previous.contact;
    const dx = feet[f].vertices[v].z - previous.feet[f].vertices[v].z;
    if (dx >= 0) forward += dx;
    else back -= dx;
  }
  const f = feet[0].vertices[feet[0].index].y <= feet[1].vertices[feet[1].index].y ? 0 : 1;
  previous = { feet, contact: [f, feet[f].index] };
}
report.fixedFloorNativeWalk = {
  cycleS: cycle,
  samples: stages + 1,
  zeroSlipRootTravelForwardM: forward,
  zeroSlipRootTravelBackwardM: back,
  netForwardM: forward - back,
};
assert.ok(forward > .98 && back > .94);
report.candidateAnchors = {
  lower: anchorSeeds('lower', 13 / 60, 4.583379274580105),
  upper: anchorSeeds('upper', 1094 / 60, -4.412428361778222),
};
await fs.writeFile(
  new URL('transfer-replay.json', import.meta.url),
  JSON.stringify(report, null, 2) + '\n',
);
for (const [k, r] of Object.entries(report)) console.log(k, r.replay480Hz ?? r);
