import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { Box3, Raycaster, Texture, Triangle, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { assembleCrossJunction, assembleTJunction } from '../mall-modules-preview/floor-junctions.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';
import { walk } from './helpers/mall-mesh.mjs';

const near = (actual, expected) => assert.ok(Math.abs(actual - expected) < 1e-6, actual + ' vs ' + expected);
const tileFile = new URL('../' + floorTransitionPaths.floor2m, import.meta.url);
const manifest = JSON.parse(await readFile(new URL('../metadata/mall-floor-module-2m.json', tileFile)));
const west = { x: -2, z: 0 },
  east = { x: 2, z: 0 },
  north = { x: 0, z: -2 },
  south = { x: 0, z: 2 },
  centre = { x: 0, z: 0 };
const plans = [
  { name: 'T', build: assembleTJunction, arms: [west, east, north] },
  { name: 'cross', build: assembleCrossJunction, arms: [west, east, north, south] },
];
const down = new Vector3(0, -1, 0);
const ray = new Raycaster(new Vector3(), down, 0, 0.4);

// The three GLBs contain PNG or JPEG artwork. These checks load the original
// mesh buffers and node transforms; they need no image decoding or WebGL context.
const loader = new GLTFLoader().register(() => ({
  name: 'geometry-only',
  loadTexture: async () => new Texture(),
}));
const sources = await Promise.all(
  manifest.lods.map(async ({ file }) => {
    const bytes = await readFile(new URL('../' + file, tileFile));
    const data = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
    return { floor2m: (await loader.parseAsync(data, '')).scene };
  }),
);
assert.equal(sources.length, 3);

function top(group, x, z) {
  ray.ray.origin.set(x, 0.15, z);
  return ray.intersectObject(group, true)[0]?.point.y;
}
function assertFlushSurface(tile, x, z) {
  const y = top(tile, x, z);
  if (Number.isFinite(y) && Math.abs(y) < 1e-6) return false;
  // A quarter turn can put an exact outer-edge ray a few ULPs outside a
  // triangle. Verify the same point against the actual horizontal wearing faces.
  const probe = new Vector3(x, 0, z),
    nearest = new Vector3(),
    triangle = new Triangle();
  let distance = Infinity;
  tile.traverse((mesh) => {
    if (!mesh.isMesh) return;
    const { index, attributes } = mesh.geometry;
    const count = index?.count ?? attributes.position.count;
    for (let start = 0; start < count; start += 3) {
      for (const [j, vertex] of [triangle.a, triangle.b, triangle.c].entries()) {
        mesh
          .getVertexPosition(index ? index.getX(start + j) : start + j, vertex)
          .applyMatrix4(mesh.matrixWorld);
      }
      if (Math.max(Math.abs(triangle.a.y), Math.abs(triangle.b.y), Math.abs(triangle.c.y)) > 1e-6) continue;
      distance = Math.min(distance, triangle.closestPointToPoint(probe, nearest).distanceTo(probe));
    }
  });
  assert.ok(
    distance < 1e-6,
    tile.name + ' at ' + x + ', ' + z + ' is ' + distance + ' m from the wearing surface',
  );
  return true;
}
function cell(group, point) {
  const found = group.children.find((tile) => tile.position.x === point.x && tile.position.z === point.z);
  assert.ok(found, 'Missing expected cell at ' + JSON.stringify(point));
  return found;
}
function visibleVoid(group, scene, point) {
  assert.equal(top(group, point.x, point.z), undefined);
  assert.equal(scene.surface(point.x, point.z), null);
  assert.equal(scene.visitor.obstruction(point), 'Floor edge');
}

for (const { name, build, arms } of plans) {
  test(name + ' junction exposes one supported 2 m seam per arm at every LOD', (t) => {
    let probes = 0,
      edgeProjections = 0;
    for (const source of sources) {
      const group = build(source);
      group.updateMatrixWorld(true);
      assert.equal(group.children.length, 1 + arms.length);
      assert.equal(new Set(group.children.map((o) => o.name)).size, group.children.length);
      assert.equal(new Set(group.children.map((o) => o.rotation.y)).size, 4);
      for (const point of [centre, ...arms]) {
        const tile = cell(group, point);
        assert.match(tile.name, /^Floor_\d+$/);
        assert.equal(tile.userData.moduleId, 'floor2m');
        assert.deepEqual(tile.scale.toArray(), [1, 1, 1]);
        const { min, max } = new Box3().setFromObject(tile, true);
        near(min.x, point.x - 1);
        near(max.x, point.x + 1);
        near(min.z, point.z - 1);
        near(max.z, point.z + 1);
        near(min.y, -0.1);
        near(max.y, 0);
      }
      for (const tip of arms) {
        const dx = tip.x / 2,
          dz = tip.z / 2;
        for (let index = 0; index <= 100; index++) {
          const along = (index - 50) * 0.02;
          const x = dx - dz * along,
            z = dz + dx * along;
          // Compare each tile's own surface 0.1 mm inside its face at the joint.
          edgeProjections += Number(
            assertFlushSurface(cell(group, centre), x - dx * 0.0001, z - dz * 0.0001),
          );
          edgeProjections += Number(assertFlushSurface(cell(group, tip), x + dx * 0.0001, z + dz * 0.0001));
          probes += 2;
        }
      }
    }
    t.diagnostic(JSON.stringify({ probesAcrossThreeLods: probes, edgeProjections }));
  });

  test(
    name + ' junction supports every ordered arm-to-arm route and blocks cuts across its inside corners',
    async (t) => {
      for (const [lod, source] of sources.entries()) {
        const group = build(source),
          scene = await measureWallContact(group);
        try {
          let paths = 0,
            metres = 0,
            footprintRays = 0;
          for (const from of arms)
            for (const to of arms) {
              if (from === to) continue;
              const result = walk(scene, [from, centre, to]);
              paths++;
              metres += result.metres;
              footprintRays += result.floorRays;
            }
          assert.equal(paths, arms.length * (arms.length - 1));
          near(metres, paths * 4);
          for (const side of arms.filter((a) => a.x))
            for (const branch of arms.filter((a) => a.z)) {
              const sx = Math.sign(side.x),
                sz = Math.sign(branch.z);
              const at = (d) => ({ x: sx * d, z: sz * d });
              const supported = at(0.54),
                shortcut = at(0.72);
              assert.equal(scene.visitor.obstruction(supported), null);
              near(top(group, shortcut.x, shortcut.z), 0); // Root is supported, but its footprint overhangs the corner.
              assert.equal(scene.visitor.obstruction(shortcut), 'Floor edge');
              const position = { ...supported };
              assert.equal(scene.visitor.move(position, sx * 0.18, sz * 0.18), 'Floor edge');
              assert.equal(scene.visitor.obstruction(position), null);
              assert.ok(Math.hypot(position.x - shortcut.x, position.z - shortcut.z) > 0.02);
              visibleVoid(group, scene, at(1.6));
            }
          if (arms.length === 3) visibleVoid(group, scene, south);
          assert.ok(scene.corrections.maxDistanceMetres <= 1e-6);
          t.diagnostic(JSON.stringify({ lod, paths, metres, footprintRays, corrections: scene.corrections }));
        } finally {
          scene.dispose();
        }
      }
    },
  );
}

test('removing the centre or a branch breaks exactly the corresponding floor route', async (t) => {
  for (const { name, build } of plans)
    for (const absent of [centre, north]) {
      const group = build(sources[0]);
      group.remove(cell(group, absent));
      const scene = await measureWallContact(group);
      try {
        visibleVoid(group, scene, absent);
        const start = absent === centre ? west : centre;
        const p = { ...start };
        assert.equal(scene.visitor.move(p, absent.x - p.x, absent.z - p.z), 'Floor edge');
        assert.equal(scene.visitor.obstruction(p), null);
        if (absent === north) near(walk(scene, [west, centre, east]).metres, 4);
        t.diagnostic(name + ' stops before missing ' + (absent === centre ? 'centre' : 'north arm'));
      } finally {
        scene.dispose();
      }
    }
});

test('quarter-turning the whole T rotates the available branch and the blocked edge together', async (t) => {
  for (const turns of [1, 2, 3]) {
    const group = assembleTJunction(sources[0]);
    group.rotation.y = (turns * Math.PI) / 2;
    group.updateMatrixWorld(true);
    const rotate = ({ x, z }) => {
      const world = group.localToWorld(new Vector3(x, 0, z));
      return { x: Math.round(world.x), z: Math.round(world.z) };
    };
    const scene = await measureWallContact(group);
    try {
      near(walk(scene, [rotate(west), centre, rotate(north)]).metres, 4);
      visibleVoid(group, scene, rotate(south));
    } finally {
      scene.dispose();
    }
  }
});
