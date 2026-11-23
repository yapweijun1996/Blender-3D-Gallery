import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { Box3, Raycaster, Vector3 } from 'three';
import validator from 'gltf-validator';

// Run from the gallery root, using its shared loader for embedded PNGs in Node.
const { readGlb, near } = await import(pathToFileURL(resolve('models/mall-floor-tile/glb.mjs')));
const pkg = new URL('.', import.meta.url);
const file = 'exports/mall-ceiling-infill-800.glb';
const { scene, json, bytes, animations } = await readGlb(new URL(file, pkg));
const report = await validator.validateBytes(bytes, { uri: file });
assert.equal(report.issues.numErrors, 0);
assert.equal(report.issues.numWarnings, 0);
assert.equal(animations.length, 0);
assert.equal(json.cameras, undefined);
const root = scene.getObjectByName('ASSET_MallCeilingInfill800');
assert.equal(root.children.length, 29);
const round = n => Number(n.toFixed(6));
const bounds = o => new Box3().setFromObject(o, true);
const point = (p, expected) => p.toArray().forEach((v,i) => near(v,expected[i]));
point(bounds(root).min, [-.6,0,-.4]);
point(bounds(root).max, [.6,.36,.4]);
const connectors = { XN:[-.6,.018,0], XP:[.6,.018,0], ZN:[0,.018,-.4], ZP:[0,.018,.4] };
for (const [name, p] of Object.entries(connectors)) {
  point(root.getObjectByName('CONNECTOR_' + name).getWorldPosition(new Vector3()),p);
}
const up = new Vector3(0,1,0), down = new Vector3(0,-1,0);
function ray(obj, x, y, z, direction) {
  return new Raycaster(new Vector3(x,y,z),direction).intersectObject(obj,true)[0];
}
for (const n of [1,2,3,4]) {
  const panel = root.getObjectByName('PANEL_' + n), b = bounds(panel);
  const x = n % 2 ? -.3 : .3, z = n <= 2 ? .3 : -.1, depth = n <= 2 ? .176 : .576;
  point(b.getSize(new Vector3()), [.576,.016,depth]);
  point(b.getCenter(new Vector3()), [x,.016,z]);
  near(ray(panel,x,-.25,z,up).point.y,.008);
  near(ray(panel,x,.25,z,down).point.y,.024);
  const rod = bounds(root.getObjectByName('HANGER_Rod_' + n));
  const cleat = bounds(root.getObjectByName('HANGER_Cleat_' + n));
  const plate = bounds(root.getObjectByName('HANGER_TopPlate_' + n));
  near(rod.min.y,cleat.max.y); near(rod.max.y,plate.min.y);
  point(rod.getCenter(new Vector3()), [n%2 ? -.48 : .48,.191,n<=2 ? .2 : -.391]);
  assert.ok(plate.min.z > -.398 && plate.max.z < .399);
}
for (const [name, z, half] of [['GRID_Main_1',.394,.006],['GRID_Main_2',.2,.012],['GRID_Main_3',-.394,.006]]) {
  const rail = root.getObjectByName(name);
  near(ray(rail,.23,-.1,z,up).point.y,0);
  near(ray(rail,.23,.1,z,down).point.y,.032);
  near(ray(rail,.23,.1,z+half-.0005,down).point.y,.004);
  assert.equal(ray(rail,.23,.1,z+half+.0005,down),undefined);
}
for (const node of json.nodes.filter(n => n.name.startsWith('HANGER_TopPlate_'))) {
  for (const primitive of json.meshes[node.mesh].primitives) {
    assert.equal(primitive.attributes.TEXCOORD_0, undefined, 'the scalar steel material uses no UV channel');
  }
}
const primitives = json.meshes.flatMap(mesh => mesh.primitives);
const triangles = primitives.reduce((total,p) => total + json.accessors[p.indices].count/3,0);
const vertices = primitives.reduce((total,p) => total + json.accessors[p.attributes.POSITION].count,0);
const image = json.images[0];
assert.equal(json.images.length,1); assert.equal(image.mimeType,'image/png');
const buffer = json.bufferViews[image.bufferView];
const binStart = 28 + bytes.readUInt32LE(12);
const embedded = bytes.subarray(binStart + buffer.byteOffset,binStart + buffer.byteOffset + buffer.byteLength);
assert.deepEqual(embedded,readFileSync(new URL('textures/mineral-fibre-original.png', pkg)));
const result = { file, sha256:createHash('sha256').update(bytes).digest('hex'), bytes:bytes.length,
  meshes:json.meshes.length, primitives:primitives.length, triangles, vertices, materials:json.materials.map(m=>m.name),
  embeddedTexturePixels:[embedded.readUInt32BE(16),embedded.readUInt32BE(20)], animations:animations.length,
  bounds:[bounds(root).min,bounds(root).max].map(p=>p.toArray().map(round)), connectors,
  khronos:{version:report.validatorVersion,errors:report.issues.numErrors,warnings:report.issues.numWarnings} };
writeFileSync(new URL('reports/geometry.json',pkg),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result));
