// Supplemental Three.js material diagnostic, not a replacement for the gallery E2E.
// Uses the unchanged shipped GLB with a checker target behind its panel.
import fs from 'node:fs/promises';import path from 'node:path';import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';import {chromium} from 'playwright';import {serveBuild,launchOptions} from './browser-test-utils.mjs';
const out=process.env.MALL_DOOR_GLASS_QA_DIR||'/tmp/mall-door-glass-material';await fs.mkdir(out,{recursive:true});
const server=await serveBuild('.'),browser=await chromium.launch(launchOptions),page=await browser.newPage({viewport:{width:800,height:700}});
const errors=[];page.on('requestfailed',r=>errors.push(r.url()+' '+r.failure()?.errorText));page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
const url=server.url+'models/mall-shopfront-door/exports/mall-shopfront-door.glb',bytes=await fs.readFile('models/mall-shopfront-door/exports/mall-shopfront-door.glb');
try{
 await page.route(server.url+'material-fixture',route=>route.fulfill({status:200,contentType:'text/html',body:'<!doctype html><html><body></body></html>'}));
 await page.goto(server.url+'material-fixture');
 await page.setContent('<style>html,body{margin:0}</style><script type="importmap">'+JSON.stringify({imports:{three:server.url+'node_modules/three/build/three.module.js','three/addons/':server.url+'node_modules/three/examples/jsm/'}})+'</script><script type="module">'+
 `import * as THREE from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
 const scene=new THREE.Scene();scene.background=new THREE.Color(0x657078);
 const camera=new THREE.PerspectiveCamera(35,800/700,.01,100);camera.position.set(0,1.2,4.8);camera.lookAt(0,1.2,0);
 const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(800,700);document.body.appendChild(renderer.domElement);
 scene.add(new THREE.HemisphereLight(0xffffff,0x535b53,2));const light=new THREE.DirectionalLight(0xffffff,2.1);light.position.set(4,7,5);scene.add(light);
 const response=await fetch('${url}');const buffer=await response.arrayBuffer();window.glassDiagnostic={status:response.status,sha256:[...new Uint8Array(await crypto.subtle.digest('SHA-256',buffer))].map(x=>x.toString(16).padStart(2,'0')).join('')};
 const gltf=await new GLTFLoader().parseAsync(buffer,'');scene.add(gltf.scene);
 const texCanvas=document.createElement('canvas');texCanvas.width=400;texCanvas.height=200;const ctx=texCanvas.getContext('2d');
 for(let y=0;y<2;y++)for(let x=0;x<4;x++){ctx.fillStyle=(x+y)%2?'#ef762c':'#ffffff';ctx.fillRect(x*100,y*100,100,100);}
 const texture=new THREE.CanvasTexture(texCanvas);texture.colorSpace=THREE.SRGBColorSpace;
 const marker=new THREE.Mesh(new THREE.PlaneGeometry(1.7,1.8),new THREE.MeshBasicMaterial({map:texture}));marker.position.set(0,1.18,-.08);scene.add(marker);
 const glass=[];gltf.scene.traverse(o=>{if(o.isMesh&&o.material.name.startsWith('GLASS '))glass.push(o);});
 window.glassDiagnostic.materials=glass.map(o=>({name:o.material.name,opacity:o.material.opacity,transparent:o.material.transparent,depthWrite:o.material.depthWrite}));
 window.setGlassMode=mode=>{for(const o of glass){o.visible=mode!=='hidden';o.material.opacity=mode==='opaque'?1:.22;o.material.needsUpdate=true;}renderer.render(scene,camera);return renderer.domElement.toDataURL();};
 window.setGlassMode('original');window.materialReady=true;
 `+'</script>');
 await page.waitForFunction(()=>window.materialReady,null,{timeout:60000});
 const data=await page.evaluate(()=>window.glassDiagnostic);assert.equal(data.status,200);assert.equal(data.sha256,createHash('sha256').update(bytes).digest('hex'));assert.ok(data.materials.length);
 for(const m of data.materials){assert.ok(m.transparent&&Math.abs(m.opacity-.22)<1e-6);}
 const hashes={};for(const mode of ['original','opaque','hidden']){await page.evaluate(m=>window.setGlassMode(m),mode);const screenshot=await page.screenshot({path:path.join(out,mode+'.png')});hashes[mode]=createHash('sha256').update(screenshot).digest('hex');}
 assert.equal(new Set(Object.values(hashes)).size,3);assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'results.json'),JSON.stringify({result:'PASS',browserVersion:browser.version(),purpose:'Diagnostic checker target behind unchanged shipped GLB, original alpha vs opaque and hidden controls',...data,screenshotHashes:hashes,errors},null,2)+'\n');
 console.log('PASS Three.js glass remains visible and differs from opaque/hidden controls');
}catch(e){console.error('Diagnostic errors:',JSON.stringify(errors));throw e;}finally{await browser.close();await server.close();}
