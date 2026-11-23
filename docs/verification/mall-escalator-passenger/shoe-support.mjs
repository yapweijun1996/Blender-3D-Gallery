import assert from 'node:assert/strict';
import { AnimationMixer, Box3, Quaternion, Raycaster, Triangle, Vector3 } from 'three';

const v = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const bounds = (object) => new Box3().setFromObject(object, true);
const range = (list) => [list[0], list.at(-1)];

function shoeFootprint(visitor) {
  const avatar = visitor.scene.clone(true);
  avatar.rotation.y = Math.PI;
  const idle = visitor.animations.find((clip) => clip.name === 'idle');
  const mixer = new AnimationMixer(avatar);
  mixer.clipAction(idle).play();
  const shoes = ['LeftFoot', 'RightFoot'].map((name) => avatar.getObjectByName(name));
  const solePoles = [],
    combined = new Box3();
  let drift = 0;
  // Measure the lowest actual shoe vertex, alongside each shoe's full longitudinal envelope.
  const reference = [];
  for (let frame = 0; frame <= 120; frame++) {
    mixer.setTime((idle.duration * frame) / 120);
    avatar.updateMatrixWorld(true);
    shoes.forEach((shoe, index) => {
      const box = new Box3(),
        lowest = v(0, Infinity, 0),
        point = v();
      shoe.traverse((mesh) => {
        if (!mesh.isMesh) return;
        for (let i = 0; i < mesh.geometry.attributes.position.count; i++) {
          mesh.getVertexPosition(i, point).applyMatrix4(mesh.matrixWorld);
          box.expandByPoint(point);
          if (point.y < lowest.y) lowest.copy(point);
        }
      });
      if (frame === 0) {
        reference.push(box.clone());
        solePoles.push(lowest.clone());
      }
      drift = Math.max(
        drift,
        lowest.distanceTo(solePoles[index]),
        reference[index].min.distanceTo(box.min),
        reference[index].max.distanceTo(box.max),
      );
      combined.union(box);
    });
  }
  assert.ok(drift < 1e-6);
  mixer.stopAllAction();
  mixer.uncacheRoot(avatar);
  return { combined, solePoles, drift };
}

function treadInPivotSpace(body, pivot) {
  const inverse = pivot.matrixWorld.clone().invert();
  const box = new Box3(),
    triangles = [];
  body.traverse((mesh) => {
    if (!mesh.isMesh) return;
    const geometry = mesh.geometry,
      position = geometry.attributes.position;
    const points = Array.from({ length: position.count }, (_, i) => {
      const point = mesh.getVertexPosition(i, v()).applyMatrix4(mesh.matrixWorld).applyMatrix4(inverse);
      box.expandByPoint(point);
      return point;
    });
    for (let start = 0; start < (geometry.index?.count ?? points.length); start += 3) {
      triangles.push(
        [0, 1, 2].map((k) => points[geometry.index ? geometry.index.getX(start + k) : start + k]),
      );
    }
  });
  const spans = [];
  for (const triangle of triangles) {
    if (
      triangle.every((p) => Math.abs(p.y - box.max.y) < 1e-6) &&
      new Triangle(...triangle).getNormal(v()).y > 0.999
    ) {
      spans.push([Math.min(...triangle.map((p) => p.x)), Math.max(...triangle.map((p) => p.x))]);
    }
  }
  spans.sort((a, b) => a[0] - b[0]);
  const crests = spans.filter((span, i) => !i || span[0] - spans[i - 1][0] > 1e-6);
  assert.equal(crests.length, 25);
  return { box, crests };
}

export function checkShoeSupport(machine, visitor) {
  const { scene, animations } = machine,
    mixer = new AnimationMixer(scene);
  const get = (name) => scene.getObjectByName(name);
  for (const clip of animations) mixer.clipAction(clip).play();
  const step = get('STEP_00'),
    body = get('STEP_BODY_00'),
    ahead = get('STEP_01');
  const period = animations.find((clip) => clip.name === 'StepCirculation_STEP_00').duration;
  const sampleHz = 120,
    rootOffsetZ = 0.24;
  const publicRideSeconds = [0.3, 18.1];
  mixer.setTime(0);
  scene.updateMatrixWorld(true);
  const { box, crests } = treadInPivotSpace(body, step);
  const aheadBox = treadInPivotSpace(get('STEP_BODY_01'), ahead).box;
  const shoes = shoeFootprint(visitor);
  const lowerComb = bounds(get('COMB_Lower')),
    upperComb = bounds(get('COMB_Upper'));
  const surfaces = [
    body,
    get('STEP_BODY_01'),
    get('STEP_BODY_57'),
    get('COMB_Lower'),
    get('COMB_Upper'),
    get('LANDING_Lower'),
    get('LANDING_Upper'),
  ];
  const ray = new Raycaster(),
    down = v(0, -1, 0);
  function probe(targets, x, y, z) {
    ray.set(v(x, y + 0.32, z), down);
    return ray.intersectObjects(targets, true)[0];
  }
  const riderBounds = shoes.combined,
    frames = [],
    lower = [],
    upper = [];
  let toeMargin = Infinity,
    heelMargin = Infinity,
    combMargin = Infinity,
    soleError = 0,
    minimumRibMargin = Infinity;
  let publicCombMargin = Infinity,
    centredStanceOverlaps = 0;
  for (let frame = 0; frame < Math.floor(period * sampleHz); frame++) {
    const t = frame / sampleHz;
    mixer.setTime(t);
    scene.updateMatrixWorld(true);
    if (step.quaternion.angleTo(new Quaternion()) > 1e-5) continue;
    const pivot = step.getWorldPosition(v()),
      y = pivot.y + box.max.y;
    if (y < -0.000002 || y > 3.000002) continue;
    const ownFront = pivot.z + box.min.z,
      ownBack = pivot.z + box.max.z;
    const next = aheadBox.clone().applyMatrix4(ahead.matrixWorld);
    const exposedFront = next.max.y > y + 1e-5 ? Math.max(ownFront, next.max.z) : ownFront;
    const rootZ = pivot.z + rootOffsetZ,
      toe = rootZ + riderBounds.min.z,
      heel = rootZ + riderBounds.max.z;
    if (toe < Math.max(exposedFront, upperComb.max.z) || heel > Math.min(ownBack, lowerComb.min.z)) continue;
    frames.push(frame);
    if (Math.abs(y) < 1e-6) lower.push(t);
    if (Math.abs(y - 3) < 1e-6) upper.push(t);
    toeMargin = Math.min(toeMargin, toe - exposedFront);
    heelMargin = Math.min(heelMargin, ownBack - heel);
    const fixedCombClearance = Math.min(toe - upperComb.max.z, lowerComb.min.z - heel);
    combMargin = Math.min(combMargin, fixedCombClearance);
    if (t >= publicRideSeconds[0] && t <= publicRideSeconds[1])
      publicCombMargin = Math.min(publicCombMargin, fixedCombClearance);
    for (const pole of shoes.solePoles) {
      const hit = probe(surfaces, pole.x, y, rootZ + pole.z);
      assert.ok(hit && body.getObjectById(hit.object.id), 'another surface covers a planted sole');
      soleError = Math.max(soleError, Math.abs(hit.point.y - (y + pole.y)));
      const rib = crests.find(([left, right]) => left <= pole.x && pole.x <= right);
      assert.ok(rib);
      minimumRibMargin = Math.min(minimumRibMargin, pole.x - rib[0], rib[1] - pole.x);
    }
    const centredToe = (ownFront + ownBack - riderBounds.max.z + riderBounds.min.z) / 2;
    if (centredToe < exposedFront - 1e-6) centredStanceOverlaps++;
  }
  assert.equal(frames.length, 2184);
  assert.ok(frames.every((n, i) => !i || n === frames[i - 1] + 1));
  assert.ok(toeMargin > 0.02 && heelMargin > 0.02 && minimumRibMargin > 0.008 && soleError < 1e-6);
  assert.ok(centredStanceOverlaps > 100);
  assert.ok(lower[0] <= publicRideSeconds[0] && lower.at(-1) >= publicRideSeconds[0]);
  assert.ok(upper[0] <= publicRideSeconds[1] && upper.at(-1) >= publicRideSeconds[1]);
  assert.ok(publicCombMargin > combMargin);
  mixer.setTime(8);
  scene.updateMatrixWorld(true);
  const pivot = step.getWorldPosition(v()),
    top = pivot.y + box.max.y;
  const shiftedDrops = shoes.solePoles.map(
    (p) => top - probe([body], p.x + 0.02, top, pivot.z + rootOffsetZ + p.z).point.y,
  );
  assert.ok(shiftedDrops.every((drop) => Math.abs(drop - 0.02) < 1e-5));
  mixer.setTime(30);
  scene.updateMatrixWorld(true);
  const returnAngle = step.quaternion.angleTo(new Quaternion());
  assert.ok(returnAngle > 3);
  mixer.stopAllAction();
  mixer.uncacheRoot(scene);
  return {
    sampleHz,
    period,
    consecutiveSamples: frames.length,
    soleRays: frames.length * 2,
    supportedSeconds: range(frames).map((n) => n / sampleHz),
    lowerFlatSeconds: range(lower),
    upperFlatSeconds: range(upper),
    publicRideSeconds,
    stanceInStep: [0, box.max.y, rootOffsetZ],
    shoeWidth: riderBounds.max.x - riderBounds.min.x,
    shoeDepth: riderBounds.max.z - riderBounds.min.z,
    maxIdleShoeDrift: shoes.drift,
    ribs: crests.length,
    ribWidth: crests[0][1] - crests[0][0],
    ribGap: crests[1][0] - crests[0][1],
    toeMargin,
    heelMargin,
    combMargin,
    publicCombMargin,
    outsideRibMargin: Math.min(riderBounds.min.x - crests[0][0], crests.at(-1)[1] - riderBounds.max.x),
    minimumRibMargin,
    soleError,
    centredStanceOverlaps,
    shiftedDrops,
    returnAngle,
  };
}
