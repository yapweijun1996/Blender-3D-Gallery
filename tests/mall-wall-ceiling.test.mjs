import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import { assembleWallCeiling, assembleWallRun, wallRunPath } from '../mall-modules-preview/wall-run.js';
import { shellAssetPaths } from '../mall-modules-preview/shell-layout.js';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';

const ceilingSource = (await readGlb(fileURLToPath(new URL('../' + shellAssetPaths.ceiling, import.meta.url)))).scene;
const wallSource = (await readGlb(fileURLToPath(new URL('../' + wallRunPath, import.meta.url)))).scene;
const down = new Vector3(0, -1, 0), up = new Vector3(0, 1, 0);
function near(a, b, label) {
  assert.ok(Number.isFinite(a) && Math.abs(a - b) < .000001, `${label}: ${a}, expected ${b}`);
}
function cast(group, x, y, z, direction) {
  return new Raycaster(new Vector3(x, y, z), direction).intersectObject(group, true)[0];
}
function inPart(hit, prefix) {
  for (let p = hit?.object; p; p = p.parent) if (p.name.startsWith(prefix)) return true;
  return false;
}
function ceilingAndWall() {
  const roof = assembleWallCeiling(ceilingSource), wall = assembleWallRun(wallSource);
  roof.updateMatrixWorld(true); wall.updateMatrixWorld(true);
  return { roof, wall };
}

test('the five legacy cassettes keep their underside, panel recesses and hangers over a three-wall run', () => {
  const { roof, wall } = ceilingAndWall();
  assert.equal(roof.children.length, 5);
  for (const [i, part] of roof.children.entries()) {
    const x = -2.4 + 1.2 * i;
    const bounds = new Box3().setFromObject(part, true);
    near(part.position.x, x, 'cassette centre X');
    near(bounds.min.x, x - .6, 'cassette west'); near(bounds.max.x, x + .6, 'cassette east');
    near(bounds.min.z, -2, 'rear edge on wall'); near(bounds.max.z, -.8, 'aisle edge');
    near(bounds.min.y, 2.8, 'visible grid underside'); near(bounds.max.y, 3.16, 'hanger plates');
    const rods = [], plates = [];
    part.traverse(o => {
      if (o.name.startsWith('HANGER_Rod_')) rods.push(o);
      if (o.name.startsWith('HANGER_TopPlate_')) plates.push(o);
    });
    assert.equal(rods.length, 4, 'four suspension rods per cassette');
    assert.equal(plates.length, 4, 'four hanger plates per cassette');
    for (const plate of plates) near(new Box3().setFromObject(plate, true).max.y, 3.16, 'plate top');
    for (const dx of [-.3, .3]) for (const z of [-1.7, -1.1]) {
      const panel = cast(part, x + dx, 2.6, z, up);
      assert.ok(inPart(panel, 'PANEL_'), 'adjacent ceiling panel faces the aisle');
      near(panel.point.y, 2.808, 'panel underside');
      assert.equal(cast(wall, x + dx, 2.95, z, down), undefined, 'open space below the panel');
    }
  }
  for (const [i, part] of roof.children.slice(0, -1).entries()) {
    const left = part.getObjectByName('CONNECTOR_XP').getWorldPosition(new Vector3());
    const right = roof.children[i + 1].getObjectByName('CONNECTOR_XN').getWorldPosition(new Vector3());
    near(left.distanceTo(right), 0, 'cassette registration');
    near(left.y, 2.818, 'registration height above visible rail');
  }
  const bbox = new Box3().setFromObject(roof, true);
  near(bbox.min.x, -3, 'west end'); near(bbox.max.x, 3, 'east end');
});

test('continuous rear grid contacts three wall tops and transverse rails meet differently pitched joints', t => {
  const { roof, wall } = ceilingAndWall();
  let bearingPairs = 0;
  function checkBearing(x, z) {
    const underside = cast(roof, x, 2.6, z, up), top = cast(wall, x, 2.95, z, down);
    assert.ok(inPart(underside, 'GRID_') && top, `missing grid-to-wall pair at ${x},${z}`);
    near(underside.point.y - top.point.y, 0, 'wall to grid');
    bearingPairs++;
  }
  // Sample each side of staggered wall/cassette seams and the full common interval.
  const xs = Array.from({ length: 121 }, (_, i) => -2.99999 + i * 5.99998 / 120);
  for (const seam of [-1.8, -1, -.6, .6, 1, 1.8]) xs.push(seam - .00001, seam + .00001);
  for (const x of xs) for (const z of [-1.999, -1.994, -1.989]) checkBearing(x, z);
  for (let i = 1; i < 10; i++) {
    const x = -3 + i * .6;
    // Both 12 mm half flanges form one transverse rail at each cassette boundary.
    for (const dx of [-.011, .011]) {
      checkBearing(x + dx, -1.91);
      const overAisle = cast(roof, x + dx, 2.6, -1.1, up);
      assert.ok(inPart(overAisle, 'GRID_'));
      near(overAisle.point.y, 2.8, 'aisle grid');
      assert.equal(cast(wall, x + dx, 2.95, -1.1, down), undefined);
    }
  }
  for (const x of [-1, 1]) for (const dx of [-.005, .005]) {
    const top = cast(wall, x + dx, 2.95, -1.91, down);
    const panel = cast(roof, x + dx, 2.6, -1.91, up);
    assert.ok(inPart(panel, 'PANEL_'));
    near(panel.point.y - top.point.y, .008, 'recessed panel beside wall joint');
  }
  t.diagnostic(JSON.stringify({ lengthM: 6, bearingPairs, transverseRails: 9, sampledPanelGapMm: 8 }));
});

test('the old 3 m cassette elevation leaves a 200 mm gap to the fitted wall', () => {
  const { roof, wall } = ceilingAndWall();
  roof.position.y += .2;
  roof.updateMatrixWorld(true);
  for (const x of [-2, 0, 2]) {
    const top = cast(wall, x, 2.95, -1.994, down);
    const grid = cast(roof, x, 2.9, -1.994, up);
    assert.ok(top && inPart(grid, 'GRID_'));
    near(grid.point.y - top.point.y, .2, 'former mounting height');
  }
});
