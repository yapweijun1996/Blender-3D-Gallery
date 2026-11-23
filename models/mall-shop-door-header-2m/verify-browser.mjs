// Draw three exact header variants and the actual installed doorway in Chromium.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const base=dirname(fileURLToPath(import.meta.url));
const req=createRequire(resolve('package.json')),three=resolve(dirname(req.resolve('three')),'..');
const {chromium}=req('playwright');
const {launchOptions}=await import(pathToFileURL(resolve('scripts/browser-test-utils.mjs')).href);
const evidence=JSON.parse(await fs.readFile(resolve(base,'reports/geometry.json'),'utf8'));
const inputs={};
for(const [level,r] of Object.entries(evidence.levels))inputs[level]=resolve(base,'exports',r.file);
inputs.door=resolve('models/mall-shopfront-door/exports/mall-shopfront-door.glb');
inputs.corner=resolve('models/mall-wall-corner-2m/exports/mall-wall-corner-2m.glb');
const browser=await chromium.launch(launchOptions);
try{
 const page=await browser.newPage({viewport:{width:900,height:675},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('http://127.0.0.1:18514/**',async route=>{
   const p=new URL(route.request().url()).pathname;
   if(p==='/')return route.fulfill({contentType:'text/html',body:'<!doctype html><meta charset=utf-8><style>body{margin:0;background:#dedbd2;color:#332e25;font:16px system-ui;display:flex;flex-wrap:wrap}figure{margin:0}figcaption{padding:5px 10px}canvas{display:block}</style><script type=importmap>{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>'});
   if(p.startsWith('/models/'))return route.fulfill({path:inputs[p.slice(8)],contentType:'model/gltf-binary'});
   if(p.startsWith('/three/')&&p.endsWith('.js')){
     const path=resolve(three,p.slice(7));assert.ok(path.startsWith(three+'/'));return route.fulfill({path,contentType:'application/javascript'});
   }
   return route.fulfill({status:404,body:''});
 });
 await page.goto('http://127.0.0.1:18514/');
 const results=await page.evaluate(async()=>{
   const T=await import('three'),{GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
   const objects={},digests={};
   for(const id of ['LOD0','LOD1','LOD2','door','corner']){
     const bytes=await (await fetch('/models/'+id)).arrayBuffer();
     digests[id]=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
     objects[id]=(await new GLTFLoader().parseAsync(bytes,'')).scene;
   }
   function scene(){
     const s=new T.Scene();s.add(new T.HemisphereLight(0xfff5df,0xbac1c3,1.7));
     const l=new T.DirectionalLight(0xfff8ec,2.2);l.position.set(-3,5,6);s.add(l);return s;
   }
   function shot(s,camera,width,height,label){
     const r=new T.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});r.setClearColor(0,0);r.setSize(width,height);
     const fig=document.createElement('figure'),cap=document.createElement('figcaption');cap.textContent=label;
     fig.append(r.domElement,cap);document.body.append(fig);r.render(s,camera);
     const gl=r.getContext(),pix=new Uint8Array(4*width*height);gl.readPixels(0,0,width,height,gl.RGBA,gl.UNSIGNED_BYTE,pix);
     return {mask:Array.from({length:width*height},(_,i)=>pix[i*4+3]>127),draws:r.info.render.calls,triangles:r.info.render.triangles};
   }
   const levels=[],masks=[];
   for(const [i,name] of ['LOD0','LOD1','LOD2'].entries()){
     const s=scene();s.add(objects[name].clone(true));
     const camera=new T.OrthographicCamera(-1.18,1.18,.66,-.66,.01,30);camera.position.set(2.1,1.0,4.4);camera.lookAt(0,.19,.04);
     const view=shot(s,camera,300,165,['Close · LOD0','Middle · LOD1','Distant · LOD2'][i]);masks.push(view.mask);
     let shared=0,total=0,pixels=0;view.mask.forEach((n,j)=>{if(n)pixels++;if(n&&masks[0][j])shared++;if(n||masks[0][j])total++;});
     let texture;
     objects[name].traverse(o=>{ if(o.isMesh&&o.material.map)texture=[o.material.map.image.width,o.material.map.image.height];});
     levels.push({draws:view.draws,triangles:view.triangles,renderedPixels:pixels,texture,silhouetteIntersectionOverUnion:shared/total});
   }
   const assembly=scene();
   function place(base,x,y,z,yaw=0){const clone=base.clone(true);clone.position.set(x,y,z);clone.rotation.y=yaw;assembly.add(clone);return clone;}
   place(objects.corner,-3,0,3,Math.PI);place(objects.corner,3,0,3,-Math.PI/2);
   place(objects.LOD0,0,2.4,3);
   const frame=place(objects.door,0,0,3.135);
   frame.getObjectByName('HINGE_Left').rotation.y=-Math.PI/4;
   frame.getObjectByName('HINGE_Right').rotation.y=Math.PI/4;
   const cam=new T.PerspectiveCamera(29,900/435,.01,40);cam.position.set(2.3,2.68,10.25);cam.lookAt(0,1.43,3.02);
   const installed=shot(assembly,cam,900,435,'Installed header · original frame, wall returns and leaves opened 45°');
   return {digests,levels,installedPixels:installed.mask.filter(Boolean).length};
 });
 assert.deepEqual(errors,[]);
 for(const [i,entry] of Object.values(evidence.levels).entries()){
   const r=results.levels[i];assert.equal(results.digests['LOD'+i],entry.sha256);
   assert.equal(r.draws,entry.draws);assert.equal(r.triangles,entry.triangles);assert.deepEqual(r.texture,i===0?[512,512]:undefined);
   assert.ok(r.renderedPixels>5000 && r.silhouetteIntersectionOverUnion>.995);
 }
 assert.equal(results.digests.door,evidence.doorSha256);assert.equal(results.digests.corner,evidence.wallCornerSha256);assert.ok(results.installedPixels>45000);
 const img=await page.screenshot({path:resolve(base,'reports/installed.png')});
 const report={chromium:browser.version(),errors,...results,imageSHA256:createHash('sha256').update(img).digest('hex')};
 await fs.writeFile(resolve(base,'reports/browser.json'),JSON.stringify(report,null,2)+'\n');
 console.log(JSON.stringify(report));
}finally{await browser.close();}
