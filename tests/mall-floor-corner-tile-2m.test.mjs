import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { assembleCornerTileFloor, cornerFloorPath } from '../mall-modules-preview/floor-edge.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { checkFloor, measureCorridor, walk } from './helpers/mall-mesh.mjs';

async function load(path) {
  return (await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)))).scene;
}
const sources = { floor2m: await load(floorTransitionPaths.floor2m), cornerFloor2m: await load(cornerFloorPath) };
const down = new Vector3(0, -1, 0), up = new Vector3(0, 1, 0);
const stone = 'Honed ivory terrazzo, seed 421', green = 'Cut eucalyptus terrazzo';
function near(actual, expected, label) {
  assert.ok(Number.isFinite(actual) && Math.abs(actual - expected) < 1e-6, `${label}: ${actual}, expected ${expected}`);
}
function installed() {
  const group = assembleCornerTileFloor(sources);
  group.updateMatrixWorld(true);
  return group;
}
function surface(root, x, z, fromBelow = false) {
  const ray = new Raycaster(new Vector3(x, fromBelow ? -.5 : .5, z), fromBelow ? up : down);
  const hit = ray.intersectObject(root, true)[0];
  assert.ok(hit, `missing triangle at ${x}, ${z} in ${root.name}`);
  near(hit.point.y, fromBelow ? -.1 : 0, 'floor height');
  return hit.object.material.name;
}
function bandAt(tile, x, z, expected) {
  assert.equal(surface(tile, x, z), expected, `inlay at ${x}, ${z}`);
}

test('the 4 m square floor uses one unscaled corner tile and four coplanar shared edges', t => {
  const floor = installed();
  assert.equal(floor.children.length, 4);
  assert.equal(new Set(floor.children.map(p => p.name)).size, 4);
  for (const x of [-1, 1]) for (const z of [-1, 1]) {
    const p = floor.children.find(tile => tile.position.x === x && tile.position.z === z);
    assert.ok(p); assert.match(p.name, /^Floor_\d+$/);
    assert.deepEqual(p.scale.toArray(), [1, 1, 1]);
    assert.equal(p.userData.moduleId, x === 1 && z === 1 ? 'cornerFloor2m' : 'floor2m');
    const bounds = new Box3().setFromObject(p, true);
    near(bounds.min.x, x - 1, 'west'); near(bounds.max.x, x + 1, 'east');
    near(bounds.min.z, z - 1, 'rear'); near(bounds.max.z, z + 1, 'front');
    near(bounds.min.y, -.1, 'underside'); near(bounds.max.y, 0, 'wearing surface');
    surface(p, x + .13, z + .21, true);
  }
  let edgeRays = 0;
  for (const axis of ['x', 'z']) {
    const cross = axis === 'x' ? 'z' : 'x';
    for (const centre of [-1, 1]) {
      const pair = floor.children.filter(tile => tile.position[cross] === centre)
        .sort((a,b) => a.position[axis] - b.position[axis]);
      for (let i = 0; i <= 100; i++) {
        const along = centre - .99999 + 1.99998 * i / 100;
        for (const offset of [.000003, .001, .003]) for (const [j, sign] of [[0,-1],[1,1]]) {
          surface(pair[j], axis === 'x' ? sign * offset : along, axis === 'z' ? sign * offset : along);
          edgeRays++;
        }
      }
    }
  }
  t.diagnostic(JSON.stringify({ sharedEdges: 4, edgeRays }));
});

test('the brass and eucalyptus bands turn on both outside edges and meet on the 45 degree diagonal', () => {
  const tile = installed().children.find(p => p.userData.moduleId === 'cornerFloor2m');
  assert.ok(tile.getObjectByName('MODULE_CornerFloor_L0'));
  // Probe 10 micrometres to either side of each authored material boundary.
  for (const side of ['front', 'right']) {
    const brass = 'Brushed champagne ' + side;
    for (const [inset, finish] of [[.02499,stone],[.02501,brass],[.05299,brass],[.05301,green],
      [.10299,green],[.10301,brass],[.11699,brass],[.11701,stone]]) {
      const outer = 2 - inset;
      bandAt(tile, side === 'front' ? 1.173 : outer, side === 'front' ? outer : 1.173, finish);
    }
    for (const [inset, finish] of [[.038,brass],[.076,green],[.109,brass]]) {
      const outer = 2 - inset;
      // Include the paver joints and both ends of the band up to the mitre.
      for (const along of [.00001,.37,.5,.91,1,1.5,1.73,outer - .00001]) {
        bandAt(tile, side === 'front' ? along : outer, side === 'front' ? outer : along, finish);
      }
      bandAt(tile, side === 'front' ? 1.173 : inset, side === 'front' ? inset : 1.173, stone);
    }
  }
  tile.rotation.y += Math.PI;
  tile.updateMatrixWorld(true);
  const bounds = new Box3().setFromObject(tile, true);
  near(bounds.max.x, 2, 'misoriented tile still fills the floor');
  assert.throws(() => bandAt(tile, 1.173, 1.962, 'Brushed champagne front'), /inlay/);
});

test('the visitor crosses the corner tile both ways and stops at its exterior edge', async t => {
  const group = installed(), corner = group.children.find(p => p.userData.moduleId === 'cornerFloor2m');
  const scene = await measureCorridor(group);
  t.after(() => scene.dispose());
  const route = [{ x: -1.1, z: .71 }, { x: 1.395, z: .71 }, { x: 1.395, z: 1.405 },
    { x: .875, z: 1.405 }, { x: .875, z: -.91 }];
  const forward = walk(scene, route), reverse = walk(scene, route.toReversed());
  for (const [dx, dz] of [[.4, 0], [0, .4]]) {
    const p = { ...route[2] };
    assert.equal(scene.visitor.move(p, dx, dz), 'Floor edge');
    assert.equal(scene.visitor.obstruction(p), null);
    checkFloor(scene, p);
  }
  group.remove(corner);
  const omitted = await measureCorridor(group);
  t.after(() => omitted.dispose());
  assert.equal(omitted.surface(.9,.9), null, 'missing tile has no supporting triangles');
  assert.equal(omitted.visitor.obstruction({ x: .9, z: .9 }), 'Floor edge');
  t.diagnostic(JSON.stringify({ forward, reverse }));
});
