import assert from "node:assert/strict";
import { createHash } from "node:crypto";
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

function channelHash(channels) {
  const hash = createHash("sha256");
  for (const name of Object.keys(channels).sort()) {
    const { times, values, interpolation } = channels[name];
    hash.update(JSON.stringify([name, interpolation, times.length, values.length]));
    hash.update(times);
    hash.update(values);
  }
  return hash.digest("hex");
}

// Channel hashes from motion.glb before the preset Run replacement.
const unchanged = {
  idle: "f5d2ebe68207df9f651adee68bf6b56e953f8a2eb53da65a5590dac30f600ce6",
  wave: "43240b02854bc0dbaed19990bd02042017218cb4ad1534f9d3fcbd72c556fa2e",
  nod: "17edee6ec5add4af1f227f7a755acd4ee8eb8492979d435d7c161e1dd4d357ca",
  jump: "2d39fdf31f3f261f441ffc2857fed8c4ba61e6c356432fb1a75f0dbddfb5b408",
  dance: "126d3ac17830ec19d6ec75347ea2f64479b018a37194bc31c26d6c6f0e929f5a",
};

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
  if (clip.name in unchanged) {
    assert.equal(channelHash(channels), unchanged[clip.name], `${clip.name}: exported channel bytes changed`);
  }
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

const run = motion.doc.animations.find(clip => clip.name === "run");
const runHips = motion.channels(run)["mixamorig:Hips.translation"];
const runFrames = Math.round((38 - 1) / 30 * 24);
assert.equal(runHips.times.length, (runFrames + 1) * 4);
const heights = [];
for (let frame = 0; frame <= runFrames; frame++) {
  assert.ok(Math.abs(runHips.times.readFloatLE(frame * 4) - frame / 24) < 1e-6,
    "Run must use the 24 fps scene timeline with the preset duration");
  heights.push(runHips.values.readFloatLE(frame * 12 + 4));
}
assert.ok(Math.max(...heights) - Math.min(...heights) > 0.02, "Run must retain vertical Hips bounce");

console.log(`PASS: Khronos 0 errors, 0 warnings; 65 joints, 39,214 triangles; clips: ${expected.join(", ")}`);
console.log(`PASS: six closed pose cycles without ground-plane root drift; preset Run ${(runFrames / 24).toFixed(2)} s at 24 fps with vertical bounce`);
console.log("PASS: Idle, Wave, Nod, Jump, Dance and original Walk channels byte-identical");
