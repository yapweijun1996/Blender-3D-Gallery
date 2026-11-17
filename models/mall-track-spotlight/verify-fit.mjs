import assert from 'node:assert/strict';
import { Box3, Raycaster, Vector3 } from 'three';
import validator from 'gltf-validator';
import { near, readGlb } from '../../scripts/node-glb-structure.mjs';

// Use one intact panel bay to check visual placement in the gallery's ceiling kit.
const ceiling = await readGlb(new URL('../mall-ceiling-panel/exports/mall-ceiling-panel-module.glb', import.meta.url));
const panel = ceiling.scene.getObjectByName('PANEL_1');
assert.ok(panel, 'Ceiling bay PANEL_1 must exist');
const bay = new Box3().setFromObject(panel, true);
const center = bay.getCenter(new Vector3());
const up = new Vector3(0, 1, 0);
const down = new Vector3(0, -1, 0);
const results = [];

for (const file of ['optimized.glb', 'lod1.glb']) {
  const { scene, bytes, json } = await readGlb(new URL('./exports/' + file, import.meta.url));
  const { issues } = await validator.validateBytes(new Uint8Array(bytes), { uri: file });
  assert.equal(issues.numErrors + issues.numWarnings, 0, JSON.stringify(issues.messages));
  assert.deepEqual(scene.children.map(child => child.name), ['ASSET_MallTrackSpotlight']);
  const fixture = scene.children[0];
  near(fixture.position.length(), 0);
  const bounds = new Box3().setFromObject(fixture, true);
  near(bounds.max.y, 0);
  assert.ok(bounds.min.y < 0);
  fixture.position.set(center.x, bay.min.y, center.z);
  scene.updateMatrixWorld(true);

  const placed = new Box3().setFromObject(fixture, true);
  assert.ok(placed.min.x > bay.min.x && placed.max.x < bay.max.x);
  assert.ok(placed.min.z > bay.min.z && placed.max.z < bay.max.z);
  // At both rail ends and its centre the visible rail top meets the panel underside.
  for (const x of [-0.14, 0, 0.14]) {
    const probe = new Vector3(center.x + x, bay.min.y - 1, center.z);
    const underside = new Raycaster(probe, up).intersectObject(panel, true)[0];
    probe.y = bay.min.y + 1;
    const railTop = new Raycaster(probe, down).intersectObject(fixture, true)[0];
    assert.ok(underside && railTop, 'Both surfaces must span the test position');
    near(underside.point.y, railTop.point.y);
  }

  let triangles = 0;
  fixture.traverse(part => {
    if (part.isMesh) triangles += (part.geometry.index?.count ?? part.geometry.attributes.position.count) / 3;
  });
  results.push({ file, triangles, bytes: bytes.length, materials: json.materials.length,
    dimensionsXYZ: bounds.getSize(new Vector3()).toArray(), mountY: placed.max.y });
}
assert.ok(results[1].triangles < results[0].triangles && results[1].bytes < results[0].bytes);
console.log(JSON.stringify(results, null, 2));
