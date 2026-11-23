import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { validateBytes } from 'gltf-validator';
import { Box3, Raycaster, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { placeShellModule, shellAssetPaths, shellLayout } from './shell-layout.js';

const root = new URL('../', import.meta.url);
const inputs = await Promise.all(Object.entries(shellAssetPaths).map(async ([id, path]) => {
  const { scene, bytes } = await readGlb(fileURLToPath(new URL(path, root)));
  const { issues } = await validateBytes(bytes, { uri: path });
  assert.equal(issues.numErrors, 0, `${id} glTF errors`);
  assert.equal(issues.numWarnings, 0, `${id} glTF warnings`);
  return {
    id, path, scene,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    validator: { errors: issues.numErrors, warnings: issues.numWarnings },
  };
}));
const sources = Object.fromEntries(inputs.map(({ id, scene }) => [id, scene]));
const tolerance = 1e-6; // One micrometre, above the GLB float rounding in this scene.
const probeOffset = .002;
const down = new Vector3(0, -1, 0);
const up = new Vector3(0, 1, 0);
const mm = metres => Number((metres * 1000).toFixed(6)) || 0;
const maxGapMm = gaps => mm(Math.max(...gaps.map(Math.abs)));

function near(actual, expected, label) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${label}: ${actual} m, expected ${expected} m`);
}

function place(placement) {
  const object = placeShellModule(sources, placement);
  object.updateMatrixWorld(true);
  return { ...placement, object, bounds: new Box3().setFromObject(object, true) };
}

function component(part, name) {
  const object = part.object.getObjectByName(name);
  assert.ok(object, `${part.id} missing ${name}`);
  return { ...part, object, bounds: new Box3().setFromObject(object, true) };
}

function checkJoin(lower, upper, axis, label) {
  const gap = upper.bounds.min[axis] - lower.bounds.max[axis];
  near(gap, 0, label);
  const cross = axis === 'x' ? 'z' : 'x';
  const overlap = Math.min(lower.bounds.max[cross], upper.bounds.max[cross]) -
    Math.max(lower.bounds.min[cross], upper.bounds.min[cross]);
  assert.ok(overlap > tolerance, `${label}: modules do not meet across the join`);
  return gap;
}

function ray(parts, origin, direction) {
  return new Raycaster(new Vector3(...origin), direction).intersectObjects(parts, true)[0];
}

function surface(part, origin, direction) {
  const hit = ray([part.object], origin, direction);
  assert.ok(hit, `${part.id} has no surface from (${origin.join(', ')})`);
  return hit;
}

const floor = shellLayout.floor.map(place);
const trim = shellLayout.trim.map(place);
const walls = shellLayout.walls.map(place);
const ceiling = shellLayout.ceiling.map(place);
assert.equal(floor.length, 35);
assert.equal(trim.length, 11);
assert.equal(walls.length, 10);
assert.equal(ceiling.length, 14);
for (const part of [...floor, ...trim]) near(part.bounds.max.y, 0, `${part.id} top Y`);
for (const part of walls) {
  near(part.bounds.min.y, 0, `${part.id} base Y`);
  near(part.bounds.max.y, 3, `${part.id} top Y`);
}

const floorGaps = [];
const floorHeights = [];
for (const [axis, cross] of [['x', 'z'], ['z', 'x']]) {
  for (const row of new Set(floor.map(part => part[cross]))) {
    const line = floor.filter(part => part[cross] === row).sort((a, b) => a[axis] - b[axis]);
    for (const [i, upper] of line.slice(1).entries()) {
      const lower = line[i];
      const seam = (lower.bounds.max[axis] + upper.bounds.min[axis]) / 2;
      const label = `floor ${axis.toUpperCase()} join at ${seam}, ${cross}=${row}`;
      floorGaps.push(checkJoin(lower, upper, axis, label));
      for (const across of [-.3, 0, .3]) {
        const heights = [lower, upper].map((part, index) => {
          const point = { y: 1, [axis]: seam + (index === 0 ? -probeOffset : probeOffset), [cross]: row + across };
          return surface(part, [point.x, point.y, point.z], down).point.y;
        });
        // The authored grout sits 1 mm below the stone tops.
        assert.ok(heights.every(y => y >= -.001 - tolerance && y <= tolerance), `${label}: floor surface height`);
        near(heights[1], heights[0], `${label}: height step`);
        floorHeights.push(...heights);
      }
    }
  }
}
assert.equal(floorGaps.length, 58);

const cornerTile = floor.find(part => part.id === 'cornerTile');
const mitre = trim.find(part => part.id === 'mitredTrim');
const frontEnd = trim.filter(part => part.id === 'floorEdge' && part.yaw === undefined).at(-1);
const rightEnd = trim.filter(part => part.id === 'floorEdge' && part.yaw !== undefined).at(-1);
const trimGaps = {
  frontStraightMm: mm(checkJoin(frontEnd, mitre, 'x', 'front straight to mitred trim')),
  rightStraightMm: mm(checkJoin(rightEnd, mitre, 'z', 'right straight to mitred trim')),
  frontTileMm: mm(checkJoin(cornerTile, component(mitre, 'Front_cap'), 'z', 'corner tile to front mitre cap')),
  rightTileMm: mm(checkJoin(cornerTile, component(mitre, 'Right_cap'), 'x', 'corner tile to right mitre cap')),
};
for (const [straight, axis, cross] of [[frontEnd, 'x', 'z'], [rightEnd, 'z', 'x']]) {
  const seam = (straight.bounds.max[axis] + mitre.bounds.min[axis]) / 2;
  for (const [part, offset] of [[straight, -probeOffset], [mitre, probeOffset]]) {
    const point = { [axis]: seam + offset, [cross]: straight[cross] };
    near(surface(part, [point.x, 1, point.z], down).point.y, 0, `${axis} trim end top Y`);
  }
}
const diagonal = [[.61, .64, 'Front_cap'], [.64, .61, 'Right_cap'], [.59, .63, 'Front_cap'], [.63, .59, 'Right_cap']];
for (const [x, z, name] of diagonal) {
  const hit = surface(mitre, [mitre.x + x, 1, mitre.z + z], down);
  assert.equal(hit.object.name, name, 'mitred trim diagonal profile');
  near(hit.point.y, 0, `${name} top Y`);
}
for (const [x, z] of [[.59, .3], [.3, .59]]) {
  near(surface(cornerTile, [cornerTile.x + x, 1, cornerTile.z + z], down).point.y, 0, 'corner tile inlay top Y');
}

const rear = walls.filter(part => part.id === 'wall' && part.yaw === undefined);
const right = walls.filter(part => part.id === 'wall' && part.yaw !== undefined);
const wallCorner = walls.find(part => part.id === 'wallCorner');
const rearArm = component(wallCorner, 'ARM_X_Core');
const rightArm = component(wallCorner, 'ARM_Y_Core');
const rearGaps = rear.slice(1).map((part, index) => checkJoin(rear[index], part, 'x', `rear wall join ${index + 1}`));
const rightGaps = right.slice(1).map((part, index) => checkJoin(right[index], part, 'z', `right wall join ${index + 1}`));
const rearCornerGap = checkJoin(rear.at(-1), rearArm, 'x', 'rear straight to wall corner');
const rightCornerGap = checkJoin(rightArm, right[0], 'z', 'wall corner to right straight');
assert.equal(rearGaps.length, 5);
assert.equal(rightGaps.length, 2);

function innerFaceSamples(lower, upper, axis) {
  const seam = (lower.bounds.max[axis] + upper.bounds.min[axis]) / 2;
  const rearFace = axis === 'x';
  const direction = rearFace ? new Vector3(0, 0, -1) : new Vector3(1, 0, 0);
  const cross = rearFace ? 'z' : 'x';
  // Mate registration is separate from the visible interior profile and finishes.
  return [probeOffset, .05].flatMap(offset => [.15, 1.5, 2.85].map(y => {
    const hits = [lower, upper].map((part, index) => {
      const edge = seam + (index === 0 ? -offset : offset);
      return surface(part, rearFace ? [edge, y, -2] : [3.8, y, edge], direction);
    });
    const step = hits[1].point[cross] - hits[0].point[cross];
    return {
      offsetMm: mm(offset), yM: y,
      faces: hits.map(hit => ({ mesh: hit.object.name, [`${cross}Mm`]: mm(hit.point[cross]) })),
      signedStepMm: mm(step),
      flush: Math.abs(step) <= tolerance,
    };
  }));
}
function checkInnerFinish(end, samples) {
  assert.ok(samples.every(sample => sample.flush), 'wall corner ' + end + ' interior faces are offset');
  const panelSample = samples.find(sample => sample.offsetMm === 50 && sample.yM === 1.5);
  assert.ok(panelSample.faces.every(({ mesh }) => /panel/i.test(mesh)), 'wall corner ' + end + ' needs two finished faces');
}

const rearFinish = innerFaceSamples(rear.at(-1), wallCorner, 'x');
const rightFinish = innerFaceSamples(wallCorner, right[0], 'z');
checkInnerFinish('rear', rearFinish);
checkInnerFinish('right', rightFinish);

const previousRightWall = place({ ...right[0], yaw: Math.PI / 2 });
const previousRightGap = checkJoin(rightArm, previousRightWall, 'z', 'previous right wall mating plane');
const previousRightFinish = innerFaceSamples(wallCorner, previousRightWall, 'z');
assert.throws(() => checkInnerFinish('previous right', previousRightFinish), /interior faces are offset/);
const previousRightMaxStepMm = Math.max(...previousRightFinish.map(({ signedStepMm }) => Math.abs(signedStepMm)));
assert.ok(Math.abs(previousRightMaxStepMm - 10) <= mm(tolerance), 'old outward wall should reproduce the 10 mm interior step');
assert.equal(previousRightFinish.find(sample => sample.offsetMm === 50 && sample.yM === 1.5).faces[1].mesh, 'WALL_Core');

const roofParts = ceiling.map(({ object }) => object);
const roofContacts = [[rear[0], -3.6, -2.96], [rear.at(-1), 2.4, -2.96], [wallCorner, 4.19, -2.96], [right[0], 4.19, -1.14]];
const contactSamples = roofContacts.map(([wall, x, z]) => {
  const top = surface(wall, [x, 3.5, z], down);
  const underside = ray(roofParts, [x, 2.8, z], up);
  assert.ok(underside?.object.name.startsWith('GRID_'), `ceiling grid missing at (${x}, ${z})`);
  const gap = underside.point.y - top.point.y;
  near(top.point.y, 3, 'wall top at ceiling contact');
  near(gap, 0, 'ceiling grid to wall top');
  return { xM: x, zM: z, wallMesh: top.object.name, ceilingMesh: underside.object.name, signedGapMm: mm(gap) };
});
const roofOpenings = [-2.4, 0, 2.4].map(x => [x - .3, 2.8, -.9]);
for (const origin of [...roofOpenings, [0, 2.8, 0]]) {
  assert.equal(ray(roofParts, origin, up), undefined, `ceiling opening blocked at (${origin.join(', ')})`);
}
const recessedPanel = ray(roofParts, [-2.1, 2.8, -.9], up);
assert.ok(recessedPanel, 'panel adjacent to light opening missing');
near(recessedPanel.point.y, 3.008, 'ceiling panel underside');

const lower = floor[0];
const upper = floor.find(part => part.x === -2.4 && part.z === lower.z);
const shifted = place({ ...upper, x: upper.x + .02 });
assert.throws(() => checkJoin(lower, shifted, 'x', 'offset floor seam'), /offset floor seam/);

console.log(JSON.stringify({
  verified: true,
  toleranceMm: mm(tolerance),
  inputs: inputs.map(({ scene, ...input }) => input),
  floor: {
    modules: floor.length, joins: floorGaps.length, topYmm: 0,
    maxAbsoluteGapMm: maxGapMm(floorGaps),
    surfaceRays: floorHeights.length,
    edgeSampleYMm: [mm(Math.min(...floorHeights)), mm(Math.max(...floorHeights))],
  },
  trim: { ...trimGaps, topYmm: 0, endSurfaceRays: 4, diagonalSurfaceRays: diagonal.length, cornerInlaySurfaceRays: 2 },
  walls: {
    rearStraightJoins: rearGaps.length, rearMaxAbsoluteGapMm: maxGapMm(rearGaps),
    rightStraightJoins: rightGaps.length, rightMaxAbsoluteGapMm: maxGapMm(rightGaps),
    rearCornerSignedGapMm: mm(rearCornerGap), rightCornerSignedGapMm: mm(rightCornerGap),
    cornerInnerFaces: { rear: rearFinish, right: rightFinish },
  },
  ceiling: { modules: ceiling.length, contactSamples, lightPanelOpenings: roofOpenings.length, cutawaySample: 'open', adjacentPanelYMm: mm(recessedPanel.point.y) },
  controls: {
    floorOffset: { rejected: true, translationMm: 20, signedGapMm: mm(shifted.bounds.min.x - lower.bounds.max.x) },
    outwardRightWall: {
      rejectedByFinishProbes: true, yawDegrees: 90, signedMatingGapMm: mm(previousRightGap),
      maxAbsoluteInnerFaceStepMm: previousRightMaxStepMm, samples: previousRightFinish,
    },
  },
  limits: 'Signed bounds and fixed surface samples of the current 1.2 m cutaway. Fixture geometry, full triangle intersections, collision, device rendering and physical tolerances are outside this check.',
}, null, 2));
