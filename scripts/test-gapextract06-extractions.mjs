import fs from 'node:fs';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';import {PropertyBinding,Vector3,Box3} from 'three';
const specs=JSON.parse(fs.readFileSync('scripts/batchgapextract06.json'));
const near=(a,b,label)=>assert.ok(Math.abs(a-b)<1e-5,label+': '+a+' != '+b);
for(const s of specs.filter(s=>s.parent)){
 const p='models/'+s.slug,meta=JSON.parse(fs.readFileSync(p+'/provenance/provenance.json')),proof=JSON.parse(fs.readFileSync(p+'/reports/extraction.json'));const {readGlb}=await import('../'+p+'/glb.mjs');const a=await readGlb(p+'/exports/'+s.slug+'.glb'),b=await readGlb(p+'/provenance/parent.glb');
 for(const [name,v] of Object.entries(meta.source_files))assert.equal(createHash('sha256').update(fs.readFileSync(p+'/provenance/'+name)).digest('hex'),v.sha256);
 const origin=proof.source_origin_shift_blender,shift=[origin[0],origin[2],-origin[1]],names=proof.kept_objects.filter(o=>o.type==='MESH').map(o=>o.name);let count=0;const evidence=[];
 a.scene.traverse(o=>{if(o.isMesh)count++});assert.equal(count,names.length,'No added/deleted extraction mesh');assert.equal(a.json.animations?.length??0,0);
 for(const name of names){const n=PropertyBinding.sanitizeNodeName(name),x=a.scene.getObjectByName(n),y=b.scene.getObjectByName(n);assert.ok(x?.isMesh&&y?.isMesh,'Exact selected parent node '+name);const gx=x.geometry,gy=y.geometry;
  for(const attribute of ['position','normal']){const ax=gx.attributes[attribute],ay=gy.attributes[attribute];assert.equal(ax.count,ay.count,name+' '+attribute+' count');for(let i=0;i<ax.array.length;i++)near(ax.array[i],ay.array[i],name+' '+attribute+i);}
  assert.equal(gx.index?.count,gy.index?.count);if(gx.index){const orientedTriangles=index=>{const out=[];for(let i=0;i<index.count;i+=3){const v=[index.getX(i),index.getX(i+1),index.getX(i+2)];out.push([v.join(','),[v[1],v[2],v[0]].join(','),[v[2],v[0],v[1]].join(',')].sort()[0]);}return out.sort();};assert.deepEqual(orientedTriangles(gx.index),orientedTriangles(gy.index),name+' oriented triangle multiset');}
  for(let i=0;i<16;i++){const expected=y.matrixWorld.elements[i]+(i>=12&&i<=14?shift[i-12]:0);near(x.matrixWorld.elements[i],expected,name+' world matrix '+i);}
  for(const key of ['roughness','metalness','opacity'])near(x.material[key],y.material[key],name+' '+key);assert.deepEqual(x.material.color.toArray(),y.material.color.toArray());assert.deepEqual(x.material.emissive.toArray(),y.material.emissive.toArray());evidence.push({name,vertices:gx.attributes.position.count,geometryAndMaterialsPreserved:true});
 }
 const bounds=new Box3().setFromObject(a.scene);near(bounds.min.y,0,'Grounded origin');near((bounds.min.x+bounds.max.x)/2,0,'X centred');near((bounds.min.z+bounds.max.z)/2,0,'Z centred');
 const report={result:'PASS',kind:'DERIVED EXTRACTION',parent:meta.parent_asset,parent_commit:meta.parent_commit,dependency:meta.publication,new_design_count:false,count_policy:'PENDING OWNER POLICY',sha256:createHash('sha256').update(a.bytes).digest('hex'),transform_only_glTF:shift,selected_meshes:names.length,evidence};fs.writeFileSync(p+'/reports/extraction-validation.json',JSON.stringify(report,null,2)+'\n');console.log('EXTRACTION_PASS',s.id,names.length);
}
