import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { Box3, Vector3 } from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import validator from 'gltf-validator';

const root=path.dirname(fileURLToPath(import.meta.url));
const specs=[['post',0],['1m',1],['2m',2]];
export const reports=[], scenes=new Map();
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-5, `${a} != ${b}`);

// Weld only for connected-component bounds analysis, without modifying the asset.
// This recovers separate authored pieces even after material-wise export merging.
export function componentBounds(object) {
  object.updateMatrixWorld(true);
  const output=[];
  object.traverse(mesh=>{
    if(!mesh.isMesh) return;
    const g=mesh.geometry,p=g.attributes.position, indices=g.index;
    const keys=new Map(),parents=[], ids=[];
    for(let i=0;i<p.count;i++){
      const key=[p.getX(i),p.getY(i),p.getZ(i)].map(n=>n.toFixed(6)).join(',');
      if(!keys.has(key)){keys.set(key,parents.length);parents.push(parents.length);}
      ids.push(keys.get(key));
    }
    function find(i){while(parents[i]!==i){parents[i]=parents[parents[i]];i=parents[i];}return i;}
    function union(a,b){parents[find(a)]=find(b);}
    const count=indices?.count??p.count;
    for(let i=0;i<count;i+=3){
      const tri=[0,1,2].map(j=>ids[indices?indices.getX(i+j):i+j]);union(tri[0],tri[1]);union(tri[1],tri[2]);
    }
    const boxes=new Map();
    for(let i=0;i<p.count;i++){
      const id=find(ids[i]);if(!boxes.has(id))boxes.set(id,new Box3());
      boxes.get(id).expandByPoint(new Vector3().fromBufferAttribute(p,i).applyMatrix4(mesh.matrixWorld));
    }
    output.push(...boxes.values());
  });return output;
}

for(const [suffix,spacing] of specs){
  const id='mall-glass-railing-'+suffix,bytes=fs.readFileSync(path.join(root,'exports',id+'.glb'));
  const validation=await validator.validateBytes(new Uint8Array(bytes),{uri:id+'.glb'});
  assert.equal(validation.issues.numErrors,0);assert.equal(validation.issues.numWarnings,0);
  const json=JSON.parse(bytes.subarray(20,20+bytes.readUInt32LE(12)));
  assert.ok(!json.images?.length && json.buffers.every(b=>!b.uri));
  assert.ok(!json.cameras?.length && !json.animations?.length);
  const gltf=await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
  gltf.scene.updateMatrixWorld(true);scenes.set(id,gltf.scene);
  const bounds=new Box3().setFromObject(gltf.scene);let triangles=0,vertices=0,primitives=0;
  gltf.scene.traverse(o=>{if(o.isMesh){primitives++;vertices+=o.geometry.attributes.position.count;triangles+=(o.geometry.index?.count??o.geometry.attributes.position.count)/3;}});
  near(bounds.min.y,0);near(bounds.getSize(new Vector3()).x,spacing+.16);
  near(bounds.getSize(new Vector3()).z,.16);
  assert.ok(triangles<12000 && primitives<=16 && bytes.length<500000);
  const modules={};
  for(const name of spacing?['MODULE_Post_Left','MODULE_Post_Right','MODULE_Infill']:['MODULE_Post']){
    const o=gltf.scene.getObjectByName(name);assert.ok(o,name);
    const b=new Box3().setFromObject(o);modules[name]={origin:o.getWorldPosition(new Vector3()).toArray(),min:b.min.toArray(),max:b.max.toArray(),connectedPieces:componentBounds(o).length};
  }
  const glass=json.materials.find(m=>m.name.startsWith('GLASS '));
  if(spacing){
    assert.ok(glass);assert.equal(glass.alphaMode,'BLEND');assert.equal(glass.doubleSided,true);
    near(glass.pbrMetallicRoughness.baseColorFactor[3],.28);
    near(modules.MODULE_Infill.min[0],-spacing/2+.026);
    near(modules.MODULE_Infill.max[0],spacing/2-.026);
    near(modules.MODULE_Post_Right.origin[0]-modules.MODULE_Post_Left.origin[0],spacing);
  }
  reports.push({id,spacing,modules,glb_bytes:bytes.length,triangles,vertices,primitives,materials:json.materials.length,animations:0,
    dimensions:bounds.getSize(new Vector3()).toArray(),bounds:{min:bounds.min.toArray(),max:bounds.max.toArray()},
    sha256:createHash('sha256').update(bytes).digest('hex'),
    glass:glass?{material:glass.name,alphaMode:glass.alphaMode,alpha:glass.pbrMetallicRoughness.baseColorFactor[3],doubleSided:glass.doubleSided}:null,
    validation:{errors:0,warnings:0,validator:validation.validatorVersion}});
}

const layouts=JSON.parse(fs.readFileSync(path.join(root,'layouts.json')));
const assembly=[];
for(const layout of layouts.examples){
  assert.equal(new Set(layout.posts.map(p=>p.join(','))).size,layout.posts.length);
  const instances=layout.posts.map((p,i)=>{
    const o=scenes.get('mall-glass-railing-post').getObjectByName('MODULE_Post').clone(true);
    o.position.fromArray(p);o.updateMatrixWorld(true);return {name:'post-'+i,boxes:componentBounds(o)};
  });
  let maxError=0;
  for(const [i,link] of layout.infills.entries()){
    const source=scenes.get(link.asset),o=source.getObjectByName('MODULE_Infill').clone(true);
    o.position.fromArray(link.position);o.rotation.set(0,link.rotationY,0);o.updateMatrixWorld(true);
    const [a,b]=link.posts.map(n=>new Vector3(...layout.posts[n])),direction=b.clone().sub(a).normalize();
    const r=reports.find(r=>r.id===link.asset);
    near(a.distanceTo(b),r.spacing);
    for(const [n,x] of [r.modules.MODULE_Infill.min[0],r.modules.MODULE_Infill.max[0]].entries()){
      const endpoint=new Vector3(x,1.095,0).applyMatrix4(o.matrixWorld);
      const target=(n?b:a).clone().addScaledVector(direction,n?-.026:.026);target.y=1.095;
      const error=endpoint.distanceTo(target);maxError=Math.max(maxError,error);assert.ok(error<1e-5);
    }
    instances.push({name:'infill-'+i,boxes:componentBounds(o)});
  }
  let pairs=0,maxPenetration=0;
  for(let a=0;a<instances.length;a++)for(let b=a+1;b<instances.length;b++){
    for(const ba of instances[a].boxes)for(const bb of instances[b].boxes){
      pairs++;
      const overlap=[0,1,2].map(k=>Math.min(ba.max.getComponent(k),bb.max.getComponent(k))-Math.max(ba.min.getComponent(k),bb.min.getComponent(k)));
      if(overlap.every(v=>v>0)){
        const penetration=Math.min(...overlap);maxPenetration=Math.max(maxPenetration,penetration);
        // Flush receiver gasket deliberately projects 0.5 mm into its clamp.
        assert.ok(penetration<=.00051, `${layout.name}: ${instances[a].name}/${instances[b].name} overlap ${penetration}`);
      }
    }
  }
  assembly.push({name:layout.name,uniquePosts:layout.posts.length,infills:layout.infills.length,actualExportedConnectedPiecePairsTested:pairs,maxConnectorErrorMetres:maxError,maxIntermoduleAabbPenetrationMetres:maxPenetration,allowanceMetres:.00051,result:'PASS'});
}
fs.mkdirSync(path.join(root,'reports'),{recursive:true});
fs.writeFileSync(path.join(root,'reports/assets.json'),JSON.stringify(reports,null,2)+'\n');
fs.writeFileSync(path.join(root,'reports/assembly.json'),JSON.stringify(assembly,null,2)+'\n');
console.log(JSON.stringify({assets:reports,assembly},null,2));
