import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const base = new URL('.', import.meta.url);
const slug = 'mall-floor-inside-mitre-2m';
const rootName = 'ASSET_MallFloorInsideMitre2m';
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-7, a + ' does not match ' + b);
const rows = [];

for (const level of [0, 1, 2]) {
  const suffix = level ? '-lod' + level : '';
  const file = 'exports/' + slug + suffix + '.glb';
  const bytes = await readFile(new URL(file, base));
  const validation = await validator.validateBytes(bytes, { uri: file });
  assert.equal(validation.issues.numErrors, 0);
  assert.equal(validation.issues.numWarnings, 0);
  const gltf = await new GLTFLoader().parseAsync(
    bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    '',
  );
  const root = gltf.scene.getObjectByName(rootName + (level ? '_LOD' + level : ''));
  assert.ok(root);
  root.updateWorldMatrix(true, true);
  const box = new Box3().setFromObject(root, true);
  const bounds = [box.min.toArray(), box.max.toArray()];
  const expected = [
    [0, -0.1, 0],
    [2, 0, 2],
  ];
  for (let i = 0; i < 2; i++) bounds[i].forEach((x, j) => close(x, expected[i][j]));
  for (const [arm, coords] of [
    ['East', [2, 0, 0.03]],
    ['PositiveZ', [0.03, 0, 2]],
  ]) {
    const socket = root.getObjectByName('CONNECTOR_InsideMitre_' + arm + '_LOD' + level);
    assert.ok(socket);
    socket
      .getWorldPosition(new Vector3())
      .toArray()
      .forEach((x, i) => close(x, coords[i]));
  }
  let triangles = 0,
    draws = 0;
  root.traverse((node) => {
    if (!node.isMesh) return;
    const geometry = node.geometry;
    triangles += (geometry.index?.count ?? geometry.attributes.position.count) / 3;
    draws++;
  });
  if (rows.length) assert.ok(triangles < rows.at(-1).triangles);
  const extras = gltf.parser.json.scenes[0].extras;
  assert.equal(extras, undefined);
  assert.equal(gltf.animations.length, 0);
  rows.push({
    level: 'LOD' + level,
    file,
    triangles,
    draws,
    bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    errors: 0,
    warnings: 0,
  });
}
console.log(JSON.stringify({ result: 'pass', variants: rows }, null, 2));
