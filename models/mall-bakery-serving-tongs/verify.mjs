import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = dirname(fileURLToPath(import.meta.url));
const project = createRequire(resolve('package.json'));
const { validateBytes } = project('gltf-validator');
const { Box3, Raycaster, Vector3 } = await import(new URL('three.module.js', pathToFileURL(project.resolve('three'))));
const { readGlb } = await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')));
const slug = 'mall-bakery-serving-tongs';
const levels = [];

for (let level = 0; level < 3; level++) {
  const file = 'exports/' + slug + (level ? '-lod' + level : '') + '.glb';
  const { bytes, json, scene } = await readGlb(join(root, file));
  const issues = (await validateBytes(new Uint8Array(bytes))).issues;
  assert.equal(issues.numErrors, 0);
  assert.equal(issues.numWarnings, 0);
  assert.equal(json.images?.length ?? 0, 0);
  assert.equal(json.animations?.length ?? 0, 0);
  const box = new Box3().setFromObject(scene, true);
  const bounds = [...box.min.toArray(), ...box.max.toArray()];
  [-.1014, 0, -.02265, .113, .0233, .02265].forEach((expected, i) => {
    assert.ok(Math.abs(bounds[i] - expected) < 1e-6, 'native folded utensil envelope');
  });
  const ray = (x, z) => new Raycaster(new Vector3(x, -.01, z), new Vector3(0, 1, 0), 0, .045)
    .intersectObject(scene, true)[0];
  for (const [x, z] of [[-.1, 0], [.08, -.0173], [.08, .0173]]) {
    for (const dx of [-.00025, .00025]) for (const dz of [-.00025, .00025]) {
      assert.ok(Math.abs(ray(x + dx, z + dz).point.y) < 1e-6, 'spring return and two jaws seat on the tray');
    }
  }
  for (const x of [-.04, 0, .08, .103]) assert.equal(ray(x, 0), undefined, 'open grip and jaws');
  const primitives = json.meshes.flatMap(mesh => mesh.primitives);
  const triangles = primitives.reduce((total, primitive) => total + json.accessors[primitive.indices].count / 3, 0);
  assert.ok(triangles <= [4500, 2400, 900][level]);
  assert.ok(primitives.length <= [4, 4, 3][level]);
  if (level) assert.ok(triangles < levels[level - 1].triangles);
  levels.push({ level: 'LOD' + level, file, triangles, draws: primitives.length, bytes: bytes.length,
    sha256: createHash('sha256').update(bytes).digest('hex') });
}
const report = { result: 'pass', sizeMetres: [.2144, .0233, .0453], supportProbesPerLevel: 12,
  levels, khronosErrors: 0, khronosWarnings: 0 };
writeFileSync(join(root, 'reports/assets.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify(report));
