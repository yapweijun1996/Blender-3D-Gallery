import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.launch({headless:true,args:['--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const page=await browser.newPage({viewport:{width:1200,height:900}}),errors=[];
page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
try{
 await page.goto(process.env.SAGA_DOOR_URL ?? 'http://127.0.0.1:4188/demo.html');await page.waitForFunction(()=>window.sagaRig?.doors,{timeout:60000});
 const snapshot=()=>page.evaluate(()=>{const {THREE,doors,wheels,model}=window.sagaRig;model.updateMatrixWorld(true);let result={doors:{},wheels:{}};
  for(const [id,hinge] of Object.entries(doors)){
   const meshes=[];hinge.traverse(o=>{if(o.isMesh)meshes.push(o)});
   const pane=meshes.find(o=>new RegExp(`^${id.startsWith('F')?'Front':'Rear'}_door_window(?:\\d+)?_EXPORT$`).test(o.name));
   const trim=meshes.find(o=>o.material?.name==='Black molded trim');
   const shell=meshes.find(o=>o.material?.name==='Silver metallic body');
   const card=meshes.find(o=>o.material?.name==='Dark woven seat cloth');
   if(!pane||!trim||!shell||!card)throw Error('Missing pane, black trim or shell for '+id+' '+meshes.map(m=>m.name+':'+m.material?.name));
   function point(mesh,target){const a=mesh.geometry.attributes.position;let best=Infinity,index=0;for(let i=0;i<a.count;i++){const p=mesh.localToWorld(new THREE.Vector3().fromBufferAttribute(a,i));let d=p.distanceToSquared(target);if(d<best){best=d;index=i}}return {name:mesh.name,index,position:mesh.localToWorld(new THREE.Vector3().fromBufferAttribute(a,index)).toArray(),distance:Math.sqrt(best)}}
   if(!hinge.userData.verifyPoints){const side=id.endsWith('L')?1:-1;const x=id.startsWith('F')?.09:1.06;hinge.userData.verifyPoints={pane:point(pane,new THREE.Vector3(x,.99,side*.72)),handle:point(trim,new THREE.Vector3(x,.844,side*.82)),edge:point(shell,new THREE.Vector3(id.startsWith('F')?.23:1.30,.7,side*.8)),interior:point(card,new THREE.Vector3(x,.7,side*.7))}}
   const sample=hinge.userData.verifyPoints;const now={};for(const [name,v] of Object.entries(sample)){const mesh=meshes.find(m=>m.name===v.name);now[name]=mesh.localToWorld(new THREE.Vector3().fromBufferAttribute(mesh.geometry.attributes.position,v.index)).toArray()}
   result.doors[id]={center:hinge.getWorldPosition(new THREE.Vector3()).toArray(),points:now,handleDistance:sample.handle.distance,angle:hinge.rotation.y};
  }
  for(const [id,w] of Object.entries(wheels))result.wheels[id]=w.roll.matrixWorld.toArray();
  const body=model.getObjectByName('Export_Silver_metallic_body');body.updateWorldMatrix(true,false);result.body=body.matrixWorld.toArray();return result;
 });
 const dist=(a,b)=>Math.hypot(...a.map((v,i)=>v-b[i]));const results={};
 for(const id of ['FL','FR','RL','RR']){
  await page.locator('#reset').click();await page.selectOption('#door',id);const before=await snapshot();assert.ok(before.doors[id].handleDistance<.09,`sampled trim is near handle for ${id}: ${JSON.stringify(before.doors[id])}`);await page.locator('#door-open').fill('45');const after=await snapshot();
  assert.deepEqual(after.body,before.body);assert.deepEqual(after.wheels,before.wheels);
  for(const other of ['FL','FR','RL','RR']){assert.ok(dist(before.doors[other].center,after.doors[other].center)<1e-6);for(const part of ['pane','handle','edge','interior']){const delta=dist(before.doors[other].points[part],after.doors[other].points[part]);assert.ok(other===id?delta>.05:delta<1e-5,`${id}: ${other} ${part} displacement ${delta}`)}}
  const dz=after.doors[id].points.edge[2]-before.doors[id].points.edge[2];assert.ok(id.endsWith('L')?dz>.05:dz<-.05,`${id} opens outward: ${dz}`);
  results[id]={windowHandlePanelAndInteriorMove:true,otherDoorsAndWheelsStationary:true,outwardDisplacement:dz};
  await page.evaluate(id=>{const {camera}=window.sagaRig;camera.position.set(id.startsWith('F')?-4.3:4.3,2.7,id.endsWith('L')?5:-5);camera.lookAt(0,.7,0);camera.updateProjectionMatrix()},id);
  await page.waitForTimeout(150);await page.screenshot({path:new URL(`./door-${id}-open.png`,import.meta.url).pathname});
 }
 await page.locator('#reset').click();const reset=await snapshot();assert.ok(Object.values(reset.doors).every(d=>d.angle===0));assert.deepEqual(errors,[]);
 await page.selectOption('#door','FL');await page.locator('#door-open').fill('45');await page.screenshot({path:new URL('./door-open-desktop.png',import.meta.url).pathname,fullPage:true});
 console.log(JSON.stringify({results,reset:true,errors},null,2));
 for(const width of [390,320]){await page.setViewportSize({width,height:844});await page.waitForTimeout(400);const overflow=await page.evaluate(()=>({scrollWidth:document.documentElement.scrollWidth,clientWidth:document.documentElement.clientWidth}));assert.ok(overflow.scrollWidth<=overflow.clientWidth,`overflow at ${width}: ${JSON.stringify(overflow)}`);await page.screenshot({path:new URL(`./door-open-mobile-${width}.png`,import.meta.url).pathname,fullPage:true});console.log('MOBILE',width,JSON.stringify(overflow))}
}finally{await browser.close()}
