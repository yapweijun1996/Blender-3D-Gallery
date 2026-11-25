// Requires the repository's pinned gltf-validator dependency (npm ci).
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { validateBytes } from 'gltf-validator';
const slug = new URL('.', import.meta.url).pathname.split('/').filter(Boolean).at(-1);
const bytes = await readFile(new URL(`exports/${slug}.glb`, import.meta.url));
assert.ok(bytes.length <= 2_000_000);
const report = await validateBytes(bytes, {uri: `${slug}.glb`});
console.log(JSON.stringify({slug, bytes: bytes.length, triangles: report.info.totalTriangleCount, issues: report.issues}));
assert.equal(report.issues.numErrors, 0); assert.equal(report.issues.numWarnings, 0);
