import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import validator from "../../../../node_modules/gltf-validator/index.js";

const regions = [
  "head", "neck", "torso", "pelvis", "upper_arm_L", "upper_arm_R",
  "forearm_L", "forearm_R", "hand_L", "hand_R", "thigh_L", "thigh_R",
  "shin_L", "shin_R", "foot_L", "foot_R",
];

function regionForJoint(joint, height) {
  if (/^Head(?:Top_End)?$/.test(joint)) return "head";
  // The collar is midway between the Neck and Head joints on this body.
  if (joint === "Neck") return height >= 0.621 ? "head" : "neck";
  if (joint === "Hips") return height >= 0.373 ? "torso" : "pelvis";
  if (/^Spine[12]?$/.test(joint)) return "torso";
  const [, side, part] = /^(Left|Right)(.+)$/.exec(joint) ?? [];
  const limb = {
    Shoulder: "upper_arm", Arm: "upper_arm", ForeArm: "forearm",
    UpLeg: "thigh", Leg: "shin", Foot: "foot", ToeBase: "foot", Toe_End: "foot",
  }[part] ?? (part?.startsWith("Hand") ? "hand" : null);
  assert.ok(limb, `Unexpected joint: ${joint}`);
  return `${limb}_${side[0]}`;
}

function readGlb(bytes) {
  assert.equal(bytes.toString("ascii", 0, 4), "glTF");
  assert.equal(bytes.readUInt32LE(4), 2);
  assert.equal(bytes.readUInt32LE(8), bytes.length);
  const jsonEnd = 20 + bytes.readUInt32LE(12);
  assert.equal(bytes.toString("ascii", 16, 20), "JSON");
  assert.equal(bytes.toString("latin1", jsonEnd + 4, jsonEnd + 8), "BIN\0");
  assert.equal(bytes.readUInt32LE(jsonEnd), bytes.length - jsonEnd - 8);
  return [JSON.parse(bytes.toString("utf8", 20, jsonEnd)), bytes.subarray(jsonEnd + 8)];
}

function writeGlb(gltf, binary) {
  const json = Buffer.from(JSON.stringify(gltf));
  const jsonLength = Math.ceil(json.length / 4) * 4;
  const bytes = Buffer.alloc(28 + jsonLength + binary.length);
  bytes.write("glTF");
  bytes.writeUInt32LE(2, 4);
  bytes.writeUInt32LE(bytes.length, 8);
  bytes.writeUInt32LE(jsonLength, 12);
  bytes.write("JSON", 16);
  bytes.fill(0x20, 20, 20 + jsonLength);
  json.copy(bytes, 20);
  bytes.writeUInt32LE(binary.length, 20 + jsonLength);
  bytes.write("BIN", 24 + jsonLength);
  binary.copy(bytes, 28 + jsonLength);
  return bytes;
}

function splitBody(bytes) {
  const [gltf, binary] = readGlb(bytes);
  const { accessors, bufferViews, meshes, nodes, skins } = gltf;
  assert.equal(skins.length, 1);
  assert.equal(skins[0].joints.length, 65);
  assert.equal(meshes.length, 1);
  assert.equal(meshes[0].primitives.length, 1);
  const [primitive] = meshes[0].primitives;
  assert.equal(primitive.mode ?? 4, 4);
  assert.equal(primitive.targets, undefined);
  const bodyIndex = nodes.findIndex(node => node.mesh === 0 && node.skin === 0);
  assert.ok(bodyIndex >= 0);
  const parent = nodes.find(node => node.children?.includes(bodyIndex));
  assert.ok(parent && !nodes[bodyIndex].children);
  assert.ok(["matrix", "translation", "rotation", "scale"].every(key => parent[key] === undefined));
  const scene = gltf.scenes[gltf.scene ?? 0];
  assert.ok(scene.nodes.includes(nodes.indexOf(parent)));

  const componentBytes = { 5121: 1, 5123: 2, 5125: 4, 5126: 4 };
  const components = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
  function readAccessor(index) {
    const accessor = accessors[index];
    const view = bufferViews[accessor.bufferView];
    const stride = componentBytes[accessor.componentType] * components[accessor.type];
    assert.ok(stride && !accessor.sparse && view.buffer === 0 && !view.byteStride);
    const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
    return { accessor, view, stride, data: binary.subarray(offset, offset + stride * accessor.count) };
  }

  const attributes = Object.fromEntries(Object.entries(primitive.attributes)
    .map(([name, index]) => [name, readAccessor(index)]));
  const { POSITION, JOINTS_0, WEIGHTS_0 } = attributes;
  assert.equal(POSITION.accessor.componentType, 5126);
  assert.equal(JOINTS_0.accessor.componentType, 5121);
  assert.equal(WEIGHTS_0.accessor.componentType, 5126);
  assert.equal(primitive.attributes.JOINTS_1, undefined);
  const sourceIndices = readAccessor(primitive.indices);
  assert.equal(sourceIndices.stride, 2);
  const jointNames = skins[0].joints.map(index => nodes[index].name.replace(/^mixamorig:?/, ""));
  const byRegion = new Map(regions.map(region => [region, []]));
  for (let offset = 0; offset < sourceIndices.data.length; offset += 6) {
    const triangle = [0, 2, 4].map(step => sourceIndices.data.readUInt16LE(offset + step));
    const scores = new Map();
    for (const vertex of triangle) {
      const height = POSITION.data.readFloatLE(vertex * POSITION.stride + 4);
      for (let influence = 0; influence < 4; influence++) {
        const joint = JOINTS_0.data[vertex * JOINTS_0.stride + influence];
        const weight = WEIGHTS_0.data.readFloatLE(vertex * WEIGHTS_0.stride + influence * 4);
        if (weight === 0) continue;
        const region = regionForJoint(jointNames[joint], height);
        scores.set(region, (scores.get(region) ?? 0) + weight);
      }
    }
    const region = regions.reduce((best, name) => (scores.get(name) ?? 0) > (scores.get(best) ?? 0) ? name : best);
    assert.ok(scores.get(region) > 0);
    byRegion.get(region).push(...triangle);
  }

  gltf.accessors = [];
  gltf.bufferViews = [];
  gltf.meshes = [];
  const chunks = [];
  let byteLength = 0;
  function appendView(data, target) {
    const index = gltf.bufferViews.length;
    gltf.bufferViews.push({ buffer: 0, byteOffset: byteLength, byteLength: data.length, ...(target && { target }) });
    const padding = (4 - data.length % 4) % 4;
    chunks.push(data, Buffer.alloc(padding));
    byteLength += data.length + padding;
    return index;
  }
  function appendAccessor(data, accessor, target) {
    const index = gltf.accessors.length;
    gltf.accessors.push({ ...accessor, bufferView: appendView(data, target) });
    return index;
  }

  // Keep joint indices, inverse binds and texture bytes in their original order.
  for (const skin of skins) {
    const source = readAccessor(skin.inverseBindMatrices);
    skin.inverseBindMatrices = appendAccessor(source.data, source.accessor);
  }
  for (const image of gltf.images ?? []) {
    const { byteOffset = 0, byteLength: length } = bufferViews[image.bufferView];
    image.bufferView = appendView(binary.subarray(byteOffset, byteOffset + length));
  }

  const count = {};
  const regionNodes = [];
  for (const [region, triangles] of byRegion) {
    assert.ok(triangles.length, `Empty region ${region}`);
    count[region] = triangles.length / 3;
    const vertices = [...new Set(triangles)];
    const indexByVertex = new Map(vertices.map((vertex, index) => [vertex, index]));
    const indices = Buffer.alloc(triangles.length * 2);
    triangles.forEach((vertex, index) => indices.writeUInt16LE(indexByVertex.get(vertex), index * 2));
    const regionAttributes = {};
    for (const [name, { accessor, stride, data }] of Object.entries(attributes)) {
      const compact = Buffer.alloc(vertices.length * stride);
      vertices.forEach((vertex, index) => data.copy(compact, index * stride, vertex * stride, (vertex + 1) * stride));
      const { byteOffset, min, max, ...descriptor } = accessor;
      descriptor.count = vertices.length;
      if (name === "POSITION") {
        descriptor.min = [Infinity, Infinity, Infinity];
        descriptor.max = [-Infinity, -Infinity, -Infinity];
        for (let offset = 0; offset < compact.length; offset += stride) {
          for (let axis = 0; axis < 3; axis++) {
            const value = compact.readFloatLE(offset + axis * 4);
            descriptor.min[axis] = Math.min(descriptor.min[axis], value);
            descriptor.max[axis] = Math.max(descriptor.max[axis], value);
          }
        }
      }
      regionAttributes[name] = appendAccessor(compact, descriptor, 34962);
    }
    const mesh = gltf.meshes.length;
    gltf.meshes.push({ name: region, primitives: [{
      ...primitive,
      attributes: regionAttributes,
      indices: appendAccessor(indices, { componentType: 5123, count: triangles.length, type: "SCALAR" }, 34963),
    }] });
    const node = { ...nodes[bodyIndex], name: region, mesh };
    if (mesh === 0) nodes[bodyIndex] = node;
    else nodes.push(node);
    regionNodes.push(mesh === 0 ? bodyIndex : nodes.length - 1);
  }
  parent.children.splice(parent.children.indexOf(bodyIndex), 1);
  // A root skinned mesh has the same placement as under the source identity parent.
  scene.nodes.push(...regionNodes);
  assert.equal(Object.values(count).reduce((total, value) => total + value, 0), sourceIndices.accessor.count / 3);
  gltf.buffers[0].byteLength = byteLength;
  return [writeGlb(gltf, Buffer.concat(chunks, byteLength)), count];
}

const [source, output] = process.argv.slice(2);
if (!source || !output) throw new Error("Usage: node split_body_regions.mjs <body.glb> <output_directory>");
const [bytes, counts] = splitBody(readFileSync(source));
const validation = await validator.validateBytes(new Uint8Array(bytes), { uri: "base_body_regions.glb" });
writeFileSync(join(output, "validator.json"), JSON.stringify(validation, null, 2) + "\n");
console.log(`Khronos validator: ${validation.issues.numErrors} errors, ${validation.issues.numWarnings} warnings`);
assert.equal(validation.issues.numErrors, 0, "Khronos validator rejected the split body");
writeFileSync(join(output, "base_body_regions.glb"), bytes);
writeFileSync(join(output, "regions.json"), JSON.stringify(counts, null, 2) + "\n");
