// Run from the checkout with node models/gjh-visitor-classic/qa_modules.mjs.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { validateBytes } from 'gltf-validator';
import { createWardrobe } from './wardrobe.mjs';

const home = dirname(fileURLToPath(import.meta.url));
const exportsDir = join(home, 'exports');
const manifestBytes = await readFile(join(exportsDir, 'manifest.json'));
const manifest = JSON.parse(manifestBytes);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const loader = new GLTFLoader();
globalThis.self ??= globalThis;
loader.register(() => ({
  name: 'GeometryOnlyTexture',
  loadTexture: () => Promise.resolve(new THREE.Texture()),
}));
const parse = bytes => loader.parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.length), '');
const tolerance = 1e-5;
const report = {
  threeRevision: THREE.REVISION, maxVertexErrorMetres: tolerance,
  manifestSha256: hash(manifestBytes), files: {}, modules: {}, fingers: {}, wardrobeOrder: [],
  limitations: ['Node replaces decoded textures with placeholders. The skinning checks do not measure surface collisions.'],
};
function collect(root, matches) {
  const out = [];
  root.traverse(node => { if (matches(node)) out.push(node); });
  return out;
}
const meshes = root => collect(root, n => n.isSkinnedMesh);
const bones = root => new Map(collect(root, n => n.isBone).map(b => [b.name, b]));
function visibleToRoot(node, root) {
  for (let parent = node; parent; parent = parent.parent) {
    if (!parent.visible) return false;
    if (parent === root) return true;
  }
  return false;
}
function slotMeshes(root, key) {
  const tagged = collect(root, n => n.userData.partSlot === key);
  return [...new Set(tagged.flatMap(meshes))];
}
function paired(a, b) {
  const geometryKey = m => {
    const attr = m.geometry.attributes.position;
    return attr.count + ':' + hash(new Uint8Array(attr.array.buffer, attr.array.byteOffset, attr.array.byteLength));
  };
  const bin = new Map();
  for (const m of b) {
    const key = geometryKey(m);
    if (!bin.has(key)) bin.set(key, []);
    bin.get(key).push(m);
  }
  assert.equal(a.length, b.length, 'Skinned primitive count differs');
  return a.map(m => {
    const match = bin.get(geometryKey(m))?.pop();
    assert.ok(match, 'Missing identical indexed positions for ' + m.name);
    return [m, match];
  });
}
function worldVertices(items) {
  const point = new THREE.Vector3();
  return items.flatMap(item => Array.from({length:item.geometry.attributes.position.count}, (_, i) => {
    item.getVertexPosition(i, point);
    return item.localToWorld(point).clone();
  }));
}
function difference(a, b) {
  assert.equal(a.length, b.length);
  let max = 0;
  for (let i = 0; i < a.length; i++) max = Math.max(max, a[i].distanceTo(b[i]));
  assert.ok(Number.isFinite(max), 'Invalid vertex position');
  return max;
}
function maxError(pairs) {
  return Math.max(0, ...pairs.map(([a,b]) => difference(worldVertices([a]), worldVertices([b]))));
}
function assertBoneIdentity(items, master) {
  let count = 0;
  for (const item of items) for (const bone of item.skeleton.bones) {
    assert.equal(bone, master.get(bone.name), 'Wrong bone identity ' + bone.name);
    count++;
  }
  assert.ok(count);
  return count;
}
function syncRig(from, to) {
  for (const [name, b] of to) {
    const source = from.get(name);
    assert.ok(source, name);
    b.position.copy(source.position);
    b.quaternion.copy(source.quaternion);
    b.scale.copy(source.scale);
  }
}
const archive = new Map();
async function inspectFile(file) {
  const bytes = await readFile(join(exportsDir,file));
  const {issues} = await validateBytes(new Uint8Array(bytes), {uri:file});
  const messages = issues.messages.filter(m => m.severity < 2).slice(0, 8);
  report.files[file] = {sha256: hash(bytes), errors: issues.numErrors, warnings: issues.numWarnings, info:issues.numInfos, messages};
  archive.set(file, bytes);
}
async function run() {
  const paths = [manifest.character, ...manifest.slots.map(e=>e.file)];
  assert.equal(new Set(paths).size, paths.length);
  const diskModules = (await readdir(join(exportsDir,'modules'))).filter(f=>f.endsWith('.glb')).map(f=>'modules/'+f).sort();
  assert.deepEqual(diskModules,paths.slice(1).sort());
  for (const name of paths) await inspectFile(name);
  const visitor = await parse(archive.get(manifest.character));
  const base = visitor.scene;
  const master = bones(base);
  const originalMesh = new Map(manifest.slots.map(e => [e.slot, slotMeshes(base,e.slot)]));
  const wardrobe = createWardrobe(base);
  const rows = new Map(manifest.slots.map(e=>[e.slot,e]));
  const hide = slot => manifest.variants[slot]?.hide ?? [slot];
  const rest = new Map([...master].map(([s,b])=>[s,[b.position.clone(),b.quaternion.clone(),b.scale.clone()]]));
  function resetBones() {
    for (const [s,[p,q,k]] of rest) {
      const b=master.get(s); b.position.copy(p);b.quaternion.copy(q);b.scale.copy(k);
    }
    base.updateMatrixWorld(true);
  }
  const mixer = new THREE.AnimationMixer(base);
  const clips = visitor.animations;
  assert.deepEqual(clips.map(c=>c.name).sort(), ['idle','run','sit','stand_up','walk']);
  assert.equal(master.size,27,'Unexpected skeleton');
  report.joints = master.size;
  report.clips = clips.map(c=>c.name);
  for (const entry of manifest.slots) {
    const slot = entry.slot;
    const module = (await parse(archive.get(entry.file))).scene;
    const reference = (await parse(archive.get(entry.file))).scene;
    const newMeshes = meshes(module);
    const referenceBones = bones(reference);
    const optional = entry.optional;
    const baseMeshes = originalMesh.get(slot);
    assert.equal(baseMeshes.length === 0, optional, slot);
    assert.ok(newMeshes.length && newMeshes.length === slotMeshes(module, slot).length, slot);
    const pairs = paired(newMeshes, meshes(reference));
    const basePairs = optional ? [] : paired(newMeshes, baseMeshes);
    let maxReference = 0, maxOriginal = 0, samples = 0;
    resetBones();
    wardrobe.equip(slot, module, hide(slot));
    const counted = assertBoneIdentity(newMeshes,master);
    for (const m of newMeshes) assert.ok(visibleToRoot(m, base),slot+' invisible');
    for (const hidden of hide(slot)) for (const m of originalMesh.get(hidden)) assert.ok(!visibleToRoot(m,base), hidden+' should be hidden');
    function sample() {
      base.updateMatrixWorld(true);
      syncRig(master,referenceBones);
      reference.updateMatrixWorld(true);
      maxReference = Math.max(maxReference,maxError(pairs));
      maxOriginal = Math.max(maxOriginal,maxError(basePairs));
      samples++;
    }
    for (const clip of clips) {
      const action = mixer.clipAction(clip).reset().setLoop(THREE.LoopOnce,1);
      action.clampWhenFinished = true;
      action.play();
      for (const t of [0,.25,.50,.75,1]) { mixer.setTime(clip.duration*t); sample(); }
      action.stop();
      resetBones();
    }
    master.get('Head').rotateY(.49);
    master.get('Head').rotateX(-.19);
    sample();
    assert.ok(maxReference <= tolerance && maxOriginal <= tolerance, 'Vertex difference '+slot);
    report.modules[slot] = {sampleCount:samples,jointsByIdentity:counted,independentMaxMetres:maxReference,
      originalMaxMetres:optional?null:maxOriginal};
    wardrobe.remove(slot);
    for (const m of newMeshes) assert.ok(!visibleToRoot(m,base));
    for (const hidden of hide(slot)) for (const m of originalMesh.get(hidden)) assert.ok(visibleToRoot(m,base), hidden+' should be restored');
    resetBones();
  }
  const headSlots = ['Head','Hair','Nose','Mouth','Ear.L','Ear.R','Eye.L','Eye.R','Brow.L','Brow.R','Cheek.L','Cheek.R'];
  const headRest = new Map(headSlots.map(key=>[key,worldVertices(originalMesh.get(key))]));
  const bodyRest = worldVertices(originalMesh.get('Body'));
  master.get('Head').rotateY(.48);
  base.updateMatrixWorld(true);
  const headTravel = Object.fromEntries(headSlots.map(key=>[key,difference(headRest.get(key),worldVertices(originalMesh.get(key)))]));
  const bodyTravel = difference(bodyRest,worldVertices(originalMesh.get('Body')));
  assert.ok(Object.values(headTravel).every(v=>v>.005) && bodyTravel<=tolerance,'Head part did not follow the head, or moved the torso');
  report.headTurn = {localRotationRadians:.48,partTravelMetres:headTravel,bodyTravelMetres:bodyTravel};
  resetBones();
  const fingerNames = [...rows.keys()].filter(key=>/^(Thumb|Index|Middle|Ring|Pinky)\.[LR]$/.test(key));
  assert.equal(fingerNames.length,10);
  for (const finger of fingerNames) {
    const positions = new Map(fingerNames.map(k=>[k,worldVertices(originalMesh.get(k))]));
    const joint = master.get(THREE.PropertyBinding.sanitizeNodeName(finger));
    assert.ok(joint,finger);
    joint.rotateX(.65);
    base.updateMatrixWorld(true);
    const movement = new Map(fingerNames.map(k=>[k,difference(positions.get(k),worldVertices(originalMesh.get(k)))]));
    const other = Math.max(...[...movement].filter(([k])=>k!==finger).map(([,v])=>v));
    assert.ok(movement.get(finger)>0.001 && other<=tolerance, finger+' coupling');
    report.fingers[finger] = {motionMetres:movement.get(finger),otherFingersMaxMetres:other};
    resetBones();
  }
  for (const order of [['Hat','Jeans'],['Jeans','Hat']]) {
    const loaded = new Map();
    for (const key of order) {
      const m=(await parse(archive.get(rows.get(key).file))).scene;
      loaded.set(key,m);
      wardrobe.equip(key,m,hide(key));
    }
    for (let i=0;i<2;i++) {
      const hat=loaded.get('Hat'), jeans=loaded.get('Jeans');
      const hatPos=worldVertices(meshes(hat)),jeansPos=worldVertices(meshes(jeans));
      const hatRefs=assertBoneIdentity(meshes(hat),master),jeansRefs=assertBoneIdentity(meshes(jeans),master);
      master.get('ThighL').rotateX(.8);
      master.get('Head').rotateY(.4);
      base.updateMatrixWorld(true);
      const hatMotion=difference(hatPos,worldVertices(meshes(hat)));
      const jeansMotion=difference(jeansPos,worldVertices(meshes(jeans)));
      assert.ok(hatMotion>.01 && jeansMotion>.05,'Optional garment failed to move');
      report.wardrobeOrder.push({order,reequipped:i===1,hatRefs,jeansRefs,hatMotionMetres:hatMotion,jeansMotionMetres:jeansMotion});
      resetBones();
      if (i === 0) {
        wardrobe.remove(order[0]);
        assert.ok(meshes(loaded.get(order[1])).every(m=>visibleToRoot(m,base)), 'Removing one module hid the other');
        wardrobe.equip(order[0],loaded.get(order[0]),hide(order[0]));
      }
    }
    for (const key of order) wardrobe.remove(key);
    assert.ok([...originalMesh.values()].flat().every(m=>visibleToRoot(m,base)));
  }
  const hair=(await parse(archive.get(rows.get('Hair').file))).scene;
  const placement=new THREE.Group();
  placement.position.set(2,.3,-1);
  placement.rotation.y=.71;
  placement.scale.setScalar(1.24);
  placement.add(base);
  wardrobe.equip('Hair',hair);
  const hairPairs=paired(meshes(hair),originalMesh.get('Hair'));
  master.get('Head').rotateY(.42);
  placement.updateMatrixWorld(true);
  report.transformedCharacterHairErrorMetres = maxError(hairPairs);
  assert.ok(report.transformedCharacterHairErrorMetres<=tolerance,'Hair diverged on placed character');
  wardrobe.remove('Hair');
  base.removeFromParent();
  resetBones();
  const leg=(await parse(archive.get(rows.get('Leg.L').file))).scene;
  const denim=(await parse(archive.get(rows.get('Jeans').file))).scene;
  wardrobe.equip('Leg.L',leg);
  wardrobe.equip('Jeans',denim,hide('Jeans'));
  assert.ok(meshes(leg).every(m=>!visibleToRoot(m,base)),'Replacement leg should be covered by jeans');
  wardrobe.remove('Jeans');
  assert.ok(meshes(leg).every(m=>visibleToRoot(m,base)) && originalMesh.get('Leg.L').every(m=>!visibleToRoot(m,base)),'Replacement leg should reappear independently');
  wardrobe.remove('Leg.L');
  assert.ok([...originalMesh.values()].flat().every(m=>visibleToRoot(m,base)));
  report.overlappingVisibility = 'Equipped leg hidden by jeans; removing jeans restores the replacement leg; removing the leg restores its default.';
  for (const [name,bytes] of archive) assert.equal(hash(await readFile(join(exportsDir,name))),hash(bytes),name+' changed during test');
  assert.ok(Object.values(report.files).every(f=>f.errors===0&&f.warnings===0),'Validator findings');
}
try { await run(); report.status='PASS'; }
catch(error) { report.status='FAIL'; report.failure=error.message; console.error(error); process.exitCode=1; }
await mkdir(join(home,'qa'),{recursive:true});
await writeFile(join(home,'qa','modules.json'),JSON.stringify(report,null,2)+'\n');
console.log(report.status, Object.keys(report.files).length+' GLBs', Object.keys(report.modules).length+' modules');
