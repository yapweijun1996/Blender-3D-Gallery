import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import validator from "gltf-validator";

async function readGlb(path) {
  const bytes = await readFile(new URL(path, import.meta.url));
  const jsonEnd = 20 + bytes.readUInt32LE(12);
  const doc = JSON.parse(bytes.subarray(20, jsonEnd));
  const bin = bytes.subarray(jsonEnd + 8);

  function samples(index) {
    const accessor = doc.accessors[index];
    const view = doc.bufferViews[accessor.bufferView];
    const size = { SCALAR: 4, VEC3: 12, VEC4: 16 }[accessor.type];
    assert.ok(size && accessor.componentType === 5126 && !accessor.sparse);
    assert.equal(view.byteStride ?? size, size);
    const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
    return bin.subarray(start, start + accessor.count * size);
  }

  function channels(clip) {
    return Object.fromEntries(clip.channels.map(({ sampler, target }) => {
      const { input, output, interpolation = "LINEAR" } = clip.samplers[sampler];
      return [`${doc.nodes[target.node].name}.${target.path}`,
        { times: samples(input), values: samples(output), interpolation }];
    }));
  }

  return { bytes, doc, channels };
}

const motion = await readGlb("./motion.glb");
const report = await validator.validateBytes(new Uint8Array(motion.bytes));
assert.equal(report.issues.numErrors, 0, JSON.stringify(report.issues));
assert.equal(report.issues.numWarnings, 0, JSON.stringify(report.issues));
assert.equal(report.info.totalTriangleCount, 39214);
assert.equal(motion.doc.meshes.length, 1);
assert.equal(motion.doc.skins.length, 1);
assert.equal(motion.doc.skins[0].joints.length, 65);
const skinNode = motion.doc.nodes.findIndex(node => node.mesh === 0 && node.skin === 0);
assert.ok(motion.doc.scenes[motion.doc.scene].nodes.includes(skinNode));
assert.equal(motion.doc.images[0].mimeType, "image/jpeg");
assert.ok(motion.doc.materials[0].pbrMetallicRoughness.baseColorTexture);

const expected = ["idle", "wave", "nod", "jump", "dance", "run", "walk"];
assert.deepEqual(motion.doc.animations.map(clip => clip.name).sort(), [...expected].sort());
const original = await readGlb("../tripo-convert-405dc0a0/character.glb");
const walk = motion.doc.animations.find(clip => clip.name === "walk");
assert.deepEqual(motion.channels(walk), original.channels(original.doc.animations[0]),
  "Walk must retain every original channel, timestamp and exported value");

for (const clip of motion.doc.animations.filter(clip => clip !== walk)) {
  const channels = motion.channels(clip);
  const hips = channels["mixamorig:Hips.translation"];
  assert.ok(hips, `${clip.name} needs Hips translation`);
  assert.ok(Object.keys(channels).some(name => name.endsWith(".rotation")), clip.name);
  for (const [name, { times, values }] of Object.entries(channels)) {
    const size = values.length / (times.length / 4);
    for (let offset = 0; offset < size; offset += 4) {
      assert.ok(Math.abs(values.readFloatLE(offset) -
        values.readFloatLE(values.length - size + offset)) < 1e-6,
      `${clip.name}: endpoints differ for ${name}`);
    }
  }
  for (let offset = 0; offset < hips.values.length; offset += 12) {
    for (const axis of [0, 8]) {
      assert.ok(Math.abs(hips.values.readFloatLE(offset + axis) - hips.values.readFloatLE(axis)) < 1e-6,
        `${clip.name}: Hips drift along the ground`);
    }
  }
}

console.log(`PASS: Khronos 0 errors, 0 warnings; 65 joints, 39,214 triangles; clips: ${expected.join(", ")}`);
console.log("PASS: six closed pose cycles without ground-plane root drift; original walk samples identical");
