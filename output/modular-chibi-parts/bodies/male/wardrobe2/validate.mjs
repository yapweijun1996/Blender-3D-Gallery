import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import validator from 'gltf-validator';

const [path, output] = process.argv.slice(2);
const bytes = readFileSync(path);
const sha256 = createHash('sha256').update(bytes).digest('hex');
const document = (file) => JSON.parse(file.toString('utf8', 20, 20 + file.readUInt32LE(12)));
const doc = document(bytes);
const body = readFileSync(new URL('../body_male.glb', import.meta.url));
const bodyDoc = document(body);
const report = await validator.validateBytes(new Uint8Array(bytes), {uri:path, maxIssues:0});
const triangles = doc.meshes.flatMap(m=>m.primitives)
  .reduce((total, p)=>total + doc.accessors[p.indices].count/3, 0);
const textures = report.info.resources.filter(r=>r.image).map(r=>[r.image.width,r.image.height]);
const [skin] = doc.skins;
const bones = (data, file) => {
  const bind = data.accessors[data.skins[0].inverseBindMatrices];
  const view = data.bufferViews[bind.bufferView];
  const parent = new Map(data.nodes.flatMap((node,i)=>(node.children??[]).map(id=>[id,i])));
  const joints = new Set(data.skins[0].joints);
  return new Map(data.skins[0].joints.map((joint,i)=>{
    const offset = 28 + file.readUInt32LE(12) + (view.byteOffset??0) + (bind.byteOffset??0) + i*(view.byteStride??64);
    return [data.nodes[joint].name, {
      parent: joints.has(parent.get(joint)) ? data.nodes[parent.get(joint)].name : null,
      bind: Array.from({length:16},(_,element)=>file.readFloatLE(offset+element*4)),
    }];
  }));
};
const expected = bones(bodyDoc,body);
const actual = bones(doc,bytes);
const sameHierarchy = actual.size===65 && [...actual].every(([name,j])=>expected.get(name)?.parent===j.parent);
const bindError = sameHierarchy ? Math.max(...[...actual].flatMap(([name,j])=>
  j.bind.map((value,i)=>Math.abs(value-expected.get(name).bind[i])))) : null;
const result = {sha256, bytes:bytes.length, triangles, textures, joints:skin.joints.length,
  sameHierarchy, bindError, errors:report.issues.numErrors, warnings:report.issues.numWarnings, report};
writeFileSync(output, JSON.stringify(result, null, 2)+'\n');
console.log({path, triangles, textures, errors:result.errors, warnings:result.warnings});
