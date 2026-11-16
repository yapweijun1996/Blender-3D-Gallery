import assert from 'node:assert/strict';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
// This adapter supplies PNG dimensions only. Pixel decoding/rendering is checked
// separately in Blender previews and the actual Chromium model page.
globalThis.self ??= globalThis;
globalThis.createImageBitmap ??= async blob => {
  const bytes = Buffer.from(await blob.arrayBuffer());
  assert.equal(bytes.toString('hex', 0, 8), '89504e470d0a1a0a');
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20), close() {} };
};
export const load = bytes => new GLTFLoader().parseAsync(
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '');

export async function validate() {
  const bytes = fs.readFileSync(dir + 'exports/optimized.glb');
  const json = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
  const validation = await validator.validateBytes(new Uint8Array(bytes), { maxIssues: 100 });
  fs.writeFileSync(dir + 'reports/khronos.json', JSON.stringify(validation, null, 2) + '\n');
  assert.equal(validation.issues.numErrors, 0);
  assert.equal(validation.issues.numWarnings, 0);
  assert.ok(json.buffers.every(buffer => !buffer.uri));
  assert.equal(json.images.length, 2);
  assert.ok(json.images.every(image => image.bufferView !== undefined && !image.uri));
  assert.ok(!json.cameras?.length && !json.extensions?.KHR_lights_punctual);
  assert.equal(json.meshes.length, 2);
  assert.equal(json.materials.length, 3);
  assert.ok(json.materials.every(material => (material.alphaMode ?? 'OPAQUE') === 'OPAQUE'));
  const gltf = await load(bytes);
  gltf.scene.updateMatrixWorld(true);
  const root = gltf.scene.getObjectByName('ASSET_SpeakerSoundbar');
  assert.ok(root);
  assert.deepEqual(root.position.toArray(), [0, 0, 0]);
  assert.equal(root.userData.units, 'metres');
  assert.equal(root.userData.front_axis, 'Blender -Y / glTF +Z');
  assert.equal(gltf.animations.length, 0);
  assert.deepEqual(root.children.map(object => object.name).sort(), ['FLOOR_SPEAKER', 'SOUNDBAR']);
  const nodeBounds = {};
  const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-5, `${a} != ${b}`);
  for (const name of ['SOUNDBAR', 'FLOOR_SPEAKER']) {
    const node = root.getObjectByName(name);
    near(node.position.y, 0);
    const bounds = new Box3().setFromObject(node, true);
    nodeBounds[name] = { min: bounds.min.toArray(), max: bounds.max.toArray(), size: bounds.getSize(new Vector3()).toArray() };
    near(bounds.min.y, 0);
    assert.equal(node.userData.units, 'metres');
    assert.equal(node.children.length, 3, 'one primitive per shared material on each product');
    const cloth = node.children.find(child => child.material?.map);
    assert.ok(cloth?.geometry.attributes.uv);
    assert.equal(cloth.material.map.image.width, 128);
    assert.equal(cloth.material.map.image.height, 128);
    const alloy = node.children.find(child => child.material?.name === 'Satin driver alloy');
    assert.ok(alloy, 'visible driver geometry');
    assert.ok(new Box3().setFromObject(alloy, true).max.z > .075, 'drivers face +Z');
  }
  near(nodeBounds.SOUNDBAR.size[0], .9);
  near(nodeBounds.FLOOR_SPEAKER.size[1], .9);
  assert.ok(nodeBounds.SOUNDBAR.max[0] < nodeBounds.FLOOR_SPEAKER.min[0], 'products do not overlap');
  let triangles = 0, vertices = 0, primitives = 0;
  gltf.scene.traverse(object => {
    if (!object.isMesh) return;
    const geometry = object.geometry, position = geometry.attributes.position, index = geometry.index;
    const normal = geometry.attributes.normal;
    assert.ok(normal);
    assert.ok([...position.array, ...normal.array].every(Number.isFinite));
    const count = index?.count ?? position.count;
    assert.equal(count % 3, 0);
    const a = new Vector3(), b = new Vector3(), c = new Vector3();
    for (let i = 0; i < count; i += 3) {
      a.fromBufferAttribute(position, index ? index.getX(i) : i);
      b.fromBufferAttribute(position, index ? index.getX(i + 1) : i + 1);
      c.fromBufferAttribute(position, index ? index.getX(i + 2) : i + 2);
      assert.ok(b.sub(a).cross(c.sub(a)).lengthSq() > 1e-20, 'nondegenerate triangle');
    }
    triangles += count / 3;
    vertices += position.count;
    primitives += Math.max(1, geometry.groups.length);
  });
  const bounds = new Box3().setFromObject(root, true), dimensions = bounds.getSize(new Vector3()).toArray();
  near(bounds.min.y, 0);
  near(bounds.min.x + bounds.max.x, 0);
  near(bounds.min.z + bounds.max.z, 0);
  assert.ok(triangles < 20000);
  assert.ok(bytes.length < 1572864);
  assert.equal(primitives, 6);
  const report = {
    result: 'PASS', id: 'speaker-soundbar', glb_bytes: bytes.length, triangles, vertices,
    meshes: json.meshes.length, primitives, materials: json.materials.length,
    images: json.images.length, image_dimensions: [128, 128], animations: gltf.animations.length,
    dimensions, dimensions_order: 'width, height, depth (glTF X,Y,Z)',
    bounds: { min: bounds.min.toArray(), max: bounds.max.toArray() }, nodes: nodeBounds,
    sha256: createHash('sha256').update(bytes).digest('hex'),
    validation: { errors: validation.issues.numErrors, warnings: validation.issues.numWarnings },
    texture_check_scope: 'Node structural PNG dimensions only; actual pixels rendered separately',
  };
  fs.writeFileSync(dir + 'reports/assets.json', JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report, null, 2));
  return report;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await validate();
