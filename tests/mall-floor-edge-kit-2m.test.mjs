import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { assembleFinishedFloorEdge, cornerFloorPath, floorEdgePaths } from '../mall-modules-preview/floor-edge.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { shellAssetPaths } from '../mall-modules-preview/shell-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor } from './helpers/mall-mesh.mjs';
import { BODY } from '../docs/verification/mall-corridor/collision.js';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';

async function load(path) {
  return (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const sources = {};
for (const [id, path] of Object.entries({ floor2m: floorTransitionPaths.floor2m, cornerFloor2m: cornerFloorPath, ...floorEdgePaths })) {
  sources[id] = await load(path);
}
const legacy = await load(shellAssetPaths.floorEdge);
const down = new Vector3(0, -1, 0), up = new Vector3(0, 1, 0);
const nosing = 'Satin champagne nosing', fascia = 'Anodized bronze fascia';
function near(actual, expected, label) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < 1e-6, `${label}: ${actual}, expected ${expected}`);
}
function installed() {
  const group = assembleFinishedFloorEdge(sources);
  group.updateMatrixWorld(true);
  const straight = group.children.filter(part => part.userData.moduleId === 'edge2m');
  assert.equal(straight.length, 2);
  const front = straight.find(p => p.position.x < 0), right = straight.find(p => p !== front);
  const pair = group.children.find(p => p.userData.moduleId === 'mitredEdge2m');
  const floors = group.children.filter(part => ['floor2m', 'cornerFloor2m'].includes(part.userData.moduleId));
  assert.equal(floors.length, 4);
  return { group, front, right, pair, floors };
}
function ray(objects, xyz, direction) {
  return new Raycaster(new Vector3(...xyz), direction).intersectObjects(objects, true);
}
function hit(objects, xyz, dir) {
  const first = ray(objects, xyz, dir)[0];
  assert.ok(first, `missing triangle from ${xyz} along ${dir.toArray()}`);
  return first;
}
const coords = (front, along, y, radial) => front ? [along, y, radial] : [radial, y, along];
const section = [[-.002,.060,nosing], [-.008,.0585,nosing], [-.016,.0595,fascia], [-.043,.0575,fascia],
  [-.085,.0545,fascia], [-.094,.057,fascia], [-.099,.056,fascia]];

test('the 2 m straight and mitred pieces meet end to end through the full 100 mm section', t => {
  const { front, right, pair, floors } = installed();
  const dimensions = new Box3().setFromObject(pair, true).getSize(new Vector3());
  near(dimensions.x, 2.06, 'mitre X span'); near(dimensions.z, 2.06, 'mitre Z span');
  near(dimensions.y, .1, 'mitre depth');
  let endPairs = 0, floorPairs = 0, profileRays = 0, bevelCorners = 0;
  for (const [straight, isFront, straightSocket, pairSocket] of [
    [front,true,'CONNECTOR_Straight_East_LOD0','CONNECTOR_Mitre_West_LOD0'],
    [right,false,'CONNECTOR_Straight_West_LOD0','CONNECTOR_Mitre_South_LOD0'],
  ]) {
    const coordinate = isFront ? 'x' : 'z', radialAxis = isFront ? 'z' : 'x';
    const along = isFront ? new Vector3(1,0,0) : new Vector3(0,0,1);
    const outward = isFront ? new Vector3(0,0,1) : new Vector3(1,0,0);
    const inward = outward.clone().negate();
    const p = straight.getObjectByName(straightSocket).getWorldPosition(new Vector3());
    const q = pair.getObjectByName(pairSocket).getWorldPosition(new Vector3());
    near(p.distanceTo(q), 0, 'mating connectors');
    near(q[coordinate], 0, 'mating plane'); near(q[radialAxis], 2.03, 'section centre'); near(q.y, 0, 'top');
    for (const [y, lip, material] of section) {
      for (const r of [.00002, .02, .043, lip - .00002]) {
        const a = hit([straight], coords(isFront, .1, y, 2 + r), along.clone().negate());
        const b = hit([pair], coords(isFront, -.1, y, 2 + r), along);
        near(a.point[coordinate], 0, 'end of straight');
        near(b.point[coordinate] - a.point[coordinate], 0, 'section end gap');
        endPairs++;
      }
      for (const [part, station] of [[straight, -.00001], [pair, .00001]]) {
        const face = hit([part], coords(isFront, station, y, 2.3), inward);
        near(face.point[radialAxis], 2 + lip, 'wearing edge / fascia profile');
        assert.equal(face.object.material.name, material);
        profileRays++;
      }
    }
    for (const [part, sign] of [[straight, -1], [pair, 1]]) {
      for (let i = 0; i <= 35; i++) {
        const station = sign * (.00002 + (1.99996 * i / 35));
        for (const y of [-.002, -.04, -.085, -.099]) {
          const edge = ray(floors, coords(isFront, station, y, 2.3), inward);
          if (y === -.099 && (i === 0 || i === 35)) {
            // At both slab ends the underside bevel retreats in BOTH horizontal axes.
            assert.equal(edge.length, 0, 'expected underside relief at the tile corner');
            bevelCorners++;
            continue;
          }
          assert.ok(edge.length, 'floor edge must support the trim interface here');
          const tile = edge[0];
          const inside = hit([part], coords(isFront, station, y, 1.7), outward);
          near(inside.point[radialAxis], 2, 'straight inner trim face');
          // The floor substrate has a 2 mm bevel on its underside.
          near(inside.point[radialAxis] - tile.point[radialAxis], y === -.099 ? .001 : 0, 'floor-to-trim fit');
          floorPairs++;
        }
      }
    }
  }
  t.diagnostic(JSON.stringify({ endPairs, floorPairs, profileRays, bevelCorners }));
});

test('the diagonal mitre is covered by precisely one arm on either side and retains the outer lip and inlay', t => {
  const { pair } = installed();
  let topRays = 0;
  for (const r of [.0001,.012,.04399,.04401,.04549,.04551,.057,.0599]) {
    for (const offset of [-.00001, .00001]) {
      const x = 2 + r + Math.min(0, offset), z = 2 + r - Math.max(0, offset);
      const hits = ray([pair], [x,.4,z], down).filter(h => Math.abs(h.point.y) < 1e-6);
      assert.ok(hits.length > 0);
      const arms = new Set(hits.map(h => h.object.name.split('_')[0]));
      assert.deepEqual([...arms], [offset < 0 ? 'Front' : 'Right'], 'only the matching arm owns the top');
      assert.equal(hits[0].object.material.name, r > .044 && r < .0455 ? fascia : nosing);
      topRays++;
    }
    near(hit([pair], [2+r,.4,2+r], down).point.y, 0, 'diagonal top stays covered');
  }
  // Cast toward the corner from outside at each depth; this verifies the edge profile
  // around the folded turn independently of the top face and the nominal bounding box.
  const inward = new Vector3(-1,0,-1).normalize();
  for (const [y, lip, mat] of section) for (const offset of [-.003, 0, .003]) {
    const first = hit([pair], [2.3+offset,y,2.3-offset], inward);
    near(offset <= 0 ? first.point.z : first.point.x, 2 + lip, 'outer diagonal section');
    assert.equal(first.object.material.name, mat);
  }
  for (const r of [.0001, .02, .0549]) {
    near(hit([pair], [2+r,-.4,2+r], up).point.y, -.1, 'mitre underside');
  }
  t.diagnostic(JSON.stringify({ topSides: topRays, diagonalTop: 8, outerProfile: 21, diagonalBase: 3 }));
});

test('backwards trim, a shallow legacy section and an omitted mitre each fail a different visual joint', () => {
  const { group, right, front, pair } = installed();
  const atStripe = () => hit([right], [2.04475,.2,-.73], down).object.material.name;
  assert.equal(atStripe(), fascia);
  right.rotation.y = -Math.PI / 2;
  right.updateMatrixWorld(true);
  near(new Box3().setFromObject(right,true).max.x, 2.06, 'reversed cap can still reach the same outer line');
  assert.equal(atStripe(), nosing, 'reversal puts the bronze stripe on the wrong side');

  const old = legacy.clone(true); old.position.copy(front.position); old.updateMatrixWorld(true);
  near(new Box3().setFromObject(old,true).getSize(new Vector3()).y, .03, 'legacy profile depth');
  const nextOld = old.clone(true); nextOld.position.x += 2; nextOld.updateMatrixWorld(true);
  const oldBounds = new Box3().setFromObject(old, true), nextBounds = new Box3().setFromObject(nextOld, true);
  near(nextBounds.min.x - oldBounds.max.x, .8, '800 mm gap on a 2 m repeat');
  assert.equal(ray([old, nextOld], [0,.4,2.03], down).length, 0, 'old caps leave an open strip between them');
  const inward = new Vector3(0,0,-1);
  assert.ok(ray([old], [-1,-.006,2.3], inward).length > 0);
  assert.equal(ray([old], [-1,-.08,2.3], inward).length, 0);
  near(hit([front], [-1,-.08,2.3], inward).point.y, -.08, 'new full-depth facing');
  group.remove(pair);
  for (const [x, z] of [[1.37,2.03], [2.03,1.37], [2.035,2.035]]) {
    assert.equal(ray([group], [x,.5,z], down).length, 0, 'uncovered exterior strip');
  }
});

test('the 60 mm trim finishes the slab without adding a walkable floor cell', async t => {
  const { group, pair, floors } = installed();
  const scene = await measureWallContact(group);
  t.after(() => scene.dispose());
  assert.equal(scene.visitor.floors.length, 4);
  const edgeSupport = [];
  for (const [x, z, dx, dz] of [[1.2,1.39,0,.25], [1.39,1.2,.25,0]]) {
    const p = { x, z };
    const outer = dx === 0 ? [x, .5, 2.03] : [2.03, .5, z];
    near(hit([pair], outer, down).point.y, 0, 'visible trim top');
    assert.equal(scene.surface(outer[0], outer[2]), null, 'finishing strip is outside floor support');
    assert.equal(scene.sweep(p, dx, dz), null, 'trim is outside the visitor obstacle set');
    assert.equal(scene.visitor.move(p, dx, dz), 'Floor edge');
    checkFloor(scene, p);
    const ex = p.x + (dx ? BODY.radius : 0), ez = p.z + (dz ? BODY.radius : 0);
    near(dx ? ex : ez, 2, 'accepted footprint reaches the slab boundary');
    const wearing = hit(floors, [ex,.1,ez], down);
    const closest = scene.projectFloor(wearing.point);
    assert.ok(closest && wearing.point.distanceTo(closest) <= .000001, 'same-point Rapier and GLB agreement within 1 μm');
    near(scene.surface(ex, ez), 0, 'supported at the actual boundary');
    const xOut = ex + (dx ? .00001 : 0), zOut = ez + (dz ? .00001 : 0);
    assert.equal(scene.surface(xOut, zOut), null, '10 μm outside has no floor support');
    edgeSupport.push({ x: ex, z: ez, rawRapier: scene.rawSurface(ex, ez), checkedY: closest.y });
  }
  assert.ok(edgeSupport.some(p => p.rawRapier === null), 'locked Rapier reproduces a miss on an exact outer edge');
  t.diagnostic(JSON.stringify({ edgeSupport }));
});
