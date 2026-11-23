import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Group, Matrix3, Raycaster, Vector2, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { assembleCeilingInfill, ceilingInfillPaths } from '../mall-modules-preview/ceiling-infill.js';
import { walk } from './helpers/mall-mesh.mjs';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

const columns = [-2.4, -1.2, 0, 1.2, 2.4];
const height = 2.8;
const up = new Vector3(0, 1, 0), down = new Vector3(0, -1, 0);
const load = async path => (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
const sources = Object.fromEntries(await Promise.all(Object.entries(ceilingInfillPaths).map(async ([id, path]) => [id, await load(path)])));
const original = sources.ceiling;
const bay = assembleCeilingInfill(sources);
bay.updateMatrixWorld(true);
const roof = bay.getObjectByName('Ceiling cassettes');
const walls = bay.children.filter(part => part.userData.moduleId === 'wall2m');
const row = id => roof.children.filter(part => part.userData.moduleId === id).sort((a, b) => a.position.x - b.position.x);
const full = row('ceiling'), infill = row('ceilingInfill');

function near(actual, expected, label, tolerance = 1e-6) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < tolerance, `${label}: ${actual} vs ${expected}`);
}

function hit(parts, x, y, z, direction) {
  return new Raycaster(new Vector3(x, y, z), direction).intersectObjects(parts, true)[0];
}

function underside(parts, x, z) {
  return hit(parts, x, height - .25, z, up);
}

test('original-only cassette rows leave 800 mm uncovered or overhang the 2 m bay by 400 mm', () => {
  const row = new Group();
  for (const x of columns) {
    const cassette = original.clone(true);
    cassette.position.set(x, height, -.4);
    row.add(cassette);
  }
  row.updateMatrixWorld(true);
  const one = new Box3().setFromObject(row, true);
  near(1 - one.max.z, .8, 'single-row gap');
  for (const x of columns.map(x => x + .27)) {
    assert.ok(underside([row], x, .199));
    for (const z of [.203, .5, .79, .994]) assert.equal(underside([row], x, z), undefined);
  }
  const second = row.clone(true);
  second.position.z = 1.2;
  second.updateMatrixWorld(true);
  const two = new Box3().setFromObject(second, true);
  near(two.max.z - 1, .4, 'two-row overhang');
  for (const x of columns.map(x => x + .27)) {
    assert.ok(underside([second], x, 1.39));
    assert.equal(underside([second], x, 1.401), undefined);
  }
});

const cross = (a, b, c) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);

// Extract actual roof undersides and wall heads. In the XZ projection a clockwise face points up.
function contactFaces(parts, facingDown) {
  const faces = [];
  for (const part of parts) part.traverse(mesh => {
    if (!mesh.isMesh) return;
    const pos = mesh.geometry.getAttribute('position'), indices = mesh.geometry.index;
    for (let i = 0; i < (indices?.count ?? pos.count); i += 3) {
      const t = [i, i + 1, i + 2].map(j => new Vector3()
        .fromBufferAttribute(pos, indices ? indices.getX(j) : j).applyMatrix4(mesh.matrixWorld));
      if (!t.every(p => Math.abs(p.y - height) < 1e-6)) continue;
      const points = t.map(p => new Vector2(p.x, p.z));
      const area = cross(...points);
      if (facingDown ? area > 0 : area < 0) faces.push(facingDown ? points : points.reverse());
    }
  });
  return faces;
}

// Both triangles wind counterclockwise here. Clip to their actual common polygon and integrate its area.
function commonArea(points, triangle) {
  for (let i = 0; i < 3 && points.length; i++) {
    const a = triangle[i], b = triangle[(i + 1) % 3], clipped = [];
    let last = points.at(-1), before = cross(a, b, last);
    for (const point of points) {
      const after = cross(a, b, point);
      if ((before >= 0) !== (after >= 0)) clipped.push(last.clone().lerp(point, before / (before - after)));
      if (after >= 0) clipped.push(point);
      last = point;
      before = after;
    }
    points = clipped;
  }
  let area = 0;
  for (let i = 2; i < points.length; i++) area += cross(points[0], points[i - 1], points[i]) / 2;
  return area;
}

test('unscaled roof closes the actual floor and bears on both inward-facing wall runs', t => {
  assert.equal(walls.length, 6);
  const floors = bay.children.filter(p => p.userData.moduleId === 'floor2m').sort((a, b) => a.position.x - b.position.x);
  assert.deepEqual(floors.map(p => p.position.toArray()), [-2, 0, 2].map(x => [x, -.1, 0]));
  const outline = new Box3().setFromObject(roof, true);
  for (const [actual, expected] of [[outline.min.x, -3], [outline.max.x, 3], [outline.min.z, -1],
    [outline.max.z, 1], [outline.min.y, height], [outline.max.y, height + .36]]) near(actual, expected, 'roof vertex extent');
  for (const [parts, z] of [[full, -.4], [infill, .6]]) {
    assert.deepEqual(parts.map(p => p.position.toArray()), columns.map(x => [x, height, z]));
    for (const part of parts) assert.deepEqual(part.scale.toArray(), [1, 1, 1]);
  }
  let totalArea = 0;
  for (const sign of [-1, 1]) {
    const rowWalls = walls.filter(p => Math.sign(p.position.z) === sign).sort((a, b) => a.position.x - b.position.x);
    assert.deepEqual(rowWalls.map(p => p.position.toArray()), [-2, 0, 2].map(x => [x, 0, .925 * sign]));
    const facing = hit(rowWalls, .27, 1.7, 0, new Vector3(0, 0, sign));
    assert.match(facing.object.material.name, /limestone/i);
    near(Math.abs(facing.point.z), .853, 'aisle-facing finish');
    const grid = contactFaces(sign < 0 ? full : infill, true);
    for (const [i, wall] of rowWalls.entries()) {
      const head = contactFaces([wall], false);
      const area = grid.reduce((sum, rail) => sum + head.reduce((n, face) => n + commonArea(rail, face), 0), 0);
      // 2 m of 12 mm boundary flange plus cross-rail flanges across the remaining 138 mm wall depth.
      const crossRailWidth = i === 1 ? .072 : .084;
      near(area, 2 * .012 + crossRailWidth * .138, `coplanar bearing on ${wall.name}`);
      totalArea += area;
    }
    for (const x of columns.map(x => x + .23)) {
      assert.equal(underside([roof], x, sign * 1.001), undefined);
      const z = sign * .994;
      near(underside([roof], x, z).point.y, hit(rowWalls, x, 2.9, z, down).point.y, 'edge flange to wall');
    }
  }
  for (const sign of [-1, 1]) for (const z of [-.7, .3, .9]) {
    assert.equal(underside([roof], sign * 3.001, z), undefined);
  }
  t.diagnostic(`Actual coplanar bearing on six wall heads: ${totalArea.toFixed(6)} m²`);
});

function expectSurface(parts, x, z, direction, level, material) {
  const start = height + (direction.y > 0 ? -.05 : .05);
  const surface = hit(parts, x, start, z, direction);
  assert.ok(surface, `missing surface at ${x},${z}`);
  near(surface.point.y - height, level, 'actual section level');
  assert.match(surface.object.material.name, material);
}

function capPair(first, second, axis, x, y, z) {
  const seam = new Vector3(x, y, z);
  for (const [part, sign] of [[first, 1], [second, -1]]) {
    const outward = new Vector3();
    outward[axis] = sign;
    const probe = seam.clone().addScaledVector(outward, .025);
    const face = hit([part], probe.x, probe.y, probe.z, outward.clone().negate());
    assert.ok(face, `missing native end face at ${seam.toArray()}`);
    near(face.point.distanceTo(seam), 0, 'opposing rail cap location');
    const normal = face.face.normal.clone().applyNormalMatrix(new Matrix3().getNormalMatrix(face.object.matrixWorld));
    near(normal.dot(outward), 1, 'cap points out of its own cassette');
  }
}

test('mixed and end-to-end seams retain two 12 mm flanges and two distinct 3 mm webs', () => {
  // The two original half rails place their web centres 6 mm to each side of a join.
  function pairProfile(parts, point) {
    for (const sign of [-1, 1]) {
      for (const [offset, top] of [[.002, .004], [.0044, .004], [.0046, .032], [.0074, .032], [.0076, .004], [.0118, .004]]) {
        const [x, z] = point(sign * offset);
        expectSurface(parts, x, z, up, 0, /grid/i);
        expectSurface(parts, x, z, down, top, /grid/i);
      }
      const [x, z] = point(sign * .014);
      expectSurface(parts, x, z, up, .008, /fibre/i);
    }
  }
  for (let i = 0; i < columns.length; i++) {
    const x = columns[i] + .24;
    pairProfile([full[i], infill[i]], offset => [x, .2 + offset]);
    capPair(full[i], infill[i], 'z', x, height + .002, .2);
  }
  for (const [parts, z, longitudinalWeb] of [[full, -.7, -.4], [infill, .49, .8], [infill, .90, .994]]) {
    for (let i = 1; i < parts.length; i++) {
      const x = columns[i] - .6;
      pairProfile([parts[i - 1], parts[i]], offset => [x + offset, z]);
      capPair(parts[i - 1], parts[i], 'x', x, height + .002, z);
      capPair(parts[i - 1], parts[i], 'x', x, height + .018, longitudinalWeb);
    }
  }
});

test('the 800 mm field retains a 600 mm pitch and a shortened final panel under a single native tee', () => {
  for (const part of infill) for (const dx of [-.29, .29]) {
    const x = part.position.x + dx;
    for (const z of [.214, .45, .786, .814, .9, .986]) expectSurface([part], x, z, up, .008, /fibre/i);
    for (const z of [.789, .800, .811, .989, .999]) expectSurface([part], x, z, up, 0, /grid/i);
    for (const [dz, top] of [[-.002, .004], [-.0014, .032], [.0014, .032], [.002, .004]]) {
      expectSurface([part], x, .8 + dz, down, top, /grid/i);
    }
    // The surviving mineral face is between the inner edges of the 24 mm tee and 12 mm half flange.
    for (const [z, depth, finish] of [[.8119, 0, /grid/i], [.813, .008, /fibre/i],
      [.987, .008, /fibre/i], [.9881, 0, /grid/i]]) {
      expectSurface([part], x, z, up, depth, finish);
    }
  }
});

test('the production visitor and independent triangle sweep traverse both sides of the open aisle', async t => {
  const world = await measureWallContact(bay);
  t.after(() => world.dispose());
  const result = walk(world, [{ x: -2.4, z: -.15 }, { x: 2.4, z: -.15 },
    { x: 2.4, z: .15 }, { x: -2.4, z: .15 }]);
  near(result.metres, 9.9, 'returned walking distance');
  for (const z of [-.32, .32]) assert.ok(world.visitor.obstruction({ x: .27, z }), 'side wall constrains the visitor');
  t.diagnostic(`${result.metres} m traversed, ${result.samples} visitor positions and ${result.floorRays} floor probes`);
});
