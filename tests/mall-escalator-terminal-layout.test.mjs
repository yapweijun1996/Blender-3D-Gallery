import assert from 'node:assert/strict';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { Box3, PerspectiveCamera, Raycaster, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { assembleEscalatorTerminals, escalatorTerminalPaths } from '../mall-modules-preview/escalator-terminal.js';

const entries = await Promise.all(Object.entries(escalatorTerminalPaths).map(async ([id, path]) => {
  const glb = await readGlb(fileURLToPath(new URL('../' + path, import.meta.url)));
  return [id, glb.scene];
}));
const sources = Object.fromEntries(entries);
const output = assembleEscalatorTerminals(sources);
output.group.updateMatrixWorld(true);
const ray = new Raycaster();
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-6, a + ' versus ' + b);
const samePoint = (a, b) => a.toArray().forEach((value, axis) => near(value, b[axis]));

function cast(scene, origin, direction) {
  ray.set(origin, direction.clone().normalize());
  return ray.intersectObject(scene, true)[0];
}

function inModule(object, root) {
  for (let current = object; current; current = current.parent) {
    if (current === root) return true;
  }
  return false;
}

test('the complete machine and both three-tile landings use the original deck edge as their datum', () => {
  const machine = output.group.children.find(object => object.userData.moduleId === 'escalator');
  assert.ok(machine.getObjectByName('ASSET_EscalatorV1_ID004'));
  assert.equal(machine.getObjectByName('ASSET_EscalatorV1_ID004').children.length,
    sources.escalator.getObjectByName('ASSET_EscalatorV1_ID004').children.length);
  assert.deepEqual(Object.keys(output.inspections), ['lower', 'upper']);
  for (const [key, label, sign] of [['lower', 'Lower', 1], ['upper', 'Upper', -1]]) {
    const end = output.group.children.find(object => object.userData.terminal === key);
    const original = new Box3().setFromObject(machine.getObjectByName('LANDING_' + label), true);
    const edge = sign === 1 ? original.max.z : original.min.z;
    const datum = original.max.y;
    const profile = output.inspections[key].object;
    assert.equal(end.children.length, 4);
    assert.equal(profile.parent, end);
    samePoint(profile.getWorldPosition(new Vector3()), [0, datum, edge]);
    const outward = new Vector3(0, 0, 1).transformDirection(profile.matrixWorld);
    samePoint(outward, [0, 0, sign]);
    const tiles = end.children.filter(o => o.userData.moduleId === 'floor2m');
    assert.equal(tiles.length, 3);
    for (const x of [-2, 0, 2]) {
      const tile = tiles.find(o => o.position.x === x);
      samePoint(tile.getWorldPosition(new Vector3()), [x, datum - .1, edge + sign * (x === 0 ? 1.12 : 1)]);
      const towardsSlab = new Vector3(0, -1, 0);
      for (const [width, depth] of x === 0 ? [[-.96,.122],[0,1],[.96,.122]] :
        [[x<0?-1.003:1.003,.004],[x<0?-1.003:1.003,.117],[x,1]]) {
        const surface = cast(tile, new Vector3(width,datum+.03,edge+sign*depth), towardsSlab);
        assert.ok(surface);near(surface.point.y,datum);
      }
    }
  }
});

test('each detail camera can see both machine-facing shoulders and the full width of the floor joint', () => {
  for (const focus of Object.values(output.inspections)) {
    const profile = focus.object;
    const target = profile.localToWorld(new Vector3(...focus.target));
    const direction = new Vector3(...focus.direction).transformDirection(profile.matrixWorld);
    for (const [width, height] of [[900,560], [390,530]]) {
      const camera = new PerspectiveCamera(34, width/height, .01, 70);
      const half = camera.fov * Math.PI / 360;
      const distance = focus.radius / Math.sin(Math.min(half, Math.atan(Math.tan(half) * camera.aspect)));
      camera.position.copy(target).addScaledVector(direction,distance);
      camera.lookAt(target);camera.updateMatrixWorld(true);
      const surfacePoints = [
        [-.88,-.042,0],[.88,-.042,0],
        [-.985,0,.055],[0,0,.055],[.985,0,.055],
      ];
      for (const point of surfacePoints) {
        const world = profile.localToWorld(new Vector3(...point));
        const ndc = world.clone().project(camera);
        assert.ok(Math.abs(ndc.x)<.95 && Math.abs(ndc.y)<.90, 'inspect targets fit the canvas');
        const first = cast(output.group, camera.position, world.clone().sub(camera.position));
        assert.ok(first && inModule(first.object,profile), 'camera sees the transition rather than adjacent machinery');
        assert.ok(world.distanceTo(first.point)<.006, 'requested face is visible');
      }
    }
  }
});
