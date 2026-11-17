// Exercise a saved source edit in a temporary directory, preserving the delivery.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Vector3 } from 'three';
import validator from 'gltf-validator';

const here = fileURLToPath(new URL('.', import.meta.url));
const source = path.join(here, 'sources/abalone-gift-box-display.blend');
const hash = b => createHash('sha256').update(b).digest('hex');
const before = hash(await fs.readFile(source));
const temp = await fs.mkdtemp(path.join(os.tmpdir(), 'abalone-source-edit-'));
try {
  const script = `import bpy, importlib.util
from pathlib import Path
here = Path(${JSON.stringify(here)})
bpy.ops.wm.open_mainfile(filepath=${JSON.stringify(source)})
target = bpy.data.objects['BlankSignPanel']
for v in target.data.vertices: v.co.x *= .9
target.location.x += .02
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=${JSON.stringify(path.join(temp, 'edited.blend'))}, compress=True)
bpy.ops.wm.open_mainfile(filepath=${JSON.stringify(path.join(temp, 'edited.blend'))})
spec = importlib.util.spec_from_file_location('generator', here / 'generate.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
bpy.context.view_layer.update()
m.export(bpy.data.objects[m.ROOT], Path(${JSON.stringify(path.join(temp, 'edited.glb'))}))
`;
  await fs.writeFile(path.join(temp, 'edit.py'), script);
  execFileSync('/opt/homebrew/bin/blender', ['--background', '--python-exit-code', '1', '--python', path.join(temp, 'edit.py')], { stdio: 'pipe' });
  const edited = await fs.readFile(path.join(temp, 'edited.glb'));
  const original = await fs.readFile(path.join(here, 'exports/optimized.glb'));
  const validation = await validator.validateBytes(new Uint8Array(edited));
  assert.equal(validation.issues.numErrors, 0);
  assert.equal(validation.issues.numWarnings, 0);
  const signExtent = async bytes => {
    const g = await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');
    g.scene.updateMatrixWorld(true);
    const points = [];
    g.scene.traverse(o => {
      if (!o.isMesh || o.material.name !== 'SharedLacquer') return;
      for (let i = 0; i < o.geometry.attributes.position.count; i++) {
        const p = new Vector3().fromBufferAttribute(o.geometry.attributes.position, i).applyMatrix4(o.matrixWorld);
        if (p.y > .71) points.push(p.x);
      }
    });
    assert.ok(points.length > 0);
    const min = Math.min(...points), max = Math.max(...points);
    return { min, max, width: max - min, center: (min + max) / 2 };
  };
  const a = await signExtent(original), b = await signExtent(edited);
  assert.ok(Math.abs(b.width / a.width - .9) < .00001);
  assert.ok(Math.abs(b.center - a.center - .02) < .00001);
  assert.equal(hash(await fs.readFile(source)), before);
  const report = { result: 'PASS', edit: 'Saved sign mesh X width scaled to 90%; location X increased by 0.02 m; reopened and exported without regeneration',
    original: a, edited: b, original_source_unchanged: true, source_sha256: before,
    edited_glb_sha256: hash(edited), validation: { errors: 0, warnings: 0 } };
  await fs.writeFile(path.join(here, 'reports/source-edit.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
} finally {
  await fs.rm(temp, { recursive: true, force: true });
}
