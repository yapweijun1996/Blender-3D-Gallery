import test from 'node:test';
import assert from 'node:assert/strict';
import { Group, Mesh, BoxGeometry, MeshStandardMaterial, Texture } from 'three';
import { createLatestLoader, disposeProduct } from '../src/product-studio/load.js';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};};
function resource(id){
  const scene=new Group();scene.name=id;const geometry=new BoxGeometry(1,1,1), texture=new Texture();let closed=0;texture.image={close(){closed++;}};
  const material=new MeshStandardMaterial({map:texture});scene.add(new Mesh(geometry,material),new Mesh(geometry,material));
  const counts={geometry:0,material:0,texture:0};for(const [key,obj]of Object.entries({geometry,material,texture}))obj.addEventListener('dispose',()=>counts[key]++);
  return{scene,counts,get closed(){return closed;}};
}
function harness(){const pending=[],adopted=[],errors=[],starts=[];const loader=createLatestLoader({prepare(item,signal){const d=deferred();pending.push({...d,item,signal});return d.promise;},commit(value,item){adopted.push({value,item});},release(value){disposeProduct(value.scene);},start(item){starts.push(item.id);},fail(error,item){errors.push({error,item});}});return{loader,pending,adopted,errors,starts};}
test('latest B adopts; delayed parsed A releases real shared Three resources once',async()=>{
 const h=harness(),a=resource('A'),b=resource('B');const pa=h.loader.select({id:'A'}),pb=h.loader.select({id:'B'});
 assert.equal(h.pending[0].signal.aborted,true);h.pending[1].resolve(b);await pb;h.pending[0].resolve(a);await pa;
 assert.deepEqual(h.adopted.map(x=>x.item.id),['B']);assert.deepEqual(a.counts,{geometry:1,material:1,texture:1});assert.equal(a.closed,1);assert.deepEqual(b.counts,{geometry:0,material:0,texture:0});assert.deepEqual(h.errors,[]);h.loader.dispose();disposeProduct(b.scene);
});
test('A B A reverse completions never adopt an obsolete selection',async()=>{
 const h=harness(),values=[resource('oldA'),resource('B'),resource('newA')];const promises=['A','B','A'].map(id=>h.loader.select({id}));
 h.pending[2].resolve(values[2]);await promises[2];h.pending[1].resolve(values[1]);h.pending[0].resolve(values[0]);await Promise.all(promises);
 assert.equal(h.adopted.length,1);assert.equal(h.adopted[0].value.scene.name,'newA');for(const v of values.slice(0,2))assert.equal(v.closed,1);h.loader.dispose();disposeProduct(values[2].scene);
});
test('late fetch failure cannot overwrite newer success; current error is reported',async()=>{
 const h=harness();const a=h.loader.select({id:'A'}),b=h.loader.select({id:'B'}),value=resource('B');h.pending[1].resolve(value);await b;h.pending[0].reject(new Error('late A'));await a;assert.equal(h.errors.length,0);
 const c=h.loader.select({id:'C'});h.pending[2].reject(new Error('current C'));await c;assert.equal(h.errors.length,1);assert.equal(h.errors[0].item.id,'C');disposeProduct(value.scene);h.loader.dispose();
});
test('dispose aborts request, releases late parse and prevents later starts',async()=>{
 const h=harness(),value=resource('late');const p=h.loader.select({id:'A'});h.loader.dispose();h.loader.dispose();assert.equal(h.pending[0].signal.aborted,true);h.pending[0].resolve(value);await p;await h.loader.select({id:'B'});assert.equal(h.starts.length,1);assert.equal(h.adopted.length,0);assert.equal(value.closed,1);assert.deepEqual(h.errors,[]);
});
test('failed commit releases its parsed scene and reports failure exactly once',async()=>{
 const value=resource('bad'),errors=[];const h=createLatestLoader({start(){},prepare:async()=>value,commit(){throw new Error('contract failed');},release:v=>disposeProduct(v.scene),fail:e=>errors.push(e)});await h.select({id:'bad'});assert.equal(value.closed,1);assert.equal(errors.length,1);h.dispose();
});
