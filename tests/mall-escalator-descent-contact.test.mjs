import assert from 'node:assert/strict';
import test from 'node:test';
import { Box3, MathUtils } from 'three';
import {
  assets,
  v,
  near,
  touch,
  install,
  sole,
  terrain,
  sideClearance,
  finishUnderShoe,
  undersideAt,
} from './helpers/mall-escalator-geometry.mjs';

function partBounds(node) {
  return new Box3().setFromObject(node, true);
}

function downhillHeading(visual, shoePoses, mouth) {
  const head = visual.getObjectByName('Head').getWorldPosition(v());
  const faceOffset = partBounds(mouth).getCenter(v()).z - head.z;
  const ankle = ['LeftFoot', 'RightFoot'].map((name) => visual.getObjectByName(name).getWorldPosition(v()));
  return {
    faceOffset,
    soleOffsets: shoePoses.map((shoe, i) => shoe.pole.z - ankle[i].z),
    footLanes: ankle[1].x - ankle[0].x,
  };
}

function originalClockAt(point, track) {
  // Geometrically locate the posed physical step pivot on the original translation polyline.
  // Its time determines the reference for every other part, including the distinct belt period.
  let best = { distance: Infinity, time: null };
  const left = v(),
    right = v(),
    delta = v(),
    current = v();
  for (let i = 1; i < track.times.length; i++) {
    left.fromArray(track.values, (i - 1) * 3);
    right.fromArray(track.values, i * 3);
    delta.subVectors(right, left);
    const u = MathUtils.clamp(current.subVectors(point, left).dot(delta) / delta.lengthSq(), 0, 1);
    const distance = current.copy(left).addScaledVector(delta, u).distanceTo(point);
    if (distance < best.distance)
      best = { distance, time: MathUtils.lerp(track.times[i - 1], track.times[i], u) };
  }
  assert.ok(best.distance < 2e-6, 'the starting step is absent from the original motion path');
  return best.time;
}

test('the original 58 steps and both exposed handrail seams circulate downhill at matching physical speed', (t) => {
  const { machine, route } = install('down');
  t.after(() => route.dispose());
  const clips = assets.escalator.animations,
    step = machine.getObjectByName('STEP_00');
  const stepClip = clips.find((c) => c.name === 'StepCirculation_STEP_00');
  const nativeStart = originalClockAt(
    step.position,
    stepClip.tracks.find((c) => c.name === 'STEP_00.position'),
  );
  const expected = clips.flatMap((clip) =>
    clip.tracks.map((track) => {
      const [name, property] = track.name.split('.');
      return {
        duration: clip.duration,
        node: machine.getObjectByName(name),
        property,
        interpolant: track.createInterpolant(),
      };
    }),
  );
  assert.equal(new Set(expected.map((k) => k.node)).size, 60);
  assert.equal(expected.length, 120);
  assert.equal(new Set(expected.map((k) => k.duration)).size, 2);
  const seams = ['L', 'R'].map((side) => machine.getObjectByName('HANDRAIL_MaterialSeam_' + side));
  const tread = machine.getObjectByName('STEP_BODY_00');
  const frames = Math.ceil(route.duration * 6),
    dt = route.duration / frames;
  let maxDifference = 0;
  let matchedSlopeSegments = 0;
  let minSpeed = Infinity;
  let maxSpeed = 0;
  let worstSpeedMismatch = 0;
  let worstDirectionMismatch = 0;
  let prior;
  for (let i = 0; i <= frames; i++) {
    const elapsed = i * dt;
    route.seek(elapsed);
    for (const track of expected) {
      const tm = MathUtils.euclideanModulo(nativeStart - elapsed, track.duration);
      const original = track.interpolant.evaluate(tm);
      const actual = track.node[track.property].toArray();
      const sign =
        track.property === 'quaternion' && actual.reduce((a, b, j) => a + b * original[j], 0) < 0 ? -1 : 1;
      for (let j = 0; j < original.length; j++)
        maxDifference = Math.max(maxDifference, Math.abs(sign * original[j] - actual[j]));
    }
    // The centres of the rendered metal seam patches and of the complete tread are
    // measured on their original GLB meshes, independent of their node origin offsets.
    const points = [tread, ...seams].map((node) => partBounds(node).getCenter(v()));
    if (prior && route.phase === 'ride' && points[0].y > 0.45 && points[0].y < 2.35) {
      const vel = points.map((p, j) => p.clone().sub(prior[j]).divideScalar(dt));
      const angles = vel.map((d) => (Math.atan2(-d.y, d.z) * 180) / Math.PI);
      if (angles.every((a) => Math.abs(a - 30) < 0.15)) {
        matchedSlopeSegments++;
        for (const vector of vel) {
          assert.ok(vector.z > 0 && vector.y < 0);
          minSpeed = Math.min(minSpeed, vector.length());
          maxSpeed = Math.max(maxSpeed, vector.length());
        }
        for (const belt of vel.slice(1)) {
          worstSpeedMismatch = Math.max(worstSpeedMismatch, Math.abs(belt.length() - vel[0].length()));
          worstDirectionMismatch = Math.max(worstDirectionMismatch, (belt.angleTo(vel[0]) * 180) / Math.PI);
        }
      }
    }
    prior = points;
  }
  assert.ok(
    maxDifference < 1.5e-5,
    'an original track was not sampled at the shared decreasing native time: ' + maxDifference,
  );
  assert.ok(matchedSlopeSegments > 35 && minSpeed > 0.495 && maxSpeed < 0.505);
  assert.ok(worstSpeedMismatch < 0.001 && worstDirectionMismatch < 0.1);
  assert.ok(nativeStart - route.duration < 0, 'the sweep must include the clocks wrapping');
  t.diagnostic(
    JSON.stringify({
      nativeStart,
      elapsedDuration: route.duration,
      trackComparisons: (frames + 1) * expected.length,
      maxDifference,
      matchedSlopeSegments,
      minSpeed,
      maxSpeed,
      worstSpeedMismatch,
      worstDirectionMismatch,
    }),
  );
});

test('downhill-facing original shoes board at the upper comb and leave at the lower comb before crossing the finished slabs', (t) => {
  const { group, machine, route, shoes } = install('down');
  t.after(() => route.dispose());
  const ground = terrain(group, machine),
    railClearance = sideClearance(machine, route.visual);
  const head = route.visual.getObjectByName('Head');
  let mouth;
  head.traverse((o) => {
    if (o.isMesh && o.material.name === 'Warm smile') mouth = o;
  });
  assert.ok(mouth);
  const bodies = [0, 1, 57].map((id) =>
    machine.getObjectByName('STEP_BODY_' + String(id).padStart(2, '0')),
  );
  const comb = Object.fromEntries(
    ['upper', 'lower'].map((k) => [
      k,
      partBounds(machine.getObjectByName('COMB_' + (k === 'upper' ? 'Upper' : 'Lower'))),
    ]),
  );
  const hz = 90,
    frames = Math.ceil(route.duration * hz),
    states = [],
    owners = new Map(),
    observedStations = {};
  const finish = {},
    missing = {},
    combPoints = { upper: 0, lower: 0 },
    combClearance = { upper: Infinity, lower: Infinity },
    dual = { upper: 0, lower: 0 };
  const previous = [null, null],
    routePoints = [],
    phases = [];
  let maxPenetration = 0;
  let maxGap = 0;
  let maxSlide = 0;
  let minSide = Infinity;
  let minFacing = Infinity;
  let minShoeFacing = Infinity;
  let minLaneWidth = Infinity;
  let minHeelTread = Infinity;
  let minToeTread = Infinity;
  let minHeelComb = Infinity;
  let minToeComb = Infinity;
  let centralRiseCount = 0;
  let contactCount = 0;
  let grooveDepth = null;
  let transferProbes = 0;
  let penetrationUnderShoe = 0;
  const transferMargins = { board: Infinity, alight: Infinity };
  const transferWitnesses = {};
  const decks = {
    board: partBounds(machine.getObjectByName('LANDING_Upper')),
    alight: partBounds(machine.getObjectByName('LANDING_Lower')),
  };
  for (let i = 0; i <= frames; i++) {
    const time = (i * route.duration) / frames;
    route.seek(time);
    ground.update();
    const pos = route.visual.getWorldPosition(v());
    if (phases.at(-1) !== route.phase) phases.push(route.phase);
    const feet = shoes.map(sole),
      heading = downhillHeading(route.visual, feet, mouth);
    minFacing = Math.min(minFacing, heading.faceOffset);
    minShoeFacing = Math.min(minShoeFacing, ...heading.soleOffsets);
    minLaneWidth = Math.min(minLaneWidth, heading.footLanes);
    minSide = Math.min(minSide, railClearance());
    const labels = [];
    for (const [j, f] of feet.entries()) {
      const h = ground.probe(f.pole),
        label = h && Math.abs(h.gap) < touch ? h.label : null;
      labels.push(label);
      if (h) maxPenetration = Math.max(maxPenetration, -h.gap);
      if (label) {
        contactCount++;
        owners.set(label, (owners.get(label) || 0) + 1);
        maxGap = Math.max(maxGap, h.gap);
        const local = h.object.worldToLocal(f.pole.clone());
        if (previous[j]?.object === h.object)
          maxSlide = Math.max(maxSlide, local.distanceTo(previous[j].local));
        previous[j] = { object: h.object, local };
      } else previous[j] = null;
      if (route.phase === 'board' || route.phase === 'alight') {
        const duringBoarding = route.phase === 'board';
        const deckLabel = duringBoarding ? 'LANDING_Upper' : 'LANDING_Lower';
        const tread = partBounds(bodies[0]);
        if (label === 'STEP_BODY_00' || label === deckLabel) {
          let lo, hi;
          if (label === 'STEP_BODY_00') {
            lo = Math.max(tread.min.z, comb.upper.max.z);
            hi = Math.min(tread.max.z, comb.lower.min.z);
          } else {
            lo = decks[route.phase].min.z;
            hi = decks[route.phase].max.z;
          }
          const margin = Math.min(f.bounds.min.z - lo, hi - f.bounds.max.z);
          if (margin < transferMargins[route.phase]) {
            transferMargins[route.phase] = margin;
            transferWitnesses[route.phase] = {
              elapsed: time,
              shoe: j === 0 ? 'left' : 'right',
              owner: label,
              end: f.bounds.min.z - lo < hi - f.bounds.max.z ? 'heel' : 'toe',
            };
          }
        }
        // Check the full toe-to-heel extent above central ribs and the adjacent fixed
        // tooth lanes. Raised or rotating neighbouring steps can also be the first hit.
        for (const xMagnitude of [0.1, 0.12, 0.14]) {
          const x = Math.sign(f.pole.x) * xMagnitude;
          for (const fraction of [0.05, 0.25, 0.5, 0.75, 0.95]) {
            const z = MathUtils.lerp(f.bounds.min.z, f.bounds.max.z, fraction);
            const underside = undersideAt(shoes[j], x, z, f.bounds.min.y);
            if (!underside) continue;
            const contact = ground.probe(underside);
            if (!contact) continue;
            transferProbes++;
            penetrationUnderShoe = Math.max(penetrationUnderShoe, -contact.gap);
            if (contact.label === 'COMB_Upper' || contact.label === 'COMB_Lower') {
              const terminal = contact.label === 'COMB_Upper' ? 'upper' : 'lower';
              combPoints[terminal]++;
              combClearance[terminal] = Math.min(combClearance[terminal], contact.gap);
            }
          }
        }
      }
      for (const level of ['upper', 'lower']) {
        if (label === level + ' profile' && !finish[level]) {
          const spans = finishUnderShoe(shoes[j], f, ground);
          finish[level] = {
            labels: [...new Set(spans.map((s) => s.label))].sort(),
            rangeM: Math.max(...spans.map((s) => s.y)) - Math.min(...spans.map((s) => s.y)),
            footprintM: f.bounds.max.z - f.bounds.min.z,
          };
        }
        if (label === level + ' profile' && !missing[level]) {
          const absent = ground.probe(f.pole, label);
          if (!absent || Math.abs(absent.gap) > 0.01) missing[level] = true;
        }
      }
    }
    assert.ok(labels.some(Boolean), 'the passenger lost both supports at ' + time);
    const state = labels.filter(Boolean).sort().join('+');
    if (states.at(-1) !== state) states.push(state);
    if (i === 0 || i === frames)
      observedStations[i === 0 ? 'upper' : 'lower'] = { position: pos.toArray(), labels };
    for (const [tag, surface] of [
      ['upper', 'LANDING_Upper'],
      ['lower', 'LANDING_Lower'],
    ])
      if (labels.includes(surface) && labels.includes('STEP_BODY_00')) dual[tag]++;
    if (route.phase === 'ride') {
      assert.deepEqual(labels, ['STEP_BODY_00', 'STEP_BODY_00']);
      const [tread, ...neighbours] = bodies.map(partBounds),
        level = tread.max.y;
      let exposedHeel = tread.min.z,
        exposedToe = tread.max.z;
      // In the downhill heading the heels face the higher neighbouring stair (−Z).
      for (const n of neighbours)
        if (n.max.y > level + 1e-5) {
          if (n.min.z < tread.min.z) exposedHeel = Math.max(exposedHeel, n.max.z);
          if (n.max.z > tread.max.z) exposedToe = Math.min(exposedToe, n.min.z);
        }
      for (const f of feet) {
        minHeelTread = Math.min(minHeelTread, f.bounds.min.z - exposedHeel);
        minToeTread = Math.min(minToeTread, exposedToe - f.bounds.max.z);
        minHeelComb = Math.min(minHeelComb, f.bounds.min.z - comb.upper.max.z);
        minToeComb = Math.min(minToeComb, comb.lower.min.z - f.bounds.max.z);
      }
      if (!grooveDepth && level > 0.65 && level < 2.35) {
        const shifted = feet[0].pole.clone();
        shifted.x += 0.02;
        grooveDepth = ground.probe(shifted)?.gap;
      }
      if (routePoints.length) {
        const d = pos.clone().sub(routePoints.at(-1));
        assert.ok(d.z > 0 && d.y < 2e-6, 'rider travels uphill');
        if (Math.abs((Math.atan2(-d.y, d.z) * 180) / Math.PI - 30) < 0.05) centralRiseCount++;
      }
      routePoints.push(pos);
    }
  }
  assert.deepEqual(phases, ['approach', 'board', 'ride', 'alight', 'depart']);
  for (const [name, y, z] of [
    ['upper', 3, -6],
    ['lower', 0, 6],
  ]) {
    const station = observedStations[name];
    assert.deepEqual(station.labels, [name + ' tile', name + ' tile']);
    near(station.position[1], y, 2e-6, name + ' slab elevation');
    near(station.position[2], z, 2e-5, name + ' station');
    assert.deepEqual(
      finish[name].labels,
      ['LANDING_' + (name === 'upper' ? 'Upper' : 'Lower'), name + ' profile', name + ' tile'].sort(),
    );
    assert.ok(finish[name].footprintM > 0.3 && finish[name].rangeM < 2e-6 && missing[name]);
    assert.ok(combPoints[name] > 50 && combClearance[name] > 0.005);
    assert.ok(dual[name] >= 2);
  }
  assert.ok(
    [...owners.keys()].every((k) =>
      [
        'upper tile',
        'upper profile',
        'LANDING_Upper',
        'STEP_BODY_00',
        'LANDING_Lower',
        'lower profile',
        'lower tile',
      ].includes(k),
    ),
  );
  assert.ok(minFacing > 0.15 && minShoeFacing > 0.025 && minLaneWidth > 0.23);
  assert.ok(minSide > 0.13 && maxSlide < 0.0002 && maxPenetration < touch && maxGap < touch);
  assert.ok(minHeelTread > 0.018 && minToeTread > 0.018 && minHeelComb > 0 && minToeComb > 0);
  assert.ok(transferProbes > 500 && penetrationUnderShoe < touch);
  for (const phase of ['board', 'alight']) {
    assert.ok(
      transferMargins[phase] > touch,
      'a planted shoe crosses its physical boundary during ' + phase,
    );
  }
  assert.ok(centralRiseCount > 500);
  near(grooveDepth, 0.02, 2e-6, 'offset sole enters an actual groove');
  const byPhase = [
    'upper tile',
    'upper profile',
    'LANDING_Upper',
    'STEP_BODY_00',
    'LANDING_Lower',
    'lower profile',
    'lower tile',
  ];
  const first = byPhase.map((k) => states.findIndex((s) => s.includes(k)));
  assert.ok(
    first.every((v, i) => v >= 0 && (!i || v > first[i - 1])),
    'wrong physical travel order',
  );
  t.diagnostic(
    JSON.stringify({
      frames: frames + 1,
      contactCount,
      owners: Object.fromEntries(owners),
      stations: observedStations,
      dual,
      finish,
      combPoints,
      combClearance,
      minSide,
      minFacing,
      minShoeFacing,
      minLaneWidth,
      maxPenetration,
      maxGap,
      maxSlide,
      minHeelTread,
      minToeTread,
      minHeelComb,
      minToeComb,
      grooveDepth,
      transferMargins,
      transferWitnesses,
      transferProbes,
      penetrationUnderShoe,
    }),
  );
});

test('rewinding the ascent fails the physical downhill-facing shoe and face checks', (t) => {
  const { route, shoes } = install('up');
  t.after(() => route.dispose());
  const midpoint = route.duration / 2;
  route.seek(midpoint + 0.12);
  const before = route.visual.getWorldPosition(v());
  route.seek(midpoint - 0.12);
  const displacement = route.visual.getWorldPosition(v()).sub(before);
  assert.ok(displacement.z > 0 && displacement.y < 0, 'rewinding should move the character downhill');
  let mouth;
  route.visual.getObjectByName('Head').traverse((o) => {
    if (o.isMesh && o.material.name === 'Warm smile') mouth = o;
  });
  const heading = downhillHeading(route.visual, shoes.map(sole), mouth);
  assert.ok(
    heading.faceOffset < -0.15 && heading.soleOffsets.every((n) => n < -0.025) && heading.footLanes < -0.23,
  );
});
