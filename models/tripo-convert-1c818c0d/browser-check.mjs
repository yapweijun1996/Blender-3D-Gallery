import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import http from 'node:http';
import { chromium } from 'playwright';
import { launchOptions } from '../../scripts/browser-test-utils.mjs';
const root = process.cwd();
const output = process.env.TRIPO_QA_DIR;
const sourcePath = process.env.TRIPO_SOURCE_SAMPLES;
if (!sourcePath) throw Error('Set TRIPO_SOURCE_SAMPLES to the audit-source.py output');
const source = JSON.parse(await fs.readFile(sourcePath, 'utf8'));
if (!output) throw Error('Set TRIPO_QA_DIR to a fresh output directory');
await fs.mkdir(output, { recursive: true });
const html = `<!doctype html><html><head><script type="importmap">{"imports":{"three":"/node_modules/three/build/three.module.js"}}</script></head><body style="margin:0"><script type="module">
import * as T from 'three'; import {GLTFLoader} from '/node_modules/three/examples/jsm/loaders/GLTFLoader.js';
const g = await new GLTFLoader().loadAsync('/models/tripo-convert-1c818c0d/character.glb');
const scene = new T.Scene(); scene.background = new T.Color('#353535'); scene.add(g.scene);
scene.add(new T.HemisphereLight(0xffffff,0x888899,2)); const light=new T.DirectionalLight(0xffffff,2); light.position.set(3,5,4); scene.add(light);
const camera=new T.PerspectiveCamera(35,1,.01,100); const renderer=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true}); renderer.setSize(600,600); document.body.append(renderer.domElement);
const mixer = new T.AnimationMixer(g.scene); const mesh = (()=>{let m;g.scene.traverse(o=>{if(o.isSkinnedMesh)m=o});return m})();
window.pose=(name,t)=>{mixer.stopAllAction();const a=mixer.clipAction(g.animations.find(c=>c.name===name));a.reset().setLoop(T.LoopOnce,1);a.clampWhenFinished=true;a.play();mixer.setTime(t);scene.updateMatrixWorld(true);const box=new T.Box3(); const p=new T.Vector3(); const vertices=[];for(let i=0;i<mesh.geometry.attributes.position.count;i++){mesh.getVertexPosition(i,p);p.applyMatrix4(mesh.matrixWorld);box.expandByPoint(p);vertices.push([p.x,-p.z,p.y])}const center=box.getCenter(new T.Vector3()), size=box.getSize(new T.Vector3()).length();camera.position.copy(center).add(new T.Vector3(1.3,.8,2).normalize().multiplyScalar(size*1.5));camera.lookAt(center);renderer.render(scene,camera);return {min:box.min.toArray(),max:box.max.toArray(),drawCalls:renderer.info.render.calls,vertices}};
window.clips=g.animations.map(x=>({name:x.name,duration:x.duration}));window.ready=true;
</script></body></html>`;
const server=http.createServer(async(req,res)=>{try{if(req.url==='/'){res.setHeader('content-type','text/html');res.end(html);return}if(req.url==='/favicon.ico'){res.writeHead(204).end();return}const f=path.resolve(root,'.'+new URL(req.url,'http://localhost').pathname);assert.ok(f.startsWith(root+path.sep));res.setHeader('content-type',f.endsWith('.js')?'text/javascript':'model/gltf-binary');res.end(await fs.readFile(f))}catch{res.writeHead(404).end()}});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch(launchOptions); const page=await browser.newPage({viewport:{width:600,height:600}}); const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>errors.push(r.url()));page.on('console',m=>{if(m.type()==='error')errors.push(m.text())});
const expected={run:[[-.28185,-.76957,-.03577,.16941,-.17624,.90480],[-.23594,-1.25963,-.01113,.20061,-.61962,.91815],[-.27038,-1.73872,-.03013,.16680,-1.14440,.91769],[-.23245,-2.26288,-.01081,.20404,-1.62273,.92895],[-.27337,-2.76825,-.02536,.16396,-2.15314,.91196]],sit:[[-.21612,-.33409,-.04753,.22187,.19299,.87288],[-.21360,-.33598,-.04677,.22433,.18091,.87199],[-.28507,-.39425,-.03953,.16302,.13705,.79073],[-.28963,-.43388,-.03967,.16385,.13689,.78148],[-.21554,-.33411,-.04769,.22244,.19030,.87401]]};
const frames={run:[1,8.5,16,23.5,31],sit:[1,44,87,130,173]}; const results=[];
try{await page.goto('http://127.0.0.1:'+server.address().port+'/');await page.waitForFunction(()=>window.ready);for(const name of ['run','sit']){for(let i=0;i<5;i++){const frame=frames[name][i];const pose=await page.evaluate(({name,frame})=>window.pose(name,frame/24),{name,frame});const gl=pose;const actual=[gl.min[0],-gl.max[2],gl.min[1],gl.max[0],-gl.min[2],gl.max[1]];const buckets=new Map();const cell=.001;const key=(x,y,z)=>[x,y,z].join(',');for(const p of pose.vertices){const v=p.map(x=>Math.floor(x/cell));const k=key(...v);if(!buckets.has(k))buckets.set(k,[]);buckets.get(k).push(p)}let vertexError=0;for(const p of source.samples[name][i].vertices){const c=p.map(x=>Math.floor(x/cell));let nearest=Infinity;for(let x=-1;x<=1;x++)for(let y=-1;y<=1;y++)for(let z=-1;z<=1;z++)for(const q of buckets.get(key(c[0]+x,c[1]+y,c[2]+z))||[]){nearest=Math.min(nearest,Math.hypot(...p.map((v,k)=>v-q[k])))}vertexError=Math.max(vertexError,nearest)}assert.ok(vertexError<.0001,`${name} frame ${frame} vertex error ${vertexError}`);const maxDiff=Math.max(...actual.map((v,j)=>Math.abs(v-expected[name][i][j])));assert.ok(maxDiff<.004,`${name} frame ${frame} differs from source bounds by ${maxDiff}`);assert.ok(pose.drawCalls>0);await page.locator('canvas').screenshot({path:path.join(output,`${name}-${i}.png`)});results.push({name,frame,maxVertexError:vertexError,maxBoundsError:maxDiff,sourceBounds:expected[name][i],actualBounds:actual})}}assert.deepEqual(errors,[]);console.log(JSON.stringify({browser:browser.version(),clips:await page.evaluate(()=>window.clips),results,errors},null,2));}finally{await browser.close();await new Promise(r=>server.close(r))}
