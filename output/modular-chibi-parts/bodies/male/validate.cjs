const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const validator = require('../../../../node_modules/gltf-validator');
const here = __dirname;

function read(file) {
  const raw = fs.readFileSync(file);
  const jsonSize = raw.readUInt32LE(12);
  return { raw, doc: JSON.parse(raw.subarray(20, 20 + jsonSize)), binary: raw.subarray(28 + jsonSize) };
}

function dimensions(bytes, mime) {
  if (mime === 'image/png') return [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
  for (let i = 2; i < bytes.length;) {
    if (bytes[i] !== 0xff) break;
    const marker = bytes[i + 1];
    if ([0xc0, 0xc1, 0xc2, 0xc3].includes(marker)) {
      return [bytes.readUInt16BE(i + 7), bytes.readUInt16BE(i + 5)];
    }
    i += 2 + bytes.readUInt16BE(i + 2);
  }
  throw Error('Unknown JPEG frame header');
}

function facts(file) {
  const { raw, doc, binary } = read(file);
  const triangles = (doc.meshes || []).flatMap(m => m.primitives)
    .reduce((sum, p) => sum + (p.indices === undefined ? doc.accessors[p.attributes.POSITION].count : doc.accessors[p.indices].count) / 3, 0);
  const images = (doc.images || []).map(image => {
    const view = doc.bufferViews[image.bufferView];
    return { name: image.name, mime: image.mimeType, size: dimensions(binary.subarray(view.byteOffset || 0, (view.byteOffset || 0) + view.byteLength), image.mimeType) };
  });
  const animations = Object.fromEntries((doc.animations || []).map(a => [a.name, {
    duration: Math.max(...a.samplers.map(s => doc.accessors[s.input].max[0])),
    channels: a.channels.reduce((result, c) => ({ ...result, [c.target.path]: (result[c.target.path] || 0) + 1 }), {})
  }]));
  const parents = new Map(doc.nodes.flatMap((n,i) => (n.children || []).map(c => [c, i])));
  const hierarchy = Object.fromEntries(doc.nodes.flatMap((n,i) => n.name?.startsWith('mixamorig:')
    ? [[n.name, doc.nodes[parents.get(i)]?.name]] : []));
  const positions = (doc.meshes || []).flatMap(m => m.primitives.map(p => doc.accessors[p.attributes.POSITION]));
  const bounds = positions.length ? [0,1,2].map(i => [
    Math.min(...positions.map(p => p.min[i])), Math.max(...positions.map(p => p.max[i]))
  ]) : [];
  return {
    bytes: raw.length, sha256: crypto.createHash('sha256').update(raw).digest('hex'), triangles, images,
    skinnedNodes: doc.nodes.filter(n => n.mesh !== undefined && n.skin !== undefined).map(n => n.name),
    joints: Object.keys(hierarchy).length, animations, hierarchy, bounds
  };
}

(async () => {
  const result = {};
  const neutral = facts(path.resolve(here, '../../../../models/chibi-dressup/base_body.glb'));
  for (const name of process.argv.slice(2)) {
    const file = path.resolve(here, name);
    const data = facts(file);
    data.hierarchyMatchesNeutral = JSON.stringify(data.hierarchy) === JSON.stringify(neutral.hierarchy)
      || Object.keys(data.hierarchy).length === Object.keys(neutral.hierarchy).length
        && Object.keys(data.hierarchy).every(k => data.hierarchy[k] === neutral.hierarchy[k]);
    delete data.hierarchy;
    data.validator = await validator.validateBytes(new Uint8Array(fs.readFileSync(file)), { uri: name, maxIssues: 10000 });
    result[path.basename(name)] = data;
    const issue = data.validator.issues;
    console.log(name, data.bytes, data.triangles, issue.numErrors, issue.numWarnings);
  }
  fs.writeFileSync(path.resolve(here, 'qa/khronos.json'), JSON.stringify(result, null, 2) + '\n');
})().catch(error => { console.error(error); process.exitCode = 1; });
