import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { assembleEscalatorTerminals, escalatorTerminalPaths } from '../mall-modules-preview/escalator-terminal.js';
import { createEscalatorRoute } from '../mall-modules-preview/escalator-passenger-route.js';

const load = (path) => readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
const assets = Object.fromEntries(
  await Promise.all(Object.entries(escalatorTerminalPaths).map(async ([key, path]) => [key, await load(path)])),
);
const avatar = await load('models/gjh-mall-visitor/exports/gjh-mall-visitor.glb');
const v = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const near = (a, b, tolerance, label) => assert.ok(Math.abs(a - b) <= tolerance, label + ': ' + a + ' vs ' + b);
const down = v(0, -1, 0);
const rounded = (x) => +x.toFixed(8);
const startClock = -3.5339295944;
const atClock = (t) => t - startClock;
const touch = 0.000002;

function install() {
  const { group, machine } = assembleEscalatorTerminals(
    Object.fromEntries(Object.entries(assets).map(([key, gltf]) => [key, gltf.scene])),
  );
  group.updateMatrixWorld(true);
  const route = createEscalatorRoute({
    machine,
    clips: assets.escalator.animations,
    avatar: avatar.scene,
    avatarClips: avatar.animations,
  });
  const shoes = ['LeftFoot', 'RightFoot'].map((name) => {
    const meshes = [];
    route.visual.getObjectByName(name).traverse((object) => {
      if (object.isMesh) meshes.push(object);
    });
    assert.ok(meshes.length);
    return meshes;
  });
  return { group, machine, route, shoes };
}

function sole(meshes) {
  const point = v(),
    pole = v(0, Infinity, 0),
    bounds = new Box3();
  for (const mesh of meshes) {
    const positions = mesh.geometry.attributes.position;
    for (let i = 0; i < positions.count; i++) {
      mesh.getVertexPosition(i, point).applyMatrix4(mesh.matrixWorld);
      bounds.expandByPoint(point);
      if (point.y < pole.y) pole.copy(point);
    }
  }
  return { pole, bounds };
}

function terrain(group, machine) {
  const parts = [],
    ray = new Raycaster();
  const add = (root, label, moving = false) =>
    root.traverse((mesh) => {
      if (!mesh.isMesh) return;
      mesh.geometry.computeBoundingBox();
      parts.push({ mesh, label, moving, box: mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld) });
    });
  for (const terminal of group.children.filter((node) => node.userData.terminal)) {
    const level = terminal.userData.terminal;
    for (const module of terminal.children) {
      if (module.userData.role === 'centre') add(module, level + ' tile');
      if (module.userData.moduleId === 'escalatorTransition2m') add(module, level + ' profile');
    }
  }
  for (const level of ['Lower', 'Upper'])
    for (const prefix of ['LANDING', 'COMB']) {
      const name = prefix + '_' + level;
      add(machine.getObjectByName(name), name);
    }
  machine.traverse((node) => {
    if (/^STEP_BODY_\d+$/.test(node.name)) add(node, node.name, true);
  });
  assert.equal(parts.filter((p) => p.moving).length, 58);
  const byMesh = new Map(parts.map((p) => [p.mesh, p]));
  function update() {
    for (const p of parts) if (p.moving) p.box.copy(p.mesh.geometry.boundingBox).applyMatrix4(p.mesh.matrixWorld);
  }
  function probe(point, ignore) {
    const from = point.y + 0.33;
    const boundsMatch = ({ box: b, label }) =>
      label !== ignore &&
      b.min.x <= point.x + 1e-6 &&
      b.max.x >= point.x - 1e-6 &&
      b.min.z <= point.z + 1e-6 &&
      b.max.z >= point.z - 1e-6 &&
      b.min.y <= from &&
      b.max.y >= point.y - 0.5;
    ray.set(v(point.x, from, point.z), down);
    ray.far = 0.83;
    const hit = ray.intersectObjects(
      parts.filter(boundsMatch).map((p) => p.mesh),
      false,
    )[0];
    return (
      hit && {
        object: hit.object,
        label: byMesh.get(hit.object).label,
        gap: point.y - hit.point.y,
        y: hit.point.y,
      }
    );
  }
  return { update, probe };
}

function sideClearance(machine, visual) {
  const sides = [];
  for (const label of ['SKIRT', 'GUARD', 'HANDRAIL', 'HANDRAIL_MaterialSeam'])
    for (const side of ['L', 'R']) {
      machine.getObjectByName(label + '_' + side).traverse((mesh) => {
        if (mesh.isMesh) sides.push([mesh, side]);
      });
    }
  const visitorMeshes = [];
  visual.traverse((mesh) => {
    if (mesh.isMesh) visitorMeshes.push(mesh);
  });
  for (const mesh of [...visitorMeshes, ...sides.map((s) => s[0])]) mesh.geometry.computeBoundingBox();
  const b = new Box3(),
    projected = new Box3();
  return () => {
    projected.makeEmpty();
    for (const mesh of visitorMeshes)
      projected.union(b.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld));
    let clearance = Infinity;
    for (const [mesh, side] of sides) {
      b.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld);
      clearance = Math.min(clearance, side === 'R' ? b.min.x - projected.max.x : projected.min.x - b.max.x);
    }
    return clearance;
  };
}

// Confirm the front/back of the actual posed shoe over a short transition. Each
// vertical line intersects shoe triangles and the real surface directly below.
function finishUnderShoe(shoe, pose, surface) {
  const ray = new Raycaster(),
    upper = pose.bounds.max.y + 0.02,
    lower = pose.bounds.min.y - 0.06;
  const samples = [];
  for (const fraction of [0.07, 0.23, 0.5, 0.77, 0.93]) {
    const z = pose.bounds.min.z + (pose.bounds.max.z - pose.bounds.min.z) * fraction;
    const point = v(pose.pole.x, lower, z);
    ray.set(point, v(0, 1, 0));
    ray.far = upper - lower;
    const hit = ray.intersectObjects(shoe, false)[0];
    if (!hit) continue;
    const contact = surface.probe(hit.point);
    assert.ok(contact, 'missing surface directly under near-edge shoe');
    assert.ok(contact.gap >= -2e-6, 'shoe triangles penetrate ' + contact.label);
    samples.push({ label: contact.label, y: contact.y, gap: contact.gap });
  }
  return samples;
}

function undersideAt(meshes, x, z, lowestY) {
  const ray = new Raycaster(v(x, lowestY - 0.04, z), v(0, 1, 0), 0, 0.26);
  return ray.intersectObjects(meshes, false)[0]?.point;
}

function movingNodes(machine) {
  const nodes = [];
  machine.traverse((node) => {
    if (/^STEP_\d+$|^HANDRAIL_MaterialSeam_[LR]$/.test(node.name)) nodes.push(node);
  });
  assert.equal(nodes.length, 60);
  return nodes;
}
function matrices(nodes) {
  return nodes.flatMap((node) => node.matrixWorld.toArray());
}
function difference(a, b) {
  assert.equal(a.length, b.length);
  return a.reduce((max, value, index) => Math.max(max, Math.abs(value - b[index])), 0);
}
test('the two centre tiles, both 120 mm finishes and original escalator support the animated floor-to-floor passenger', (t) => {
  const { group, machine, route, shoes } = install();
  t.after(() => route.dispose());
  const surface = terrain(group, machine);
  const clearance = sideClearance(machine, route.visual);
  const frames = Math.ceil(route.duration * 60);
  const grounded = new Map(),
    stations = {},
    handover = { lower: 0, upper: 0 };
  const profileSpan = {},
    missingProfile = {};
  const fixedPlateBounds = {
    lower: new Box3().setFromObject(machine.getObjectByName('COMB_Lower'), true),
    upper: new Box3().setFromObject(machine.getObjectByName('COMB_Upper'), true),
  };
  const toothProbes = { lower: 0, upper: 0 },
    closeToothMargin = { lower: Infinity, upper: Infinity };
  let undersideProbes = 0,
    undersidePenetration = 0,
    maxFrameJointTravel = 0,
    previousJoints;
  const legNodes = ['LeftHip', 'LeftKnee', 'LeftFoot', 'RightHip', 'RightKnee', 'RightFoot'].map((name) =>
    route.visual.getObjectByName(name),
  );
  let worstAir = 0,
    worstPenetration = 0,
    minimumSideClearance = Infinity,
    maxSoleLength = 0,
    maxSlide = 0;
  const last = [null, null],
    rideSamples = [];
  for (let frame = 0; frame <= frames; frame++) {
    const time = (route.duration * frame) / frames;
    route.seek(time);
    surface.update();
    minimumSideClearance = Math.min(minimumSideClearance, clearance());
    const joints = legNodes.map((node) => node.getWorldPosition(v()));
    if (previousJoints)
      for (let i = 0; i < joints.length; i++)
        maxFrameJointTravel = Math.max(maxFrameJointTravel, joints[i].distanceTo(previousJoints[i]));
    previousJoints = joints;
    const poses = shoes.map(sole);
    const hits = poses.map((s) => surface.probe(s.pole));
    const gaps = hits.map((h) => h?.gap ?? Infinity);
    worstAir = Math.max(worstAir, Math.min(...gaps));
    worstPenetration = Math.max(worstPenetration, ...gaps.map((g) => -g));
    const support = hits.map((h) => (h && Math.abs(h.gap) < touch ? h.label : null));
    assert.ok(support.some(Boolean), 'both soles unsupported at ' + time + ' ' + gaps);
    for (let i = 0; i < 2; i++) {
      const s = poses[i],
        hit = hits[i],
        label = support[i];
      maxSoleLength = Math.max(maxSoleLength, s.bounds.max.z - s.bounds.min.z);
      if (label) {
        grounded.set(label, (grounded.get(label) || 0) + 1);
        const local = hit.object.worldToLocal(s.pole.clone());
        if (last[i]?.object === hit.object) maxSlide = Math.max(maxSlide, local.distanceTo(last[i].local));
        last[i] = { object: hit.object, local };
      } else last[i] = null;
      for (const level of ['lower', 'upper']) {
        const comb = fixedPlateBounds[level];
        if (s.bounds.max.z >= comb.min.z && s.bounds.min.z <= comb.max.z) {
          for (const lane of [0.1, 0.14])
            for (const fraction of [0.055, 0.25, 0.5, 0.75, 0.945]) {
              const z = s.bounds.min.z + fraction * (s.bounds.max.z - s.bounds.min.z);
              const underside = undersideAt(shoes[i], Math.sign(s.pole.x) * lane, z, s.pole.y);
              if (!underside) continue;
              const under = surface.probe(underside);
              if (!under) continue; // An actual transverse gap between moving components.
              undersideProbes++;
              undersidePenetration = Math.max(undersidePenetration, -under.gap);
              if (under.label === 'COMB_' + (level === 'lower' ? 'Lower' : 'Upper')) {
                toothProbes[level]++;
                closeToothMargin[level] = Math.min(closeToothMargin[level], under.gap);
              }
            }
        }
        if (label === level + ' profile') {
          if (!profileSpan[level]) {
            const spans = finishUnderShoe(shoes[i], s, surface);
            profileSpan[level] = {
              labels: [...new Set(spans.map((a) => a.label))].sort(),
              levelRange: Math.max(...spans.map((a) => a.y)) - Math.min(...spans.map((a) => a.y)),
              shoeDepth: s.bounds.max.z - s.bounds.min.z,
            };
          }
          if (!missingProfile[level] && !support[1 - i]) {
            const absent = surface.probe(s.pole, label);
            missingProfile[level] = {
              passengerTime: time,
              nearest: absent?.label ?? null,
              gap: absent?.gap ?? null,
            };
            assert.ok(!absent || Math.abs(absent.gap) > 0.01, 'omitted profile must lose its planted sole');
          }
        }
      }
    }
    if (support.includes('LANDING_Lower') && support.includes('STEP_BODY_00')) handover.lower++;
    if (support.includes('LANDING_Upper') && support.includes('STEP_BODY_00')) handover.upper++;
    if (frame === 0 || frame === frames)
      stations[frame === 0 ? 'start' : 'end'] = { root: route.visual.position.toArray(), support };
    if (route.phase === 'ride') {
      assert.deepEqual(support, ['STEP_BODY_00', 'STEP_BODY_00']);
      rideSamples.push(route.visual.position.clone());
    }
  }
  assert.deepEqual(stations.start.support, ['lower tile', 'lower tile']);
  assert.deepEqual(stations.end.support, ['upper tile', 'upper tile']);
  near(stations.start.root[2], 6, 1e-5, 'lower tile origin');
  near(stations.end.root[2], -6, 1e-5, 'upper tile origin');
  near(stations.start.root[1], 0, 1e-5, 'start elevation');
  near(stations.end.root[1], 3, 1e-5, 'end elevation');
  for (const level of ['lower', 'upper']) {
    assert.deepEqual(
      profileSpan[level].labels,
      ['LANDING_' + (level === 'lower' ? 'Lower' : 'Upper'), level + ' profile', level + ' tile'].sort(),
    );
    assert.ok(profileSpan[level].shoeDepth > 0.29);
    assert.ok(profileSpan[level].levelRange < 2e-6);
    assert.ok(missingProfile[level]);
    assert.ok(handover[level] >= 2);
    assert.ok(toothProbes[level] > 30);
    assert.ok(closeToothMargin[level] > 0);
  }
  assert.ok(undersidePenetration < touch, 'shoe underside enters real top geometry');
  assert.ok(maxFrameJointTravel < 0.1, 'leg moved over 100 mm in one 60 Hz interval');
  assert.ok(worstPenetration < touch, 'planted sole penetration ' + worstPenetration);
  assert.ok(minimumSideClearance > 0.13, 'body envelope reaches a skirt, guard, belt or belt seam');
  assert.ok(maxSlide < 0.0002, 'a planted sole slid on its owning surface ' + maxSlide);
  const angles = [];
  for (let i = 1; i < rideSamples.length; i++) {
    const d = rideSamples[i].clone().sub(rideSamples[i - 1]);
    assert.ok(d.z < 0 && d.y >= -1e-6);
    angles.push((Math.atan2(d.y, -d.z) * 180) / Math.PI);
  }
  near(angles[0], 0, 0.001, 'lower flat');
  near(angles.at(-1), 0, 0.001, 'upper flat');
  near(angles[Math.floor(angles.length / 2)], 30, 0.05, 'central incline');
  // Shifting the posed sole half a rib pitch places it over a real 20 mm groove.
  route.seek(atClock(9));
  surface.update();
  const pole = sole(shoes[0]).pole;
  pole.x += 0.02;
  const groove = surface.probe(pole);
  assert.equal(groove.label, 'STEP_BODY_00');
  near(groove.gap, 0.02, 0.000002, 'real groove depth');
  t.diagnostic(
    JSON.stringify(
      {
        frames: frames + 1,
        grounded: Object.fromEntries(grounded),
        handover,
        profileSpan,
        missingProfile,
        maxSoleLength,
        worstAir,
        worstPenetration,
        minimumSideClearance,
        maxSlide,
        stations,
        groove: groove.gap,
        undersideProbes,
        undersidePenetration,
        toothProbes,
        closeToothMargin,
        maxFrameJointTravel,
      },
      (_k, n) => (typeof n === 'number' ? rounded(n) : n),
    ),
  );
});

test('world poses join smoothly and survive reverse scrubbing, restarting and disposal', (t) => {
  const { machine, route, shoes } = install();
  t.after(() => route.dispose());
  const natives = movingNodes(machine),
    reference = assets.escalator.scene;
  const rest = matrices(natives.map((node) => reference.getObjectByName(node.name)));
  const character = [];
  route.visual.traverse((node) => {
    if (node.isMesh) character.push(node);
  });
  const complete = () => matrices([route.visual, ...character, ...natives]);
  const elapsed = (t) => {
    route.seek(atClock(t));
    assert.equal(route.playing, false);
  };
  const joints = ['LeftHip', 'LeftKnee', 'LeftFoot', 'RightHip', 'RightKnee', 'RightFoot', 'Head'].map((name) =>
    route.visual.getObjectByName(name),
  );
  const worldPoints = (t) => {
    elapsed(t);
    return [
      route.visual.getWorldPosition(v()),
      ...joints.map((node) => node.getWorldPosition(v())),
      ...shoes.map((parts) => sole(parts).pole),
    ];
  };
  near(route.duration, 26.2392574, 2e-6, 'full route duration');
  const joins = [-0.8, -0.6, 0.18, 0.22, 1, 1.2, 17.37, 17.55, 18.24, 18.29, 18.96, 19.16];
  let maxJoinTravel = 0,
    maxVelocityChange = 0;
  const dt = 0.0001;
  for (const time of joins) {
    const before = worldPoints(time - dt),
      exact = worldPoints(time),
      after = worldPoints(time + dt);
    for (let i = 0; i < exact.length; i++) {
      maxJoinTravel = Math.max(maxJoinTravel, before[i].distanceTo(after[i]));
      const v0 = exact[i].clone().sub(before[i]).divideScalar(dt);
      const v1 = after[i].clone().sub(exact[i]).divideScalar(dt);
      maxVelocityChange = Math.max(maxVelocityChange, v0.distanceTo(v1));
    }
  }
  assert.ok(maxJoinTravel < 0.0003, 'world-space joint jumps at a handoff ' + maxJoinTravel);
  assert.ok(maxVelocityChange < 0.015, 'world-space velocity changes abruptly at a handoff ' + maxVelocityChange);
  const keyframes = [
    [-2, 'approach'],
    [0.1, 'board'],
    [8.21, 'ride'],
    [18.26, 'alight'],
    [20.5, 'depart'],
  ];
  const snapshots = keyframes.map(([time, phase]) => {
    elapsed(time);
    assert.equal(route.phase, phase);
    return complete();
  });
  let maxScrubDifference = 0;
  for (const index of [0, 4, 2, 1, 3, 0, 2, 4, 1]) {
    elapsed(keyframes[index][0]);
    maxScrubDifference = Math.max(maxScrubDifference, difference(complete(), snapshots[index]));
  }
  assert.ok(maxScrubDifference < 2e-6, 'scrubbing changes the pose at identical times ' + maxScrubDifference);
  route.restart();
  const initial = complete();
  route.play();
  route.update(route.duration + 0.1);
  assert.equal(route.time, route.duration);
  assert.equal(route.playing, false);
  assert.equal(route.phase, 'depart');
  route.play();
  route.pause();
  near(route.time, 0, 1e-10, 'replay returns to start');
  near(difference(complete(), initial), 0, 2e-6, 'reset restores all visitor, step and belt transforms');
  route.dispose();
  assert.equal(route.visual.parent, null);
  near(difference(matrices(natives), rest), 0, 2e-6, 'disposal restores every original animated assembly node');
  t.diagnostic(
    JSON.stringify(
      {
        joins: joins.length,
        worldSamplesPerJoin: 1 + joints.length + shoes.length,
        oneSidedSeconds: dt,
        maxJoinTravel,
        maxVelocityChange,
        maxScrubDifference,
        originalMovingNodes: natives.length,
      },
      (_k, n) => (typeof n === 'number' ? rounded(n) : n),
    ),
  );
});
