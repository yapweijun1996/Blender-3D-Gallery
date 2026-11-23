import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Triangle, Vector3 } from 'three';
import { assembleEscalatorTerminals, escalatorTerminalPaths } from '../mall-modules-preview/escalator-terminal.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';

async function load(path) {
  return (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const sources = Object.fromEntries(await Promise.all(Object.entries(escalatorTerminalPaths)
  .map(async ([key, path]) => [key, await load(path)])));
const lowerLevels = await Promise.all([1, 2].map(lod =>
  load(escalatorTerminalPaths.escalatorTransition2m.replace('.glb', '-lod' + lod + '.glb'))));

const point = (x, y, z) => new Vector3(x, y, z);
const up = point(0, 1, 0), down = point(0, -1, 0);
const bounds = object => new Box3().setFromObject(object, true);
const near = (a, b, label) => assert.ok(Number.isFinite(a) && Math.abs(a - b) < 1e-6,
  label + ' measured ' + a + ', expected ' + b);
function ray(objects, origin, direction, length) {
  return new Raycaster(origin, direction, 0, length).intersectObjects(objects, true)[0];
}
function surfaces(mesh) {
  const result = [];
  mesh.traverse(part => { if (part.isMesh) result.push(part); });
  return result;
}
function worldClone(object) {
  const clone = object.clone(true);
  object.matrixWorld.decompose(clone.position, clone.quaternion, clone.scale);
  clone.updateMatrixWorld(true);
  return clone;
}

function installation(source = sources.escalatorTransition2m) {
  const { group, inspections } = assembleEscalatorTerminals({ ...sources, escalatorTransition2m: source });
  group.updateMatrixWorld(true);
  const machine = group.children.find(part => part.userData.moduleId === 'escalator');
  assert.ok(machine && machine.getObjectByName('ASSET_EscalatorV1_ID004'));
  const machineBounds = surfaces(machine).map(mesh => ({ mesh, box: bounds(mesh) }));
  return ['lower', 'upper'].map(key => {
    const sign = key === 'lower' ? 1 : -1;
    const label = key === 'lower' ? 'Lower' : 'Upper';
    const terminal = group.children.find(part => part.userData.terminal === key);
    const profile = terminal.children.find(part => part.userData.moduleId === 'escalatorTransition2m');
    assert.equal(inspections[key].object, profile);
    const tiles = Object.fromEntries(terminal.children.filter(part => part.userData.moduleId === 'floor2m')
      .map(part => [part.userData.role, part]));
    assert.deepEqual(Object.keys(tiles).sort(), ['centre', 'left', 'right']);
    const deck = machine.getObjectByName('LANDING_' + label), beam = machine.getObjectByName('TRUSS_End_' + label);
    const deckBox = bounds(deck);
    const datum = deckBox.max.y, edge = sign === 1 ? deckBox.max.z : deckBox.min.z;
    near(datum, key === 'lower' ? 0 : 3, 'native elevation');
    near(edge, sign * 5.44105586, 'native deck edge');
    const p = (x, y, station) => point(x, datum + y, edge + sign * station);
    const dz = point(0, 0, sign);
    near(profile.getWorldPosition(new Vector3()).distanceTo(p(0, 0, 0)), 0, 'mating root');
    near(profile.localToWorld(point(0, 0, .12)).distanceTo(p(0, 0, .12)), 0, 'profile faces the slab');
    for (const [tile, x, s] of [[tiles.centre, 0, 1.12], [tiles.left, -2, 1], [tiles.right, 2, 1]]) {
      near(tile.getWorldPosition(new Vector3()).distanceTo(p(x, -.1, s)), 0, 'installed floor root');
    }
    return { key, p, dz, datum, sign, machine, machineBounds, tiles, profile, deck, beam };
  });
}

function triangleIntersectsBox(meshes, targetBox) {
  const triangle = new Triangle(), box = targetBox.clone().expandByScalar(-.000001);
  for (const mesh of meshes) {
    const geometry = mesh.geometry, position = geometry.getAttribute('position'), index = geometry.getIndex();
    const count = index?.count ?? position.count;
    for (let i = 0; i < count; i += 3) {
      for (const [offset, vertex] of [[0, triangle.a], [1, triangle.b], [2, triangle.c]]) {
        vertex.fromBufferAttribute(position, index ? index.getX(i + offset) : i + offset).applyMatrix4(mesh.matrixWorld);
      }
      if (box.intersectsTriangle(triangle)) return true;
    }
  }
  return false;
}

test('both stock terminals seat the returned approach and three original slabs with the measured recess clearances', t => {
  for (const [lod, source] of [sources.escalatorTransition2m, ...lowerLevels].entries()) {
    for (const { key, p, datum, dz, machineBounds, tiles, profile, deck, beam } of installation(source)) {
      const profileBox = bounds(profile);
      const candidates = machineBounds.filter(({ box }) => {
        const size = box.clone().intersect(profileBox).getSize(new Vector3());
        return Math.min(size.x, size.y, size.z) > .000001;
      });
      // The solid rectangular end crossmember is the only original machine part
      // whose world bounds occupy the profile envelope. Test its interior against
      // every actual profile triangle. The rear and lateral slabs meet on face planes.
      assert.deepEqual(candidates.map(item => item.mesh), [beam]);
      const body = surfaces(profile);
      assert.equal(triangleIntersectsBox(body, bounds(beam)), false);
      for (const tile of Object.values(tiles)) assert.equal(triangleIntersectsBox(body, bounds(tile)), false);

      for (const x of [-.763, -.34, .18, .759]) for (const station of [.003, .013, .018]) {
        const origin = p(x, -.017, station);
        const cap = ray([profile], origin, up, .016), rail = ray([beam], origin, down, .016);
        assert.ok(cap && rail);
        near(cap.point.y - rail.point.y, .005, 'vertical beam clearance');
      }
      for (const x of [-.74, 0, .74]) {
        const origin = p(x, -.05, .0225);
        const back = ray([profile], origin, dz, .012), rail = ray([beam], origin, dz.clone().negate(), .012);
        assert.ok(back && rail);
        near(back.distance + rail.distance, .005, 'rear beam clearance');
      }
      for (const side of [-1, 1]) for (const station of [.004, .017]) {
        const origin = p(side * .7775, -.05, station), dx = point(side, 0, 0);
        const cap = ray([profile], origin, dx, .012), rail = ray([beam], origin, dx.clone().negate(), .012);
        assert.ok(cap && rail);
        near(cap.distance + rail.distance, .005, 'side beam clearance');
      }

      let samples = 0, maximumDepression = 0;
      for (let i = 0; i <= 30; i++) {
        const x = -.766 + 1.532 * i / 30;
        for (const station of [-.006, -.0015, -.0002, .0002, .006, .019, .026, .07, .1198, .1202, .126]) {
          const expected = station < 0 ? deck : station < .12 ? profile : tiles.centre;
          const hit = ray([expected], p(x, .04, station), down, .06);
          assert.ok(hit && hit.point.y <= datum + .000001 && hit.point.y >= datum - .001001,
            'continuous top across original deck bevel, transition and original slab');
          maximumDepression = Math.max(maximumDepression, datum - hit.point.y);
          samples++;
        }
      }
      t.diagnostic(JSON.stringify({ lod, terminal: key, surfaceSamples: samples, maximumDepression }));
    }
  }
});

test('front shoulder caps terminate at the deck edge and both side faces mate with real flank tiles', t => {
  for (const [lod, source] of [sources.escalatorTransition2m, ...lowerLevels].entries()) {
    for (const { key, p, dz, datum, tiles, profile, deck, machine } of installation(source)) {
      let frontRays = 0, sidePairs = 0, exposedEdges = 0;
      const across = [machine, profile, ...Object.values(tiles)];
      for (const [side, flank] of [[-1, tiles.left], [1, tiles.right]]) {
        // The inner 5 mm of the 225 mm shoulder covers the side of the beam pocket.
        // Its 15 mm cap remains above the recess; the remaining 220 mm has a full-height face.
        for (const x of [.7765, .7785]) for (const [y, expected] of [[-.004, 0], [-.012, 0], [-.030, .025], [-.083, .025]]) {
          const hit = ray([profile], p(side * x, y, -.004), dz, .04);
          assert.ok(hit);
          near(hit.distance - .004, expected, 'thin front cap over central relief');
          frontRays++;
        }
        for (const x of [.786, .812, .891, .954, .992]) for (const y of [-.006, -.024, -.067, -.095]) {
          const hit = ray([profile], p(side * x, y, -.005), dz, .015);
          assert.ok(hit && Math.abs(hit.distance - .005) <= .001001, 'finished full-depth front return');
          frontRays++;
        }
        const face = ray([profile], p(side * .88, -.05, -.002), dz, .014);
        assert.match(face.object.material.name, /shoulder wear plate/i);
        near(face.face.normal.clone().transformDirection(face.object.matrixWorld).dot(dz), -1, 'front shoulder normal');
        // The reduced distant plate keeps the same outer face. Closer levels
        // include two flush fixing heads with shallow, measurable countersinks.
        for (const x of [.810, .968]) {
          const head = ray([profile], p(side * x, -.05, -.002), dz, .012);
          const ring = ray([profile], p(side * (x + .0068), -.05, -.002), dz, .012);
          assert.match(head.object.material.name, lod < 2 ? /fixing steel/i : /shoulder wear plate/i);
          near(head.distance, .002, 'flush finished face');
          near(ring.distance - head.distance, lod < 2 ? .00055 : 0, 'countersink depth');
        }
        // Rays from above and below distinguish the exposed front from surrounding floor.
        for (const x of [.790, .85, .94, .996]) {
          assert.equal(ray(across, p(side * x, .02, -.004), down, .06), undefined);
          near(ray([profile], p(side * x, .02, .004), down, .06)?.point.y, datum, 'return wearing face');
          near(ray([profile], p(side * x, -.12, .004), up, .05)?.point.y, datum - .10, 'return underside');
          assert.equal(ray([deck], p(side * x, .02, -.004), down, .06), undefined);
          exposedEdges++;
        }
        for (const x of [.7765, .7785]) {
          assert.equal(ray(across, p(side * x, .005, -.004), down, .012), undefined,
            'the narrow cap also terminates beyond the 1.55 m deck');
        }
        const outward = point(side, 0, 0), inward = outward.clone().negate();
        for (const s of [.003, .017, .026, .060, .094, .117]) {
          for (const y of [-.006, -.037, -.072, -.095]) {
            const a = ray([profile], p(side * 1.003, y, s), inward, .008);
            const b = ray([flank], p(side * .997, y, s), outward, .008);
            assert.ok(a && b);
            near(a.point.distanceTo(b.point), 0, 'flank contact above the slab underside bevel');
            sidePairs++;
          }
          for (const [object, radius] of [[profile, .9998], [flank, 1.0002]]) {
            near(ray([object], p(side * radius, .025, s), down, .05)?.point.y, datum, 'flush side top');
          }
        }
        // The bottom 2 mm of the original precast slab is bevelled. The new
        // vertical side face remains square, leaving a triangular underside relief.
        for (const [y, gap] of [[-.098, 0], [-.099, .001], [-.0995, .0015]]) {
          const a = ray([profile], p(side * 1.004, y, .060), inward, .012);
          const b = ray([flank], p(side * .996, y, .060), outward, .012);
          near(a.point.distanceTo(b.point), gap, 'native underside bevel');
        }
        for (const x of [.80, .90, .995]) {
          near(ray([profile], p(side * x, .025, .1198), down, .05)?.point.y, datum, 'rear shoulder top');
          near(ray([tiles.centre], p(side * x, .025, .1202), down, .05)?.point.y, datum, 'rear shoulder floor');
        }
      }
      t.diagnostic(JSON.stringify({ lod, terminal: key, frontRays, sidePairs, exposedEdges }));
    }
  }
});

test('a stock slab intersects the beam or leaves a sunken band, and a wrongly aligned side tile misses the return', () => {
  for (const { p, sign, datum, tiles, beam, deck, profile } of installation()) {
    const flush = worldClone(tiles.centre);
    flush.position.z -= sign * .12;
    flush.updateMatrixWorld(true);
    assert.ok(triangleIntersectsBox(surfaces(flush), bounds(beam)), 'stock slab cuts the original beam');
    const shifted = worldClone(flush);
    shifted.position.z += sign * .02;
    shifted.updateMatrixWorld(true);
    for (const x of [-.72, -.19, .181, .73]) for (const s of [.004, .013, .018]) {
      const high = p(x, .03, s), low = p(x, -2.5, s);
      const railTop = ray([beam], high, down, .14), tileBottom = ray([flush], low, up, 2.6);
      assert.ok(railTop && tileBottom);
      near(railTop.point.y - tileBottom.point.y, .08, '80 mm stock slab penetration');
      const first = ray([deck, beam, shifted], high, down, .12);
      assert.equal(first.object, beam);
      near(datum - first.point.y, .02, 'shifting a plain slab reveals the lower beam surface');
    }
    for (const [side, tile] of [[-1, tiles.left], [1, tiles.right]]) {
      const misaligned = worldClone(tile);
      misaligned.position.z += sign * .12;
      misaligned.updateMatrixWorld(true);
      const origin = p(side * 1.002, .02, .06);
      assert.ok(ray([tile], origin, down, .05));
      assert.equal(ray([misaligned, profile, tiles.centre], origin, down, .05), undefined);
    }
  }
});
