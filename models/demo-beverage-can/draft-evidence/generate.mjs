import fs from 'node:fs';
import path from 'node:path';

const root = path.dirname(new URL(import.meta.url).pathname);
fs.mkdirSync(path.join(root, 'exports'), { recursive: true });

const positions = [], normals = [], indices = [], meshes = [], nodes = [];
const materials = [
  { name: 'Can satin teal', pbrMetallicRoughness: { baseColorFactor: [0.03, 0.38, 0.42, 1], metallicFactor: 0.72, roughnessFactor: 0.28 } },
  { name: 'Brushed aluminium', pbrMetallicRoughness: { baseColorFactor: [0.62, 0.68, 0.7, 1], metallicFactor: 0.9, roughnessFactor: 0.22 } },
  { name: 'Original citrus mark', pbrMetallicRoughness: { baseColorFactor: [0.96, 0.58, 0.08, 1], metallicFactor: 0.05, roughnessFactor: 0.35 } },
  { name: 'Score flap accent', pbrMetallicRoughness: { baseColorFactor: [0.88, 0.16, 0.08, 1], metallicFactor: 0.25, roughnessFactor: 0.3 } },
];
function mesh(name, verts, faces, material) {
  const first = positions.length / 3;
  for (const p of verts) { positions.push(...p); normals.push(0, 1, 0); }
  for (const f of faces) indices.push(...f.map(i => i + first));
  const mi = meshes.length; meshes.push({ name, material, first, count: faces.length * 3, localIndices: faces.flatMap(f => { const a = f.map(i => i); return a.length === 3 ? a : a.slice(1,-1).flatMap((_,j) => [a[0], a[j+1], a[j+2]]); }) });
  const ni = nodes.length; nodes.push({ name, mesh: mi });
  return ni;
}
function cylinder(name, radius, y0, y1, material, segments = 48) {
  const v = [], f = [];
  for (const y of [y0, y1]) for (let i = 0; i < segments; i++) { const a = i * Math.PI * 2 / segments; v.push([radius * Math.cos(a), y, radius * Math.sin(a)]); }
  for (let i = 0; i < segments; i++) { const n = (i + 1) % segments; f.push([i, n, segments + n], [i, segments + n, segments + i]); }
  f.push(...Array.from({length: segments - 2}, (_, i) => [0, i + 2, i + 1]), ...Array.from({length: segments - 2}, (_, i) => [segments, segments + i + 1, segments + i + 2]));
  return mesh(name, v, f, material);
}
function box(name, sx, sy, sz, x, y, z, material) {
  const v = [[-sx/2,-sy/2,-sz/2],[sx/2,-sy/2,-sz/2],[sx/2,sy/2,-sz/2],[-sx/2,sy/2,-sz/2],[-sx/2,-sy/2,sz/2],[sx/2,-sy/2,sz/2],[sx/2,sy/2,sz/2],[-sx/2,sy/2,sz/2]].map(([a,b,c])=>[a+x,b+y,c+z]);
  return mesh(name, v, [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[4,0,3,7]], material);
}
const rootNode = nodes.push({ name: 'ASSET_DemoBeverageCan', children: [] }) - 1;
const body = cylinder('BODY_CanShell', .033, .002, .118, 0, 64);
const label = cylinder('LABEL_OriginalCitrusBand', .03325, .018, .103, 2, 64);
const base = cylinder('BASE_ConcaveFoot', .0315, 0, .002, 1, 64);
const top = cylinder('TOP_RealProfileRim', .0328, .118, .121, 1, 64);
const tab = box('MOVABLE_Tab', .009, .0018, .019, 0, 0, 0, 1);
const flap = box('MOVABLE_ScoreFlap', .012, .0008, .022, 0, 0, 0, 3);
nodes[tab].translation = [0, .123, -.004];
nodes[flap].translation = [0, .1215, .008];
nodes[rootNode].children = [body, label, base, top, tab, flap];

const chunks = [], accessors = [], views = [];
function accessor(values, type, componentType, target) {
  const offset = chunks.reduce((n, b) => n + b.length, 0); const bytes = componentType === 5125 ? Buffer.from(new Uint32Array(values).buffer) : Buffer.from(new Float32Array(values).buffer); chunks.push(bytes); while (chunks.reduce((n,b)=>n+b.length,0)%4) chunks.push(Buffer.alloc(1));
  const count = type === 'SCALAR' ? values.length : values.length / ({ VEC3: 3, VEC4: 4 }[type]); const a = { bufferView: views.length, componentType, count, type };
  if (type === 'SCALAR') { a.min = [Math.min(...values)]; a.max = [Math.max(...values)]; }
  if (type === 'VEC3') { a.min = [Math.min(...values.filter((_,i)=>i%3===0)),Math.min(...values.filter((_,i)=>i%3===1)),Math.min(...values.filter((_,i)=>i%3===2))]; a.max = [Math.max(...values.filter((_,i)=>i%3===0)),Math.max(...values.filter((_,i)=>i%3===1)),Math.max(...values.filter((_,i)=>i%3===2))]; }
  accessors.push(a); views.push({ buffer: 0, byteOffset: offset, byteLength: bytes.length, ...(target ? { target } : {}) }); return accessors.length - 1;
}
const pAcc = accessor(positions, 'VEC3', 5126, 34962), nAcc = accessor(normals, 'VEC3', 5126, 34962);
for (const m of meshes) { m.prim = { attributes: { POSITION: pAcc, NORMAL: nAcc }, indices: accessor(m.localIndices.map(i => i + m.first), 'SCALAR', 5125, 34963), material: m.material, mode: 4 }; }
const times = accessor([0, 1.5, 3], 'SCALAR', 5126); function track(values) { return accessor(values, 'VEC3', 5126); }
const openTab = track([0,.123,-.004, 0,.127,-.004, 0,.123,-.004]); const openFlap = track([0,.1215,.008, 0,.126,.008, 0,.1215,.008]);
const explodedTab = track([0,.123,-.004, 0,.148,-.004, 0,.123,-.004]); const explodedFlap = track([0,.1215,.008, 0,.145,.008, 0,.1215,.008]);
const animations = (name, tabOut, flapOut) => ({ name, samplers: [{ input: times, output: tabOut, interpolation: 'LINEAR' }, { input: times, output: flapOut, interpolation: 'LINEAR' }], channels: [{ sampler: 0, target: { node: tab, path: 'translation' } }, { sampler: 1, target: { node: flap, path: 'translation' } }] });
const json = { asset: { version: '2.0', generator: 'Original procedural beverage can helper; Blender-equivalent GLB fixture' }, scene: 0, scenes: [{ nodes: [rootNode] }], nodes, meshes: meshes.map(m => ({ name: m.name, primitives: [m.prim] })), materials, accessors, bufferViews: views, buffers: [{ byteLength: chunks.reduce((n,b)=>n+b.length,0) }], animations: [animations('OpenClose', openTab, openFlap), animations('Exploded', explodedTab, explodedFlap)] };
let jb = Buffer.from(JSON.stringify(json)); while (jb.length % 4) jb = Buffer.concat([jb, Buffer.from(' ')]); const bin = Buffer.concat(chunks); const header = Buffer.alloc(12); header.write('glTF',0); header.writeUInt32LE(2,4); header.writeUInt32LE(12+8+jb.length+8+bin.length,8); const jh=Buffer.alloc(8); jh.writeUInt32LE(jb.length,0); jh.write('JSON',4); const bh=Buffer.alloc(8); bh.writeUInt32LE(bin.length,0); bh.write('BIN\0',4); fs.writeFileSync(path.join(root,'exports/demo-beverage-can.glb'), Buffer.concat([header,jh,jb,bh,bin]));
