import { readFileSync, renameSync, writeFileSync } from 'node:fs';

const [path] = process.argv.slice(2);
const bytes = readFileSync(path);
const jsonSize = bytes.readUInt32LE(12);
const doc = JSON.parse(bytes.toString('utf8',20,20+jsonSize));
let repaired = 0;
for (const primitive of doc.meshes.flatMap(mesh=>mesh.primitives)) {
  const {NORMAL, TANGENT} = primitive.attributes;
  if (TANGENT === undefined) continue;
  const accessor = (id, width) => {
    const attr = doc.accessors[id];
    const view = doc.bufferViews[attr.bufferView];
    if (attr.componentType!==5126) throw Error('Expected float mesh attributes');
    const base = 28 + jsonSize + (view.byteOffset??0) + (attr.byteOffset??0);
    return [attr.count, i=>base+i*(view.byteStride??4*width)];
  };
  const [count,tangentOffset] = accessor(TANGENT,4);
  const [,normalOffset] = accessor(NORMAL,3);
  for (let i=0; i<count; i++) {
    const offset = tangentOffset(i);
    const tangent = [0,4,8].map(k=>bytes.readFloatLE(offset+k));
    const size = Math.hypot(...tangent);
    if (size>1e-6) continue;
    const normal = [0,4,8].map(k=>bytes.readFloatLE(normalOffset(i)+k));
    // A UV singularity has no derivative. Use a stable orthogonal tangent
    // at those exported vertices while preserving authored handedness.
    const [x,y,z] = normal;
    const fallback = Math.abs(x)<.75 ? [0,z,-y] : [-z,0,x];
    const length = Math.hypot(...fallback);
    if (!Number.isFinite(length) || length<1e-6) continue;
    fallback.forEach((v,k)=>bytes.writeFloatLE(v/length,offset+4*k));
    repaired++;
  }
}
if (repaired) {
  writeFileSync(path+'.tangent.tmp',bytes);
  renameSync(path+'.tangent.tmp',path);
  console.log('Repaired UV-singularity tangents',path,repaired);
}
