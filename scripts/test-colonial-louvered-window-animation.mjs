import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
import {launchOptions} from './browser-test-utils.mjs';
const root=process.cwd(),out=process.env.MALL_QA_DIR||path.join(root,'models/colonial-louvered-window/reports/animation-browser');
await fs.mkdir(out,{recursive:true});
const html='<!doctype html><html><head><script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script></head><body style="margin:0"><script type="module">'+`
import * as T from 'three';import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});renderer.setSize(900,650);renderer.setPixelRatio(1);renderer.setClearColor(0x303c44);document.body.append(renderer.domElement);
const scene=new T.Scene();scene.add(new T.HemisphereLight(0xffffff,0x8090a0,2.5));const light=new T.DirectionalLight(0xffffff,3);light.position.set(3,6,5);scene.add(light);
const camera=new T.PerspectiveCamera(40,900/650,.01,100);camera.position.set(4.8,3.8,6.5);camera.lookAt(0,1,0);
const bytes=await (await fetch('/gate.glb')).arrayBuffer();const model=await new GLTFLoader().parseAsync(bytes,'');scene.add(model.scene);
const mixer=new T.AnimationMixer(model.scene);const leaves=['MOVABLE_LeftLeaf','MOVABLE_RightLeaf'].map(n=>model.scene.getObjectByName(n));const rest=leaves.map(o=>({q:o.quaternion.clone(),p:o.position.clone()}));
window.pose=t=>{mixer.stopAllAction();for(const clip of model.animations){const a=mixer.clipAction(clip);a.reset();a.setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();}mixer.setTime(t);model.scene.updateMatrixWorld(true);renderer.render(scene,camera);return {angles:leaves.map((o,i)=>o.quaternion.angleTo(rest[i].q)),positions:leaves.map((o,i)=>o.position.distanceTo(rest[i].p)),clips:model.animations.map(c=>({name:c.name,duration:c.duration})),calls:renderer.info.render.calls};};
window.gateBytes=bytes.byteLength;window.gateSHA=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(x=>x.toString(16).padStart(2,'0')).join('');window.pose(0);window.ready=true;
`+'</script></body></html>';
const server=http.createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('content-type','text/html');res.end(html);return;}
let file;if(req.url==='/gate.glb')file=path.join(root,'models/colonial-louvered-window/exports/optimized.glb');
else if(req.url.startsWith('/three/')){file=path.resolve(root,'node_modules/three',req.url.slice(7));assert.ok(file.startsWith(path.resolve(root,'node_modules/three')+'/'));}
else {res.writeHead(404);res.end();return;}
res.setHeader('content-type',file.endsWith('.js')?'text/javascript':'model/gltf-binary');res.end(await fs.readFile(file));}catch(e){res.writeHead(500);res.end(String(e));}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch(launchOptions),page=await browser.newPage({viewport:{width:900,height:650}}),errors=[];
page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>errors.push(r.url()));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
try{await page.goto('http://127.0.0.1:'+server.address().port);await page.waitForFunction(()=>window.ready);const results=[];
for(const [name,t] of [['closed',0],['open',1],['reclosed',2]]){const state=await page.evaluate(t=>window.pose(t),t);assert.ok(state.calls>0);for(const a of state.angles)assert.ok(Math.abs(a-(t===1?70*Math.PI/180:0))<.005);for(const d of state.positions)assert.ok(d<1e-6);const image=await page.locator('canvas').screenshot({path:path.join(out,name+'.png')});results.push({name,t,state,pixelSHA256:createHash('sha256').update(image).digest('hex')});}
assert.notEqual(results[0].pixelSHA256,results[1].pixelSHA256);assert.equal(results[0].pixelSHA256,results[2].pixelSHA256);
const expected=await fs.readFile(path.join(root,'models/colonial-louvered-window/exports/optimized.glb'));assert.equal(await page.evaluate(()=>window.gateBytes),expected.length);assert.equal(await page.evaluate(()=>window.gateSHA),createHash('sha256').update(expected).digest('hex'));assert.deepEqual(errors,[]);
await fs.writeFile(path.join(out,'results.json'),JSON.stringify({passed:true,runtime:'Desktop Chromium WebGL, actual GLB + Three.js AnimationMixer',android:'NOT TESTED',ios:'NOT TESTED',galleryPlaybackUI:'NOT IMPLEMENTED',results,errors},null,2)+'\n');console.log('PASS gate browser animation closed/open/reclosed; exact closed pixels restored');
}finally{await browser.close();server.close();}
