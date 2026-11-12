import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { Box3, Vector3, Raycaster } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { loadCatalog } from '../scripts/catalog.mjs';
const folder='models/mall-waste-sorting-station', id='mall-waste-sorting-station';
const catalog=loadCatalog();
const asset=catalog.collections.flatMap(c=>c.assets).find(a=>a.id===id);
const bytes=fs.readFileSync(`${folder}/exports/${id}.glb`);
const metadata=JSON.parse(fs.readFileSync(`${folder}/metadata/${id}.json`));
const report=JSON.parse(fs.readFileSync(`${folder}/reports/assets.json`));
const sources=JSON.parse(fs.readFileSync(`${folder}/reports/sources.json`));
const edit=JSON.parse(fs.readFileSync(`${folder}/reports/source-edit.json`));
const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
gltf.scene.updateMatrixWorld(true);
const root=gltf.scene.getObjectByName('ASSET_MallWasteSortingStation');
const groups=['StationFrame','RecycleCompartment','FoodCompartment','GeneralCompartment','RecycleLid','FoodLid','GeneralLid'];
const meshes=node=>{const result=[];node?.traverse(o=>{if(o.isMesh)result.push(o);});return result;};

test('sorting station is distinct from existing single bin and registered before mall essentials',()=>{
  assert.ok(asset); assert.ok(catalog.collections.flatMap(c=>c.assets).find(a=>a.id==='mall-trash-bin'));
  assert.equal(asset.downloadable,false); assert.equal(asset.license,metadata.rights); assert.equal(asset.root,root.name);
  assert.equal(metadata.display.previewRotationY,Math.PI);
  const index=catalog.collections.findIndex(c=>c.id===id);assert.equal(catalog.collections[index+1].id,'mall-essentials');
  assert.equal(bytes.length,metadata.metrics.glb_bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),metadata.metrics.sha256);
  assert.equal(report.sha256,metadata.metrics.sha256);assert.deepEqual(metadata.validation,report.validation);
  assert.equal(report.validation.errors,0);assert.equal(report.validation.warnings,0);assert.equal(report.animations,0);
});
test('floor-centred metre-scale station retains seven independent mesh-bearing groups',()=>{
  assert.equal(root.children.length,7);
  const bounds=new Box3().setFromObject(root), size=bounds.getSize(new Vector3());
  assert.ok(Math.abs(bounds.min.y)<.001);assert.ok(Math.abs(bounds.max.x+bounds.min.x)<.001);
  assert.ok(size.x>1.89&&size.x<1.91);assert.ok(size.y>1.34&&size.y<1.36);assert.ok(size.z>.62&&size.z<.64);
  for(const name of groups){const node=root.getObjectByName(name);assert.equal(node.parent,root);assert.ok(meshes(node).length>0);assert.ok(meshes(node).every(m=>m.geometry.attributes.position.count>0));}
});
test('all three apertures are genuinely open and lead to separate liner bottoms',()=>{
  for(const [key,x] of [['Recycle',.6],['Food',0],['General',-.6]]){
    const ray=new Raycaster(new Vector3(x,1.2,0),new Vector3(0,-1,0));
    assert.equal(ray.intersectObject(root.getObjectByName(key+'Lid'),true).length,0,'lid must not cap the aperture');
    const hits=ray.intersectObject(root.getObjectByName(key+'Compartment'),true);
    assert.ok(hits.length>0);assert.ok(hits[0].point.y>.16&&hits[0].point.y<.18,'first hit must be liner bottom, not false opening');
  }
});
test('each compartment or lid can be replaced without touching its siblings',()=>{
  for(const name of groups.filter(n=>n!=='StationFrame')){
    const target=root.getObjectByName(name),siblings=root.children.filter(n=>n!==target).map(node=>({node,meshes:meshes(node)})),before=root.children.slice();
    target.visible=false;for(const {node}of siblings)assert.equal(node.visible,true);target.visible=true;
    const replacement=target.clone(true);root.remove(target);root.add(replacement);assert.equal(target.parent,null);assert.ok(meshes(replacement).length>0);
    for(const {node,meshes:original}of siblings){assert.equal(node.parent,root);assert.deepEqual(meshes(node),original);}
    root.remove(replacement);root.add(target);root.children=before;
  }
});
test('source reopening and real source-edit export preserve editable labels and isolate changes',()=>{
  assert.equal(sources.source_reopened,'PASS');
  for(const [key,text]of [['Recycle','RECYCLE'],['Food','FOOD'],['General','GENERAL']])assert.ok(Object.values(sources.groups[key+'Lid'].editable_text).includes(text));
  assert.equal(edit.status,'PASS');assert.equal(edit.originalAssetUnchanged,true);assert.deepEqual(edit.changedGroups,['RecycleLid']);
  assert.deepEqual(edit.unchangedGroups,groups.filter(n=>n!=='RecycleLid'));
  assert.equal(edit.results[0].sha256,metadata.metrics.sha256);assert.match(metadata.replacement.note,/No live sorting/);
});
