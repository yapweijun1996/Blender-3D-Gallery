import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { readGlb } from '../../../models/mall-floor-tile/glb.mjs';

const load = path => readGlb(fileURLToPath(new URL('../../../models/' + path, import.meta.url)));
const [escalator, slab, landing] = await Promise.all([
  load('escalator/exports/optimized.glb'), load('mall-floor-module-2m/exports/mall-floor-module-2m.glb'),
  load('mall-escalator-landing/exports/optimized.glb'),
]);

const epsilon = 1e-6;
const v = (x, y, z) => new THREE.Vector3(x, y, z);
const round = number => +number.toFixed(8);
const box = object => new THREE.Box3().setFromObject(object, true);
const bounds = object => {
  const b = box(object);
  return { min: b.min.toArray().map(round), max: b.max.toArray().map(round) };
};
const near = (a, b, label) => assert.ok(Math.abs(a - b) < epsilon, label + ': ' + a + ' versus ' + b);
const cast = (objects, origin, direction, distance) =>
  new THREE.Raycaster(origin, direction, 0, distance).intersectObjects(objects, true)[0];
const up = v(0, 1, 0), down = v(0, -1, 0);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

// Divide the stepped section into rectangular cells. Its boundary omits all
// faces between adjacent occupied cells, including those below the cap.
const spec = { width: 2, length: .12, depth: .10, reliefWidth: 1.56, reliefLength: .025, cap: .015 };
function makeSection() {
  const xs = [-spec.width / 2, -spec.reliefWidth / 2, spec.reliefWidth / 2, spec.width / 2];
  const ys = [-spec.depth, -spec.cap, 0];
  const zs = [0, spec.reliefLength, spec.length];
  const occupied = (i, j, k) => i >= 0 && i < 3 && j >= 0 && j < 2 && k >= 0 && k < 2 &&
    !(i === 1 && j === 0 && k === 0);
  const cells = [], vertices = [], triangles = [], vertexIds = new Map();
  const faces = [
    [[-1, 0, 0], [0, 4, 6, 2]], [[1, 0, 0], [1, 3, 7, 5]],
    [[0, -1, 0], [0, 1, 5, 4]], [[0, 1, 0], [2, 6, 7, 3]],
    [[0, 0, -1], [0, 2, 3, 1]], [[0, 0, 1], [4, 5, 7, 6]],
  ];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 2; j++) for (let k = 0; k < 2; k++) {
    if (!occupied(i, j, k)) continue;
    cells.push(new THREE.Box3(v(xs[i], ys[j], zs[k]), v(xs[i + 1], ys[j + 1], zs[k + 1])));
    for (const [[di, dj, dk], corners] of faces) {
      if (occupied(i + di, j + dj, k + dk)) continue;
      const ids = corners.map(n => {
        const coords = [xs[i + (n & 1)], ys[j + ((n >> 1) & 1)], zs[k + (n >> 2)]];
        const key = coords.join(',');
        if (!vertexIds.has(key)) { vertexIds.set(key, vertices.length / 3); vertices.push(...coords); }
        return vertexIds.get(key);
      });
      triangles.push(ids[0], ids[1], ids[2], ids[0], ids[2], ids[3]);
    }
  }
  const edges = new Map();
  for (let i = 0; i < triangles.length; i += 3) {
    for (let j = 0; j < 3; j++) {
      const a = triangles[i + j], b = triangles[i + (j + 1) % 3];
      const key = [Math.min(a, b), Math.max(a, b)].join(',');
      const directions = edges.get(key) || [];
      directions.push(Math.sign(b - a));
      edges.set(key, directions);
    }
  }
  assert.ok([...edges.values()].every(pair => pair.length === 2 && pair[0] === -pair[1]),
    'the study solid has exactly two opposite uses of every boundary edge');
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setIndex(triangles);
  geometry.computeVertexNormals();
  return { mesh: new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ side: THREE.DoubleSide })), cells };
}

const installed = [];
escalator.scene.traverse(object => { if (object.isMesh) installed.push({ name: object.name, box: box(object) }); });
function placeTile(datum, edge, sign, outset) {
  const tile = slab.scene.clone();
  tile.position.set(0, datum - .10, edge + sign * (outset + 1));
  tile.updateMatrixWorld(true);
  return tile;
}
function checkEnd(label, sign) {
  const deck = escalator.scene.getObjectByName('LANDING_' + label);
  const beam = escalator.scene.getObjectByName('TRUSS_End_' + label);
  const connector = escalator.scene.getObjectByName('CONNECT_' + label).getWorldPosition(v());
  const deckBox = box(deck), beamBox = box(beam);
  const datum = deckBox.max.y;
  const edge = sign === 1 ? deckBox.max.z : deckBox.min.z;
  const beamEnd = sign === 1 ? beamBox.max.z : beamBox.min.z;
  const overhang = (beamEnd - edge) * sign;
  near(overhang, .020, 'terminal beam protrusion');
  near(datum - beamBox.max.y, .020, 'terminal beam below finish');
  const world = (x, height, outward) => v(x, datum + height, edge + sign * outward);
  const across = v(0, 0, sign);
  const flush = placeTile(datum, edge, sign, 0);
  const offset = placeTile(datum, edge, sign, overhang);
  const normalSlabOverlaps = [], offsetDrops = [];
  for (const x of [-.73, -.181, .109, .731]) for (const s of [.004, .013, .018]) {
    // Vertical intervals of both original solids, measured at the same X/Z.
    const high = world(x, .06, s), low = world(x, -2.5, s);
    const slabTop = cast([flush], high, down, .20), slabBottom = cast([flush], low, up, 3);
    const beamTop = cast([beam], high, down, .20), beamBottom = cast([beam], low, up, 3);
    assert.ok(slabTop && slabBottom && beamTop && beamBottom);
    const overlap = Math.min(slabTop.point.y, beamTop.point.y) - Math.max(slabBottom.point.y, beamBottom.point.y);
    near(overlap, .080, 'unrelieved slab occupies beam');
    normalSlabOverlaps.push(overlap);
    const gap = cast([deck, beam, offset], high, down, .2);
    assert.equal(gap.object, beam);
    near(datum - gap.point.y, .020, 'shifting the ordinary slab leaves a depressed surface');
    offsetDrops.push(datum - gap.point.y);
  }

  const { mesh: profile, cells } = makeSection();
  profile.position.set(0, datum, edge);
  if (sign < 0) profile.rotation.y = Math.PI;
  profile.updateMatrixWorld(true);
  const tile = placeTile(datum, edge, sign, spec.length);

  // A disjoint world AABB is sufficient to exclude intersection. All boundaries
  // are axis-aligned in both placements. Every occupied profile cell is tested
  // against every original transformed escalator mesh, as well as the native slab.
  const obstacles = [...installed, { name: 'native floor tile', box: box(tile) }];
  let volumePairs = 0;
  for (const cell of cells) for (const other of obstacles) {
    const intersection = cell.clone().applyMatrix4(profile.matrixWorld).intersect(other.box);
    const size = intersection.getSize(v());
    assert.ok(Math.min(size.x, size.y, size.z) <= epsilon,
      'positive volume at ' + label + ' with ' + other.name + ': ' + size.toArray());
    volumePairs++;
  }

  const verticalGaps = [], backGaps = [], sideGaps = [];
  for (const x of [-.74, -.26, .28, .75]) for (const s of [.004, .017]) {
    const origin = world(x, -.017, s);
    const a = cast([profile], origin, up, .02), b = cast([beam], origin, down, .02);
    assert.ok(a && b);
    verticalGaps.push(a.point.y - b.point.y);
  }
  for (const x of [-.74, 0, .74]) {
    const origin = world(x, -.06, .0225);
    const a = cast([profile], origin, across, .02), b = cast([beam], origin, across.clone().negate(), .02);
    assert.ok(a && b);
    backGaps.push(a.distance + b.distance);
  }
  for (const side of [-1, 1]) for (const s of [.004, .017]) {
    const origin = world(side * .7775, -.06, s);
    const a = cast([profile], origin, v(side, 0, 0), .02), b = cast([beam], origin, v(-side, 0, 0), .02);
    assert.ok(a && b);
    sideGaps.push(a.distance + b.distance);
  }
  for (const gap of [...verticalGaps, ...backGaps, ...sideGaps]) near(gap, .005, 'candidate clearance');

  const fromTile = object => {
    for (let current = object; current; current = current.parent) if (current === tile) return true;
    return false;
  };
  let count = 0, heightError = 0;
  for (let i = 0; i <= 30; i++) {
    const x = -.766 + i * 1.532 / 30;
    for (const s of [-.006, -.0015, -.0002, .0002, .006, .019, .026, .070, .1198, .1202, .126]) {
      const expected = s < 0 ? deck : s < spec.length ? profile : tile;
      const top = cast([deck, profile, tile], world(x, .05, s), down, .10);
      assert.ok(top && (expected === tile ? fromTile(top.object) : top.object === expected), 'missing or incorrect wearing surface across the join');
      const error = Math.abs(top.point.y - datum);
      // The original landing deck has a 1 mm eased edge.
      assert.ok(error <= .001001);
      heightError = Math.max(heightError, error);
      count++;
    }
  }
  // The far edge must meet the whole 2 m slab, including the parts beyond
  // the ends of the 1.55 m escalator deck. The inner side has no deck there.
  for (const x of [-.995, -.91, -.81, .81, .91, .995]) {
    const inside = cast([deck], world(x, .05, -.003), down, .10);
    const cap = cast([profile], world(x, .05, .1198), down, .10);
    const paver = cast([tile], world(x, .05, .1202), down, .10);
    assert.ok(!inside && cap && paver);
    near(cap.point.y, paver.point.y, 'whole-width connection to the native slab');
  }
  return { terminal: label, nativeDeck: bounds(deck), nativeBeam: bounds(beam),
    deckOuterEdgeZ: round(edge), deckHeight: round(datum), outwardZSign: sign,
    connector: connector.toArray().map(round), connectorInsetFromOuterEdge: round(Math.abs(connector.z - edge)),
    profileRoot: profile.position.toArray().map(round), profileYawDegrees: sign > 0 ? 0 : 180,
    originalSlabRoot: tile.position.toArray().map(round), returnedSurfaces: count,
    maxOriginalFinishRelief: round(heightError), positiveVolumePairsBeyondTolerance: 0,
    testedNativeBoundingBoxPairs: volumePairs, sampledSideClearance: round(Math.min(...sideGaps)),
    sampledBackClearance: round(Math.min(...backGaps)), sampledVerticalClearance: round(Math.min(...verticalGaps)),
    flushOrdinarySlab: { insideBeamWitnesses: normalSlabOverlaps.length, minVerticalOverlap: round(Math.min(...normalSlabOverlaps)) },
    offsetOrdinarySlab: { shift: round(overhang), depressedSurfaceWitnesses: offsetDrops.length,
      depression: round(Math.min(...offsetDrops)) } };
}

function check429Threshold() {
  const legacy = landing.scene.clone();
  legacy.position.y = -.03;
  legacy.updateMatrixWorld(true);
  const tile = placeTile(0, .6, 1, 0);
  let pairs = 0;
  for (const x of [-.45, 0, .45]) for (const delta of [.0005, .003]) {
    const a = cast([legacy], v(x, .04, .6 - delta), down, .08);
    const b = cast([tile], v(x, .04, .6 + delta), down, .08);
    assert.equal(a?.object.name, 'MODULE_FloorThreshold');
    assert.ok(b);
    near(a.point.y, b.point.y, '429 floor-side top next to a native slab');
    pairs++;
  }
  return { legacyRoot: [0, -.03, 0], nativeSlabRoot: [0, -.10, 1.6], pairs, centredWidthDifferencePerSide: .40,
    scope: '429 public-floor threshold only. Its separate comb has not been substituted for the built-in comb of 004.' };
}

const report = {
  units: 'metres', axes: 'glTF +Y up. Profile local +Z points away from the escalator.',
  scope: 'Static default-pose geometry, fit and clearances. No passenger, structural or hardware claim.',
  inputs: [escalator, slab, landing].map(a => ({ root: a.scene.children[0].name, sha256: hash(a.bytes), localBox: bounds(a.scene) })),
  section: spec, chosenMargins: '5 mm each side, behind and above the exposed 004 terminal beam.',
  independent429Threshold: check429Threshold(), terminals: [checkEnd('Lower', 1), checkEnd('Upper', -1)],
};
process.stdout.write(JSON.stringify(report, null, 2) + '\n');
