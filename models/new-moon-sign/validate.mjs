// Inspect both shipped binaries, including transforms and their embedded PNGs.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {Box3, Matrix4, Quaternion, Vector3} from 'three';
import validator from 'gltf-validator';

const dir = fileURLToPath(new URL('.', import.meta.url));
const groups = ['Frame', 'Panel', 'Moon_Logo', 'Letters', 'Light_Strips', 'Mounting'];
const metadata = JSON.parse(fs.readFileSync(dir + 'metadata/new-moon-sign.json'));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const write = (name, data) => fs.writeFileSync(dir + 'reports/' + name, JSON.stringify(data, null, 2) + '\n');
const lods = {};

for (const [level, name, limit] of [['near', 'optimized', 20000], ['far', 'far-lod', 1500]]) {
  const file = 'exports/' + name + '.glb';
  const bytes = fs.readFileSync(dir + file);
  const jsonSize = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.subarray(20, 20 + jsonSize));
  const binary = bytes.subarray(28 + jsonSize);
  const checked = await validator.validateBytes(bytes, {uri: file});
  write(level === 'near' ? 'khronos.json' : 'khronos-far.json', checked);
  for (const key of ['numErrors', 'numWarnings']) assert.equal(checked.issues[key], 0, file + ' ' + key);
  assert.equal(gltf.buffers.length, 1);
  assert.equal(gltf.buffers[0].uri, undefined);
  assert.equal(gltf.cameras, undefined);
  assert.equal(gltf.animations, undefined);
  assert.equal(gltf.extensions?.KHR_lights_punctual, undefined);
  const [rootIndex, ...otherRoots] = gltf.scenes[gltf.scene ?? 0].nodes;
  assert.equal(otherRoots.length, 0);
  const root = gltf.nodes[rootIndex];
  assert.equal(root.name, 'ASSET_NewMoonSign');
  assert.equal(root.extras.units, 'metres');
  assert.deepEqual(root.translation ?? [0, 0, 0], [0, 0, 0]);
  assert.deepEqual(root.rotation ?? [0, 0, 0, 1], [0, 0, 0, 1]);
  assert.deepEqual(root.scale ?? [1, 1, 1], [1, 1, 1]);
  const groupNodes = Object.fromEntries(root.children.map(i => [gltf.nodes[i].name, gltf.nodes[i]]));
  assert.deepEqual(Object.keys(groupNodes).sort(), [...groups].sort());
  assert.equal(root.children.length, groups.length);
  const parts = {};
  const bounds = new Box3();
  let triangles = 0;
  for (const [group, node] of Object.entries(groupNodes)) {
    assert.ok(node.children.length > 0);
    function visit(part, parent) {
      const matrix = part.matrix ? new Matrix4().fromArray(part.matrix) : new Matrix4().compose(
        new Vector3(...(part.translation ?? [0, 0, 0])), new Quaternion(...(part.rotation ?? [0, 0, 0, 1])),
        new Vector3(...(part.scale ?? [1, 1, 1])));
      matrix.premultiply(parent);
      if (part.mesh !== undefined) {
        const box = new Box3();
        let count = 0;
        for (const prim of gltf.meshes[part.mesh].primitives) {
          assert.equal(prim.mode ?? 4, 4);
          assert.ok(prim.attributes.NORMAL !== undefined);
          const position = gltf.accessors[prim.attributes.POSITION];
          const view = gltf.bufferViews[position.bufferView];
          assert.equal(position.componentType, 5126);
          assert.equal(position.type, 'VEC3');
          const offset = (view.byteOffset ?? 0) + (position.byteOffset ?? 0);
          for (let i = 0; i < position.count; i++) {
            const at = offset + i * (view.byteStride ?? 12);
            const v = new Vector3(binary.readFloatLE(at), binary.readFloatLE(at+4), binary.readFloatLE(at+8));
            box.expandByPoint(v.applyMatrix4(matrix));
          }
          count += gltf.accessors[prim.indices ?? prim.attributes.POSITION].count / 3;
        }
        parts[part.name] = {group, triangles: count, min: box.min.toArray(), max: box.max.toArray()};
        bounds.union(box);
        triangles += count;
      }
      for (const i of part.children ?? []) visit(gltf.nodes[i], matrix);
    }
    visit(node, new Matrix4());
  }
  const size = bounds.getSize(new Vector3()).toArray();
  for (const [i, expected] of [3.2, .9, .35].entries()) assert.ok(Math.abs(size[i] - expected) < 1e-5);
  assert.ok(Math.abs(bounds.min.x + bounds.max.x) < 1e-6);
  assert.ok(Math.abs(bounds.min.y) < 1e-6 && Math.abs(bounds.min.z) < 1e-6);
  for (const key of ['Letters', 'Moon_Logo']) {
    const items = Object.values(parts).filter(part => part.group === key);
    for (const part of items) {
      const depth = part.max[2] - part.min[2];
      if (level === 'far') assert.ok(depth < 1e-7 && part.triangles === 2);
      else if (key === 'Letters') assert.ok(depth > .025);
      assert.ok(part.max[2] > .215);
    }
  }
  if (level === 'near') assert.ok(Object.values(parts).some(p => p.group === 'Moon_Logo' && p.max[2] - p.min[2] > .03));
  const children = group => groupNodes[group].children.map(i => gltf.nodes[i]);
  const lights = children('Light_Strips');
  assert.equal(lights.filter(o => o.name.endsWith('diffuser')).length, 3);
  assert.equal(lights.filter(o => o.name.endsWith('bezel and baffle')).length, 3);
  const straps = children('Mounting').filter(o => o.name.endsWith('keyhole strap'));
  assert.equal(straps.length, 4);
  assert.ok(straps.every(o => Math.abs(parts[o.name].min[2]) < 1e-6));
  assert.equal(groupNodes.Letters.extras.inscription, 'New Moon');
  if (level === 'near') {
    assert.deepEqual(children('Letters').map(o => o.extras.character), [...'NewMoon']);
    for (const letter of children('Letters')) {
      const mats = gltf.meshes[letter.mesh].primitives.map(p => gltf.materials[p.material].name);
      assert.deepEqual(mats.sort(), ['Brass | satin brushed','Letter | pale gold']);
    }
  } else assert.equal(children('Letters').length, 1);
  const images = gltf.images.map(image => {
    assert.equal(image.uri, undefined);
    assert.equal(image.mimeType, 'image/png');
    const v = gltf.bufferViews[image.bufferView];
    const png = binary.subarray(v.byteOffset, v.byteOffset + v.byteLength);
    assert.equal(png.toString('ascii', 12, 16), 'IHDR');
    return {name: image.name, width: png.readUInt32BE(16), height: png.readUInt32BE(20)};
  });
  if (level === 'far') {
    assert.deepEqual(images.map(p => [p.width,p.height]), [[1024,256]]);
    const material = gltf.materials.find(m => m.name.startsWith('Artwork'));
    const tex = gltf.textures[material.pbrMetallicRoughness.baseColorTexture.index];
    assert.equal(tex.source, 0);
    assert.equal(material.alphaMode, 'MASK');
  }
  assert.ok(triangles > 0 && triangles < limit, file + ' budget');
  const record = {file, triangles, glb_bytes: bytes.length, sha256: digest(bytes), dimensions_metres: size,
    bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()}, node_groups: Object.keys(groupNodes),
    materials: gltf.materials.map(m => m.name), images, validation: {errors: 0, warnings: 0}, parts};
  lods[level] = record;
  assert.equal(metadata.lods[level].triangles, triangles, 'metadata triangle count');
  assert.equal(metadata.lods[level].bytes, bytes.length, 'metadata byte count');
  console.log(`${file}: ${triangles} triangles, ${bytes.length} bytes, 6 groups, 0 errors, 0 warnings`);
}
assert.ok(lods.far.triangles < lods.near.triangles / 10);
assert.ok(lods.far.glb_bytes < lods.near.glb_bytes);
const source = fs.readFileSync(dir + metadata.paths.source);
write('assets.json', {result: 'PASS', root: 'ASSET_NewMoonSign', source_sha256: digest(source), lods});
