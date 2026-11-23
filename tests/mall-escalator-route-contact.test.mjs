import assert from 'node:assert/strict';
import test from 'node:test';
import { Box3 } from 'three';
import {
  assets, v, near, rounded, touch, install, sole, terrain, sideClearance,
  finishUnderShoe, undersideAt, movingNodes, matrices, difference,
} from './helpers/mall-escalator-geometry.mjs';

const startClock = -3.5339295944;
const atClock = (t) => t - startClock;
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
