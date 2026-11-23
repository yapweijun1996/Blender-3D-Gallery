const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");

for (const name of process.argv.slice(2)) {
  assert(/^female-[a-z-]+\.glb$/.test(name));
  const file = path.join(__dirname, name);
  const glb = fs.readFileSync(file);
  const jsonLength = glb.readUInt32LE(12);
  const doc = JSON.parse(glb.subarray(20, 20 + jsonLength));
  const start = 28 + jsonLength;
  let cleared = 0;

  function accessor(index, componentSize) {
    const a = doc.accessors[index];
    const v = doc.bufferViews[a.bufferView];
    return {
      a, position: start + (v.byteOffset ?? 0) + (a.byteOffset ?? 0),
      stride: v.byteStride ?? 4 * componentSize,
    };
  }

  for (const primitive of doc.meshes[0].primitives) {
    const wa = accessor(primitive.attributes.WEIGHTS_0, 4);
    const index = primitive.attributes.JOINTS_0;
    const size = doc.accessors[index].componentType === 5123 ? 2 : 1;
    const ja = accessor(index, size);
    assert.equal(wa.a.componentType, 5126);
    for (let i = 0; i < ja.a.count; i++) {
      for (let j = 0; j < 4; j++) {
        const joint = ja.position + i * ja.stride + j * size;
        const weight = wa.position + i * wa.stride + j * 4;
        if (glb.readFloatLE(weight) === 0 && (glb[joint] || (size === 2 && glb[joint + 1]))) {
          glb.fill(0, joint, joint + size);
          cleared++;
        }
      }
    }
  }
  if (cleared) {
    fs.writeFileSync(file, glb);
    const report = file.replace(/\.glb$/, ".fit.json");
    const evidence = JSON.parse(fs.readFileSync(report, "utf8"));
    evidence.output_sha256 = crypto.createHash("sha256").update(glb).digest("hex");
    evidence.zero_weight_joint_slots_cleared = cleared;
    fs.writeFileSync(report, JSON.stringify(evidence, null, 2) + "\n");
  }
  console.log(name, cleared, "zero-weight joint padding entries");
}
