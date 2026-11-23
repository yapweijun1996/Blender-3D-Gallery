import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import { Box3, Color, Matrix3, Raycaster, Texture, Triangle, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import {
  assembleInsideFloorEdge,
  floorEdgePaths,
  insideMitrePath,
} from '../mall-modules-preview/floor-edge.js';
import { floorTransitionPaths } from '../mall-modules-preview/floor-transition.js';
import { measureWallContact } from './helpers/mall-wall-contact.mjs';
import { walk } from './helpers/mall-mesh.mjs';

// Read the original buffers and material assignments. The tile's image encoding
// differs by LOD; these geometry and vertex-colour measurements do not sample pixels.
const loader = new GLTFLoader().register(() => ({
  name: 'geometry-only',
  loadTexture: async () => new Texture(),
}));
async function levels(path) {
  return Promise.all(
    [0, 1, 2].map(async (lod) => {
      const file = lod ? path.replace(/\.glb$/, '-lod' + lod + '.glb') : path;
      const bytes = await readFile(new URL('../' + file, import.meta.url));
      return (
        await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length), '')
      ).scene;
    }),
  );
}
const [tiles, edges, insides, outsides] = await Promise.all([
  levels(floorTransitionPaths.floor2m),
  levels(floorEdgePaths.edge2m),
  levels(insideMitrePath),
  levels(floorEdgePaths.mitredEdge2m),
]);
const v = (x = 0, y = 0, z = 0) => new Vector3(x, y, z);
const up = v(0, 1, 0),
  down = v(0, -1, 0);
const cap = 'Satin champagne nosing',
  fascia = 'Anodized bronze fascia';
const section = [
  [-0.002, 0.06, cap],
  [-0.008, 0.0585, cap],
  [-0.016, 0.0595, fascia],
  [-0.043, 0.0575, fascia],
  [-0.085, 0.0545, fascia],
  [-0.094, 0.057, fascia],
  [-0.099, 0.056, fascia],
];
const arms = [
  {
    along: 'x',
    radial: 'z',
    axis: v(1, 0, 0),
    out: v(0, 0, 1),
    coord: (s, y, r) => v(s, y, r),
    insideSocket: 'East',
    straightSocket: 'West',
  },
  {
    along: 'z',
    radial: 'x',
    axis: v(0, 0, 1),
    out: v(1, 0, 0),
    coord: (s, y, r) => v(r, y, s),
    insideSocket: 'PositiveZ',
    straightSocket: 'East',
  },
];
const close = (a, b, label) =>
  assert.ok(Number.isFinite(a) && Math.abs(a - b) < 1e-6, label + ': ' + a + ' vs ' + b);
const ray = new Raycaster();
function hits(objects, point, dir) {
  ray.set(point, dir);
  return ray.intersectObjects(objects, true);
}
function first(objects, point, dir) {
  const hit = hits(objects, point, dir)[0];
  assert.ok(hit, 'missing actual triangle at ' + point.toArray() + ' along ' + dir.toArray());
  return hit;
}
function topHit(object, x, z) {
  return first([object], v(x, 0.21, z), down);
}
function topLayers(objects, x, z) {
  return hits(objects, v(x, 0.21, z), down).filter((h) => Math.abs(h.point.y) < 1e-6);
}
function worldNormal(hit) {
  return hit.face.normal.clone().applyNormalMatrix(new Matrix3().getNormalMatrix(hit.object.matrixWorld));
}
function sampleColor(hit) {
  const material = hit.object.material,
    geom = hit.object.geometry,
    colors = geom.getAttribute('color');
  const c = material.color.clone();
  if (!material.vertexColors || !colors) return c;
  const point = hit.object.worldToLocal(hit.point.clone()),
    p = geom.getAttribute('position'),
    ids = [hit.face.a, hit.face.b, hit.face.c];
  const weights = Triangle.getBarycoord(point, ...ids.map((i) => v().fromBufferAttribute(p, i)), v());
  const rgb = ids.reduce(
    (result, i, j) => result.addScaledVector(v().fromBufferAttribute(colors, i), weights.getComponent(j)),
    v(),
  );
  return c.multiply(new Color(rgb.x, rgb.y, rgb.z));
}
function install(inside = 0, straight = inside) {
  const group = assembleInsideFloorEdge({
    floor2m: tiles[inside],
    edge2m: edges[straight],
    insideMitre2m: insides[inside],
  });
  group.updateMatrixWorld(true);
  const floors = group.children.filter((n) => n.userData.moduleId === 'floor2m');
  const profiles = group.children.filter((n) => n.userData.moduleId === 'edge2m');
  const turn = group.children.find((n) => n.userData.moduleId === 'insideMitre2m');
  assert.equal(floors.length, 5);
  assert.equal(profiles.length, 2);
  assert.ok(turn);
  return { group, floors, turn, profiles };
}

test('both square interfaces fit the 100 mm original profile across all nine LOD combinations', (t) => {
  let capPairs = 0,
    facePairs = 0,
    connectorPairs = 0,
    slabChecks = 0;
  let maxConnectorGapM = 0;
  let maxCapGapM = 0;
  let maxSlabBackingGapM = 0;
  for (const level of [0, 1, 2])
    for (const sl of [0, 1, 2]) {
      const { turn, floors, profiles } = install(level, sl);
      const box = new Box3().setFromObject(turn, true);
      for (const axis of ['x', 'z']) {
        close(box.min[axis], 1, 'corner anchor');
        close(box.max[axis], 3, '2 m arm end');
      }
      close(box.max.y, 0, 'finished datum');
      close(box.min.y, -0.1, 'full-depth fascia');
      for (const arm of arms) {
        const straight = profiles.find((n) => Math.abs(n.position[arm.along] - 4) < 1e-6);
        const p = straight.getObjectByName('CONNECTOR_Straight_' + arm.straightSocket + '_LOD' + sl);
        const q = turn.getObjectByName('CONNECTOR_InsideMitre_' + arm.insideSocket + '_LOD' + level);
        assert.ok(p && q, 'both editable export connectors must survive');
        const a = p.getWorldPosition(v()),
          b = q.getWorldPosition(v());
        maxConnectorGapM = Math.max(maxConnectorGapM, a.distanceTo(b));
        close(a.distanceTo(b), 0, 'connector centres');
        close(a[arm.along], 3, '3 m seam');
        close(a[arm.radial], 1.03, 'radial centre');
        close(a.y, 0, 'connector datum');
        connectorPairs++;
        for (const [y, lip, finish] of section) {
          for (const depth of [0.00015, 0.021, 0.043, lip - 0.0001]) {
            const si = first([straight], arm.coord(2.85, y, 1 + depth), arm.axis);
            const mt = first([turn], arm.coord(3.16, y, 1 + depth), arm.axis.clone().negate());
            close(si.point[arm.along], 3, 'straight cap');
            maxCapGapM = Math.max(maxCapGapM, si.point.distanceTo(mt.point));
            close(si.point.distanceTo(mt.point), 0, 'mating endcaps');
            assert.ok(worldNormal(si).dot(arm.axis) < -0.999 && worldNormal(mt).dot(arm.axis) > 0.999);
            capPairs++;
          }
          for (const [part, station, lod] of [
            [turn, 2.998, level],
            [straight, 3.002, sl],
          ]) {
            const h = first([part], arm.coord(station, y, 1.25), arm.out.clone().negate());
            close(h.point[arm.radial], 1 + lip, 'exposed original section');
            // The original lowest 2 mm is a 45° underside bevel.
            const outwardComponent = y === -0.099 ? Math.SQRT1_2 : 1;
            close(worldNormal(h).dot(arm.out), outwardComponent, 'fascia points towards the void');
            if (lod < 2) assert.equal(h.object.material.name, finish);
            facePairs++;
          }
        }
        // Native slab underside has an intentional 2 mm bevel. Measure the vertical
        // mating surfaces away from that bevel and the grout at the ends of the tiles.
        for (const station of [1.16, 1.62, 2.37, 2.86, 3.21, 4.43])
          for (const y of [-0.004, -0.045, -0.085]) {
            const trim = station < 3 ? turn : straight;
            const backing = first([trim], arm.coord(station, y, 0.77), arm.out);
            const slab = first(floors, arm.coord(station, y, 1.23), arm.out.clone().negate());
            close(backing.point[arm.radial], 1, 'flat backing datum');
            maxSlabBackingGapM = Math.max(maxSlabBackingGapM, backing.point.distanceTo(slab.point));
            close(backing.point.distanceTo(slab.point), 0, 'slab contacts trim backing');
            slabChecks++;
          }
      }
    }
  t.diagnostic(
    JSON.stringify({
      lodPairs: 9,
      connectorPairs,
      capPairs,
      facePairs,
      slabChecks,
      maxConnectorGapM,
      maxCapGapM,
      maxSlabBackingGapM,
    }),
  );
});

test('the re-entrant diagonal has a single top, a continuous outer wear line and no internal cap', (t) => {
  let countedTop = 0,
    facadeCorners = 0,
    sameColorPairs = 0;
  for (const lod of [0, 1, 2]) {
    const { turn, profiles } = install(lod),
      front = profiles.find((p) => p.position.x === 4);
    let caps = 0;
    turn.traverse((mesh) => {
      if (!mesh.isMesh) return;
      const g = mesh.geometry,
        p = g.getAttribute('position'),
        indices = g.index;
      for (let k = 0; k < (indices?.count ?? p.count); k += 3) {
        const tri = [0, 1, 2].map((j) =>
          v()
            .fromBufferAttribute(p, indices ? indices.getX(k + j) : k + j)
            .applyMatrix4(mesh.matrixWorld),
        );
        if (!tri.every((v) => Math.abs(v.x - v.z) < 2e-6)) continue;
        if (new Triangle(...tri).getArea() > 1e-9) caps++;
      }
    });
    assert.equal(caps, 0, 'a diagonal face would cap or double the interior seam');
    for (const radius of [0.001, 0.021, 0.0437, 0.0444, 0.0451, 0.0458, 0.057, 0.0598]) {
      const reference = topHit(front, 4.161, 1 + radius),
        expectedColor = sampleColor(reference);
      for (const d of [-0.00022, 0.00031]) {
        const x = 1 + radius + Math.max(d, 0),
          z = 1 + radius + Math.max(-d, 0);
        const top = topLayers([turn], x, z);
        assert.equal(top.length, 1, 'one triangle on this side of diagonal');
        assert.ok(worldNormal(top[0]).y > 0.999, 'top faces the viewer above the floor');
        const sampled = sampleColor(top[0]).toArray();
        const expected = expectedColor.toArray();
        sampled.forEach((component, i) =>
          close(component, expected[i], 'matching cap or wear line colour'),
        );
        sameColorPairs++;
        countedTop++;
      }
      close(topHit(turn, 1 + radius, 1 + radius).point.y, 0, 'top directly on diagonal');
    }
    for (const [y, lip] of section)
      for (const offset of [-0.003, 0.002]) {
        // From the empty inside corner the NEAREST outward face belongs to whichever
        // radial coordinate is smaller. The opposite family of trims terminates on a convex corner.
        const diag = v(-1, 0, -1).normalize(),
          h = first([turn], v(1.3 + offset, y, 1.3 - offset), diag);
        close(Math.min(h.point.x, h.point.z), 1 + lip, 're-entrant fascia follows original lip');
        facadeCorners++;
      }
    for (const radius of [0.003, 0.021, 0.051])
      close(first([turn], v(1 + radius, -0.3, 1 + radius), up).point.y, -0.1, 'closed diagonal underside');
  }
  t.diagnostic(JSON.stringify({ countedTop, facadeCorners, sameColorPairs }));
});

test('two square strips overlap the turn and a reversed outside mitre folds onto the slabs', (t) => {
  for (const lod of [0, 1, 2]) {
    const { turn, floors } = install(lod);
    const strips = [edges[lod].clone(true), edges[lod].clone(true)];
    strips[0].position.set(2, 0, 1.03);
    strips[1].position.set(1.03, 0, 2);
    strips[1].rotation.y = Math.PI / 2;
    strips.forEach((n) => n.updateMatrixWorld(true));
    for (const [dx, dz] of [
      [0.013, 0.031],
      [0.023, 0.017],
      [0.041, 0.049],
    ]) {
      assert.equal(topLayers([turn], 1 + dx, 1 + dz).length, 1);
      assert.equal(
        topLayers(strips, 1 + dx, 1 + dz).length,
        2,
        'coincident ordinary top surfaces over the same square',
      );
      for (const strip of strips)
        close(first([strip], v(1 + dx, -0.2, 1 + dz), up).point.y, -0.1, 'duplicate full-depth volume');
    }
    const outside = outsides[lod].clone(true);
    outside.rotation.y = Math.PI;
    outside.position.set(2, 0, 2);
    outside.updateMatrixWorld(true);
    for (const [x, z, bx, bz] of [
      [2.183, 1.027, 2.183, 0.973],
      [1.027, 2.183, 0.973, 2.183],
    ]) {
      assert.equal(topLayers([turn], x, z).length, 1);
      assert.equal(topLayers([outside], x, z).length, 0, 'wrong-handed trim leaves the exposed side bare');
      assert.equal(topLayers([outside], bx, bz).length, 1, 'wrong-handed trim enters slab');
      close(first(floors, v(bx, 0.2, bz), down).point.y, 0, 'original floor already owns that top');
    }
  }
  t.diagnostic(
    'The ordinary strips overlap at three probes on each level; the reversed convex return occupies both original slab tops.',
  );
});

const centre = { x: 0, z: 0 },
  east = { x: 4, z: 0 },
  north = { x: 0, z: 4 };
test('the original floor supports both 90 degree walks and continues to reject the empty quadrant and decorative caps', async (t) => {
  for (const lod of [0, 1, 2]) {
    const { group, turn } = install(lod);
    const intact = await measureWallContact(group);
    try {
      let metres = 0,
        floorRays = 0;
      for (const route of [
        [east, centre, north],
        [north, centre, east],
      ]) {
        const proof = walk(intact, route);
        metres += proof.metres;
        floorRays += proof.floorRays;
      }
      close(metres, 16, 'two complete turns');
      for (const pos of [
        { x: 2.18, z: 1.029 },
        { x: 1.029, z: 2.18 },
        { x: 1.037, z: 1.029 },
      ]) {
        close(first([turn], v(pos.x, 0.2, pos.z), down).point.y, 0, 'visible physical cap');
        assert.equal(intact.surface(pos.x, pos.z), null, 'trim is excluded from floor triangles');
        assert.equal(intact.visitor.obstruction(pos), 'Floor edge');
      }
      assert.equal(hits([group], v(1.7, 0.2, 1.7), down).length, 0);
      assert.equal(intact.visitor.obstruction({ x: 1.7, z: 1.7 }), 'Floor edge');
      const corner = { x: 0.54, z: 0.54 };
      assert.equal(intact.visitor.obstruction(corner), null);
      assert.equal(
        intact.visitor.move(corner, 0.18, 0.18),
        'Floor edge',
        'body must not cut across the inside turn',
      );
      t.diagnostic(
        JSON.stringify({
          lod,
          metres,
          floorRays,
          maximumFloorCorrectionM: intact.corrections.maxDistanceMetres,
        }),
      );
    } finally {
      intact.dispose();
    }
    group.remove(turn);
    group.updateMatrixWorld(true);
    for (const arm of arms) {
      assert.equal(
        hits([group], arm.coord(2.18, 0.2, 1.029), down).length,
        0,
        'omitting trim uncovers this arm',
      );
      const exposed = first([group], arm.coord(2.18, -0.045, 1.22), arm.out.clone().negate());
      close(exposed.point[arm.radial], 1, 'uncovered cast floor edge');
    }
    const missing = await measureWallContact(group);
    try {
      for (const route of [
        [east, centre, north],
        [north, centre, east],
      ]) {
        close(walk(missing, route).metres, 8, 'the same turn remains walkable without the decorative trim');
      }
      for (const arm of arms) {
        const point = arm.coord(2.18, 0, 1.029);
        assert.equal(missing.surface(point.x, point.z), null);
      }
    } finally {
      missing.dispose();
    }
  }
});
