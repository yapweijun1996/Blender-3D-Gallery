import assert from 'node:assert/strict';
import { readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { here, names, source, work } from './run.mjs';

export function readGlb(path) {
  const bytes = readFileSync(path);
  assert.equal(bytes.readUInt32LE(0), 0x46546c67);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonLength = bytes.readUInt32LE(12);
  const json = JSON.parse(bytes.subarray(20, 20 + jsonLength));
  assert.equal(bytes.readUInt32LE(24 + jsonLength), 0x004e4942);
  return { bytes, json, bin: bytes.subarray(28 + jsonLength) };
}

function pad(buffer, fill = 0) {
  return Buffer.concat([buffer, Buffer.alloc((4 - buffer.length % 4) % 4, fill)]);
}

function seal(json, bin) {
  json.buffers[0].byteLength = bin.length;
  const doc = pad(Buffer.from(JSON.stringify(json)), 0x20);
  const header = Buffer.alloc(20);
  [0x46546c67, 2, 28 + doc.length + bin.length, doc.length, 0x4e4f534a]
    .forEach((value, i) => header.writeUInt32LE(value, 4 * i));
  const binaryHeader = Buffer.alloc(8);
  binaryHeader.writeUInt32LE(bin.length);
  binaryHeader.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, doc, binaryHeader, bin]);
}

function withMaterials(geometry, original, options) {
  const json = structuredClone(geometry.json);
  const bin = Buffer.from(geometry.bin);
  const parts = [bin];
  const skinNode = json.nodes.findIndex(node => node.skin !== undefined);
  for (const node of json.nodes) {
    if (!node.children?.includes(skinNode)) continue;
    assert.ok(!['matrix', 'translation', 'rotation', 'scale'].some(k => k in node));
    node.children = node.children.filter(id => id !== skinNode);
    json.scenes[json.scene ?? 0].nodes.push(skinNode);
  }
  let offset = geometry.bin.length;
  for (const mesh of json.meshes) {
    for (const primitive of mesh.primitives) {
      const name = json.materials[primitive.material].name;
      const sourceIndex = original.materials.findIndex(material => material.name === name);
      assert.ok(sourceIndex >= 0, name);
      primitive.material = sourceIndex;
      const sourcePrimitive = original.meshes[0].primitives.find(p => p.material === sourceIndex);
      if (sourcePrimitive.attributes.TANGENT === undefined) delete primitive.attributes.TANGENT;
      else normalizeTangents(bin, json, primitive.attributes);
    }
  }
  for (const field of ['materials', 'textures', 'samplers', 'extensionsUsed', 'extensionsRequired']) {
    if (original[field]) json[field] = original[field];
    else delete json[field];
  }
  if (original.images) {
    json.images = original.images.map((image, i) => {
      const { blob, extension } = options[i];
      const data = pad(blob);
      const bufferView = json.bufferViews.push({ buffer: 0, byteOffset: offset, byteLength: blob.length }) - 1;
      parts.push(data);
      offset += data.length;
      return { ...image, mimeType: extension === 'png' ? 'image/png' : 'image/jpeg', bufferView };
    });
  }
  return seal(json, Buffer.concat(parts));
}

function normalizeTangents(bin, json, attrs) {
  const data = key => {
    const accessor = json.accessors[attrs[key]];
    const view = json.bufferViews[accessor.bufferView];
    assert.equal(accessor.componentType, 5126);
    return [accessor, (accessor.byteOffset ?? 0) + (view.byteOffset ?? 0)];
  };
  const [tangent, t] = data('TANGENT');
  const [, n] = data('NORMAL');
  for (let i = 0; i < tangent.count; i++) {
    const offset = t + 16 * i;
    let vector = Array.from({ length: 3 }, (_, j) => bin.readFloatLE(offset + 4 * j));
    let length = Math.hypot(...vector);
    if (length < 1e-7) {
      const [x, y, z] = Array.from({ length: 3 }, (_, j) => bin.readFloatLE(n + i * 12 + 4 * j));
      vector = Math.abs(x) < .75 ? [0, z, -y] : [-z, 0, x];
      length = Math.hypot(...vector);
    }
    for (let j = 0; j < 3; j++) bin.writeFloatLE(vector[j] / length, offset + 4 * j);
  }
}

function pack(name, stage) {
  const dir = join(work, name);
  const original = readGlb(source(name)).json;
  const selected = join(dir, stage + '.glb');
  const geo = readGlb(selected);
  const choices = (original.images ?? []).map((image, i) =>
    (image.mimeType === 'image/jpeg' ? ['jpeg'] : ['png', 'jpeg']).map(extension => ({
      blob: readFileSync(join(dir, `image-${i}.${extension}`)), extension,
      quality: extension === 'jpeg' ? 0 : image.name.includes('basecolor') ? 3 : image.name.includes('normal') ? 2 : 1,
    })));
  const combinations = choices.reduce((sets, choice) => sets.flatMap(p => choice.map(c => [...p, c])), [[]]);
  combinations.sort((a, b) => b.reduce((sum, c) => sum + c.quality, 0) - a.reduce((sum, c) => sum + c.quality, 0));
  for (const combo of combinations) {
    const packed = withMaterials(geo, original, combo);
    if (packed.length > 600_000) continue;
    const file = `npc-${name}.glb`;
    writeFileSync(join(here, file), packed);
    console.log(file, packed.length, combo.map(c => c.extension).join(', '));
    return;
  }
  throw new Error(`${name} cannot be packed under 600000 bytes`);
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const [stage, ...selected] = process.argv.slice(2);
  assert.ok(['decimated', 'fitted', 'guarded'].includes(stage), 'Expected decimated, guarded or fitted');
  const modules = selected.length ? selected : names;
  for (const name of modules) {
    assert.ok(names.includes(name), name);
    pack(name, stage);
  }
}
