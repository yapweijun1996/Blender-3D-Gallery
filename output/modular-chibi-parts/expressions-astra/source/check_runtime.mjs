// Local r187 integration test. The file adapters decode PNGs for Node without a DOM.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { REVISION, Texture, SRGBColorSpace } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';
import { createExpressionController } from '../expression.js';

const require = createRequire(import.meta.url);
const pw = dirname(require.resolve('playwright-core/package.json'));
const { PNG } = require(resolve(pw, 'lib/utilsBundle.js'));
const root = new URL('../', import.meta.url);
const glb = await readFile(new URL('body_expressions.glb', root));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const validatorReport = await validator.validateBytes(glb, { uri: 'body_expressions.glb' });
await writeFile(new URL('checks/khronos.json', root), JSON.stringify(validatorReport, null, 2) + '\n');
assert.equal(validatorReport.issues.numErrors, 0);
assert.equal(REVISION, '187');
globalThis.self = globalThis;
globalThis.createImageBitmap = async blob => PNG.sync.read(Buffer.from(await blob.arrayBuffer()));
const scene = (await new GLTFLoader().parseAsync(glb.buffer.slice(glb.byteOffset, glb.byteOffset + glb.length), '')).scene;
const body = scene.getObjectByName('Base_Body');
const embedded = body.material.map;
const originalMaterial = body.material;
const pristine = PNG.sync.read(await readFile(new URL('textures/neutral.png', root)));
assert.deepEqual(embedded.image.data, pristine.data);
const localLoader = {
  async loadAsync(url) {
    const decoded = PNG.sync.read(await readFile(fileURLToPath(url)));
    return new Texture(decoded);
  }
};
const dir = new URL('textures/', root);
const controller = await createExpressionController(scene, dir, localLoader);
const states = {};
const names = ['happy', 'surprised', 'sad'];
for (const name of ['neutral', ...names, 'happy', 'neutral']) {
  controller.applyExpression(name);
  const map = body.material.map;
  const weights = names.map(n => body.morphTargetInfluences[body.morphTargetDictionary['expr_' + n]]);
  assert.deepEqual(weights, names.map(n => Number(n === name)));
  assert.equal(map.flipY, false);
  assert.equal(map.colorSpace, SRGBColorSpace);
  assert.equal(body.material.isMeshStandardMaterial, true);
  assert.equal(body.isSkinnedMesh, true);
  const readback = PNG.sync.read(await readFile(new URL(name + '.png', dir)));
  assert.deepEqual(map.image.data, readback.data);
  states[name] = { weights, map_rgba_sha256: hash(map.image.data), size: [map.image.width, map.image.height] };
}
assert.throws(() => controller.applyExpression('unknown'), RangeError);
controller.dispose();
assert.equal(body.material, originalMaterial);
assert.equal(body.material.map, embedded);
assert.deepEqual(body.morphTargetInfluences, [0, 0, 0]);
await writeFile(new URL('checks/three.json', root), JSON.stringify({
  three_revision: REVISION, glb_sha256: hash(glb), standard_material: true,
  method: 'Offline Node GLTFLoader.parseAsync. PNG files decoded locally with DOM image APIs adapted for Node. Map pixels and real SkinnedMesh weights checked. No GPU rendering.',
  states, selections_tested: ['neutral','happy','surprised','sad','happy','neutral'],
  unknown_name_rejected: true, dispose_restored_embedded_neutral: true
}, null, 2) + '\n');
console.log('PASS', REVISION, hash(glb), validatorReport.issues);
