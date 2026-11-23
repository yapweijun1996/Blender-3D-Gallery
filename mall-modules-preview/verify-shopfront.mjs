import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { validateBytes } from 'gltf-validator';
import { Box3, Vector3 } from 'three';
import { readGlb } from '../models/mall-floor-tile/glb.mjs';
import { fasciaBaseY, shopfrontAssets, shopfrontBays, shopfrontZ } from './shopfront-layout.js';

const root = new URL('../', import.meta.url);
const assets = await Promise.all(shopfrontAssets.map(async ({ id, path }) => {
  const { scene, bytes } = await readGlb(fileURLToPath(new URL(path, root)));
  const { issues } = await validateBytes(bytes, { uri: path });
  assert.equal(issues.numErrors, 0, `${id} glTF errors`);
  assert.equal(issues.numWarnings, 0, `${id} glTF warnings`);
  return {
    id, scene,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    validator: { errors: issues.numErrors, warnings: issues.numWarnings },
  };
}));
const sources = Object.fromEntries(assets.map(({ id, scene }) => [id, scene]));
const tolerance = 1e-6;
const mm = metres => Number((metres * 1000).toFixed(3)) || 0;

function place(id, x, y) {
  const model = sources[id].clone(true);
  model.position.set(x, y, shopfrontZ);
  model.updateMatrixWorld(true);
  const meshes = [];
  model.traverse(object => {
    if (object.isMesh) meshes.push({ name: object.name, bounds: new Box3().setFromObject(object, true) });
  });
  assert.ok(meshes.length, `${id} has no meshes`);
  return { id, meshes, bounds: new Box3().setFromObject(model, true) };
}

function findIntersections(left, right) {
  const intersections = [];
  for (const a of left.meshes) {
    for (const b of right.meshes) {
      const intersection = a.bounds.clone().intersect(b.bounds);
      const dimensions = intersection.getSize(new Vector3()).toArray();
      if (dimensions.every(value => value > tolerance)) {
        intersections.push({ left: a.name, right: b.name, overlapMm: dimensions.map(mm) });
      }
    }
  }
  return intersections;
}

function checkRow(parts) {
  return parts.slice(1).map((right, index) => {
    const left = parts[index];
    const gap = right.bounds.min.x - left.bounds.max.x;
    return {
      left: left.id,
      right: right.id,
      gapMm: mm(gap),
      aligned: Math.abs(gap) <= tolerance,
      intersections: findIntersections(left, right),
    };
  });
}

const openings = shopfrontBays.map(({ opening, x }) => place(opening, x, 0));
const fascias = shopfrontBays.map(({ fascia, x }) => place(fascia, x, fasciaBaseY));
const seams = { openings: checkRow(openings), fascias: checkRow(fascias) };
const fasciaBaseGaps = fascias.map(({ bounds }, i) => bounds.min.y - openings[i].bounds.max.y);
const verified = Object.values(seams).every(row => row.length === 4 &&
  row.every(seam => seam.aligned && seam.intersections.length === 0)) &&
  fasciaBaseGaps.every(gap => Math.abs(gap) <= tolerance);

console.log(JSON.stringify({
  verified,
  inputs: assets.map(({ id, sha256, validator }) => ({ id, sha256, validator })),
  seams,
  fasciaBaseGapsMm: fasciaBaseGaps.map(mm),
}, null, 2));
assert.ok(verified, 'Shopfront rows must meet at every seam without intersecting mesh bounds');
