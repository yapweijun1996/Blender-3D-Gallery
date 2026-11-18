// Keep the Tripo armature and clips while excluding its display mesh and textures.
import { readFile, writeFile } from "node:fs/promises";

const source = await readFile(new URL("../tripo-chibi-motion/motion.glb", import.meta.url));
const jsonEnd = 20 + source.readUInt32LE(12);
const input = JSON.parse(source.toString("utf8", 20, jsonEnd));
const binary = source.subarray(jsonEnd + 8);
const joints = new Set(input.skins[0].joints);
const nodes = new Map();
const data = {
  asset: input.asset,
  scene: 0,
  scenes: [{ nodes: [] }],
  nodes: [],
  animations: [],
  accessors: [],
  bufferViews: [],
  buffers: [],
};
function keepNode(index) {
  const { children, ...node } = input.nodes[index];
  nodes.set(index, data.nodes.length);
  data.nodes.push(node);
  const kept = (children ?? []).filter(child => joints.has(child)).map(keepNode);
  if (kept.length) node.children = kept;
  return nodes.get(index);
}
data.scenes[0].nodes = input.scenes[input.scene].nodes
  .filter(index => input.nodes[index].mesh === undefined).map(keepNode);

let offset = 0;
const chunks = [];
const views = new Map();
const accessors = new Map();
function keepAccessor(index) {
  if (accessors.has(index)) return accessors.get(index);
  const accessor = { ...input.accessors[index] };
  const viewIndex = accessor.bufferView;
  if (!views.has(viewIndex)) {
    const view = input.bufferViews[viewIndex];
    const original = view.byteOffset ?? 0;
    const bytes = binary.subarray(original, original + view.byteLength);
    views.set(viewIndex, data.bufferViews.length);
    data.bufferViews.push({ ...view, byteOffset: offset });
    const padding = (4 - bytes.length % 4) % 4;
    chunks.push(bytes, Buffer.alloc(padding));
    offset += bytes.length + padding;
  }
  accessor.bufferView = views.get(viewIndex);
  accessors.set(index, data.accessors.length);
  data.accessors.push(accessor);
  return accessors.get(index);
}

data.animations = input.animations.map(({ name, channels, samplers }) => ({
  name,
  channels: channels.map(({ sampler, target }) => {
    if (!joints.has(target.node) || !nodes.has(target.node)) throw new Error("Expected an armature channel");
    return { sampler, target: { ...target, node: nodes.get(target.node) } };
  }),
  samplers: samplers.map(sampler => ({
    ...sampler, input: keepAccessor(sampler.input), output: keepAccessor(sampler.output),
  })),
}));
data.buffers.push({ byteLength: offset });

const json = JSON.stringify(data);
const jsonLength = Math.ceil(Buffer.byteLength(json) / 4) * 4;
const header = Buffer.alloc(20 + jsonLength + 8, 0x20);
header.write("glTF", 0);
header.writeUInt32LE(2, 4);
header.writeUInt32LE(header.length + offset, 8);
header.writeUInt32LE(jsonLength, 12);
header.write("JSON", 16);
header.write(json, 20);
header.writeUInt32LE(offset, 20 + jsonLength);
header.writeUInt32LE(0x004e4942, 24 + jsonLength);
await writeFile(new URL("motion-clips.glb", import.meta.url), Buffer.concat([header, ...chunks]));
