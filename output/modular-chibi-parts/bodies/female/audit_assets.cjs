const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const parts = path.resolve(__dirname, "..", "..");
const studio = path.join(parts, "studio-modules/body-female/work");
const neutralPath = path.resolve(parts, "../..", "models/chibi-dressup/base_body.glb");

function parse(file) {
  const glb = fs.readFileSync(file);
  const length = glb.readUInt32LE(12);
  return {
    glb,
    doc: JSON.parse(glb.subarray(20, 20 + length)),
    buffer: glb.subarray(28 + length),
  };
}

function jointNodes(asset) {
  const { nodes, skins } = asset.doc;
  const parents = new Map();
  nodes.forEach((node, i) => (node.children ?? []).forEach(j => parents.set(j, nodes[i].name)));
  return Object.fromEntries(skins[0].joints.map(index => [
    nodes[index].name, parents.get(index) === nodes.find(n => n.name === "Armature")?.name ? null :
      parents.get(index) ?? null,
  ]));
}

function jointsBind(asset) {
  const { nodes, skins } = asset.doc;
  return Object.fromEntries(skins[0].joints.map(index => [nodes[index].name, {
    translation: nodes[index].translation ?? [0, 0, 0],
    rotation: nodes[index].rotation ?? [0, 0, 0, 1],
    scale: nodes[index].scale ?? [1, 1, 1],
  }]));
}

function triangles(asset) {
  return asset.doc.meshes[0].primitives.reduce((n, p) => n + asset.doc.accessors[p.indices].count / 3, 0);
}

function payload(asset, accessor) {
  const a = asset.doc.accessors[accessor];
  const view = asset.doc.bufferViews[a.bufferView];
  assert.equal(a.byteOffset ?? 0, 0);
  return asset.buffer.subarray(view.byteOffset ?? 0, (view.byteOffset ?? 0) + view.byteLength);
}

function animationRanges(asset) {
  return Object.fromEntries(asset.doc.animations.map(anim => {
    const keys = anim.samplers.map(s => asset.doc.accessors[s.input]);
    return [anim.name, [Math.min(...keys.map(k => Math.fround(k.min[0]))), Math.max(...keys.map(k => Math.fround(k.max[0])))]];
  }));
}

function textureEvidence(name) {
  const checked = JSON.parse(fs.readFileSync(path.join(__dirname, name + ".validator.json"), "utf8"));
  const images = checked.info.resources.filter(resource => resource.image);
  assert(images.every(resource => resource.storage === "buffer-view" &&
    Math.max(resource.image.width, resource.image.height) <= 1024));
  return images.map(resource => [resource.image.width, resource.image.height]);
}

const body = parse(path.join(__dirname, "body_female.glb"));
const neutral = parse(neutralPath);
assert.deepEqual(jointNodes(body), jointNodes(neutral));
assert.equal(Object.keys(jointNodes(body)).length, 65);
assert(body.doc.nodes.some(node => node.name === "Base_Body" && node.mesh === 0 && node.skin === 0));
assert.equal(body.doc.meshes.length, 1);
assert(body.glb.length <= 1.2 * 2 ** 20 && triangles(body) <= 10000);
assert(parse(path.join(studio, "hand_gestures_female.glb")).glb.equals(
  parse(path.join(__dirname, "hand_gestures_female.glb")).glb));
const evidence = { body: { bytes: body.glb.length, triangles: triangles(body), textures: textureEvidence("body_female") } };

if (fs.existsSync(path.join(__dirname, "motion_female.glb"))) {
  const motion = parse(path.join(__dirname, "motion_female.glb"));
  assert.equal(motion.doc.meshes?.length ?? 0, 0);
  assert.deepEqual(jointsBind(motion), jointsBind(body));
  const bank = ["body-fix/motion_fixed.glb", "actions-fix/actions_fixed.glb", "actions-hold2/hold_actions.glb"];
  const ranges = Object.assign({}, ...bank.map(source => animationRanges(parse(path.join(parts, source)))));
  assert.deepEqual(animationRanges(motion), ranges);
  for (const anim of motion.doc.animations) {
    const rotationChannels = anim.channels.filter(channel => channel.target.path === "rotation");
    assert.equal(new Set(rotationChannels.map(channel => channel.target.node)).size, 65);
  }
  evidence.motion = { ranges, clips: motion.doc.animations.length };
}

for (const entry of fs.readdirSync(__dirname).filter(name => /^female-.+\.fit\.json$/.test(name))) {
  const slug = entry.slice(0, -".fit.json".length);
  const fit = JSON.parse(fs.readFileSync(path.join(__dirname, entry), "utf8"));
  const asset = parse(path.join(__dirname, slug + ".glb"));
  const source = parse(path.resolve(parts, fit.source));
  assert.deepEqual(jointNodes(asset), jointNodes(body));
  assert.deepEqual(jointsBind(asset), jointsBind(body));
  assert.deepEqual(asset.doc.materials, source.doc.materials);
  assert.deepEqual(asset.doc.textures, source.doc.textures);
  assert.deepEqual(asset.doc.samplers, source.doc.samplers);
  assert(asset.glb.length <= 1.5 * 2 ** 20);
  assert.equal(triangles(asset), triangles(source));
  const cap = slug.startsWith("female-hair") ? 3000 : 6000;
  assert(triangles(asset) <= cap);
  asset.doc.meshes[0].primitives.forEach((primitive, index) => {
    const input = source.doc.meshes[0].primitives[index];
    assert(payload(asset, primitive.indices).equals(payload(source, input.indices)));
    for (const attr of Object.keys(primitive.attributes).filter(key => /^TEXCOORD|^COLOR/.test(key))) {
      assert(payload(asset, primitive.attributes[attr]).equals(payload(source, input.attributes[attr])));
    }
  });
  evidence[slug] = { bytes: asset.glb.length, triangles: triangles(asset), textures: textureEvidence(slug),
    exactUvIndicesMaterialsAndFemaleBind: true };
}
fs.writeFileSync(path.join(__dirname, "assets_check.json"), JSON.stringify(evidence, null, 2) + "\n");
console.log("GLB contracts checked", Object.keys(evidence));
