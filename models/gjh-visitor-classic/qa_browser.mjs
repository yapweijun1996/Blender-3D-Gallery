/** Exercise the shipped GLB in Chrome's WebGL2 renderer and capture its real wardrobe. */
import {chromium} from 'playwright';
import {createServer} from 'node:http';
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {dirname, join, resolve, sep} from 'node:path';
const here=dirname(fileURLToPath(import.meta.url));
const repo=resolve(here,'../..');
const target=join(here,'qa','browser');
const html=`<style>*{margin:0}body{background:#ede8f3}canvas{display:block}</style>
<script type="importmap">{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>
<script type="module">
import * as T from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {createWardrobe} from '/asset/wardrobe.mjs';
const r=new T.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
r.setSize(640,700);r.setPixelRatio(1);
r.outputColorSpace=T.SRGBColorSpace;r.toneMapping=T.NeutralToneMapping;r.toneMappingExposure=1;
document.body.appendChild(r.domElement);
const scene=new T.Scene();scene.background=new T.Color(0xece6f1);
const c=new T.OrthographicCamera(-.69,.69,.755,-.755,.01,20);
const fill=new T.HemisphereLight(0xfff8f4,0xd7c4d4,1.6);scene.add(fill);
for(const [x,y,z,color,intensity] of [[-2,3,4,0xffe8d7,2.2],[3,1,2,0xe0e8ff,1],[1,3,-3,0xffdfca,1.1]]){
 const l=new T.DirectionalLight(color,intensity);l.position.set(x,y,z);scene.add(l);
}
const load=new GLTFLoader(),model=await load.loadAsync('/asset/exports/GJH-Classic-Visitor.glb');
scene.add(model.scene);
const wardrobe=createWardrobe(model.scene);
const manifest=await (await fetch('/asset/exports/manifest.json')).json();
const animations=new T.AnimationMixer(model.scene);
const parts={};
for (const slot of ['Hat','Jeans']){
 parts[slot]=(await load.loadAsync('/asset/exports/modules/'+slot+'.glb')).scene;
}
window.resizeViewport=(width,height)=>{
 const halfWidth=.755*width/height;
 c.left=-halfWidth;c.right=halfWidth;c.updateProjectionMatrix();r.setSize(width,height);
};
window.capture=(degrees,look,clip)=>{
 animations.stopAllAction();
 for(const slot of ['Hat','Jeans'])wardrobe.remove(slot);
 if(look==='alternate'){
  for(const slot of ['Hat','Jeans'])wardrobe.equip(slot,parts[slot],manifest.variants[slot].hide);
 }
 if(clip){const a=animations.clipAction(model.animations.find(a=>a.name===clip));a.play();animations.setTime(a.getClip().duration*.95);}
 const a=degrees*Math.PI/180;c.position.set(3*Math.sin(a),.81,3*Math.cos(a));c.lookAt(0,.65,0);
 r.render(scene,c);
 return {triangles:r.info.render.triangles,calls:r.info.render.calls};
};
window.metadata={three:T.REVISION,webgl:r.getContext().getParameter(r.getContext().VERSION),clips:model.animations.map(a=>a.name)};
window.ready=true;
</script>`;
const server=createServer(async (req,res)=>{
 try {
  if(req.url==='/'){res.setHeader('Content-Type','text/html');res.end(html);return;}
  const u=new URL(req.url,'http://localhost');
  if(u.pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
  const [prefix,...rest]=u.pathname.slice(1).split('/');
  const base=prefix==='three'?join(repo,'node_modules','three'):prefix==='asset'?here:null;
  const p=base&&resolve(base,...rest);
  if(!p||!p.startsWith(base+sep))throw new Error('Unknown path');
  res.setHeader('Content-Type',p.endsWith('.js')||p.endsWith('.mjs')?'text/javascript':p.endsWith('.json')?'application/json':'application/octet-stream');
  res.end(await readFile(p));
 } catch {res.writeHead(404);res.end();}
});
await mkdir(target,{recursive:true});
await new Promise(go=>server.listen(0,'127.0.0.1',go));
let browser;
try{
 browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:640,height:700}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('console',m=>{if(['error','warning'].includes(m.type()))errors.push(m.text());});
 await page.goto('http://127.0.0.1:'+server.address().port);
 await page.waitForFunction(()=>window.ready===true);
 const report={modelSHA256:createHash('sha256').update(await readFile(join(here,'exports','GJH-Classic-Visitor.glb'))).digest('hex'),metadata:await page.evaluate(()=>window.metadata),views:[],messages:errors};
 report.wardrobeSHA256={};
 for(const slot of ['Hat','Jeans']){
  const bytes=await readFile(join(here,'exports','modules',slot+'.glb'));
  report.wardrobeSHA256[slot]=createHash('sha256').update(bytes).digest('hex');
 }
 for(const [name,angle,outfit,clip] of [['front',0,'classic',null],['quarter',28,'classic',null],['back',180,'classic',null],['hat-jeans',24,'alternate',null],['hat-jeans-sit',-30,'alternate','sit']]){
  const measured=await page.evaluate(args=>window.capture(...args),[angle,outfit,clip]);
  const img=await page.locator('canvas').screenshot({path:join(target,name+'.png')});
  report.views.push({name,...measured,sha256:createHash('sha256').update(img).digest('hex')});
 }
 for(const [name,width,height] of [['desktop-1440',1440,900],['mobile-390',390,844]]){
  await page.setViewportSize({width,height});
  const measured=await page.evaluate(([w,h])=>{window.resizeViewport(w,h);return window.capture(12,'classic',null);},[width,height]);
  const img=await page.screenshot({path:join(target,name+'.png')});
  report.views.push({name,width,height,...measured,sha256:createHash('sha256').update(img).digest('hex')});
 }
 await writeFile(join(target,'report.json'),JSON.stringify(report,null,2)+'\n');
 if(errors.some(e=>!e.includes('GPU stall due to ReadPixels')))throw new Error(errors.join('\n'));
}finally{if(browser)await browser.close();server.close();}
