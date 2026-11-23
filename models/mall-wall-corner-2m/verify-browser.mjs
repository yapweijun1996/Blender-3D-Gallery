// Render the exact three exported files with the repository's Three.js and Chromium.
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs/promises';
import http from 'node:http';
import { createRequire } from 'node:module';
import { basename, dirname, join, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const dir=dirname(fileURLToPath(import.meta.url));
const project=createRequire(resolve('package.json'));
const { chromium }=project('playwright');
const { launchOptions }=await import(pathToFileURL(resolve('scripts/browser-test-utils.mjs')).href);
const files=['mall-wall-corner-2m.glb','mall-wall-corner-2m-lod1.glb','mall-wall-corner-2m-lod2.glb'];
const threeDir=resolve(dirname(project.resolve('three')),'..');
const content='<!doctype html><meta charset=utf-8><style>*{box-sizing:border-box}body{display:flex;margin:0;background:#ddd9d0;color:#342e20;font:15px system-ui}figure{margin:0}figcaption{padding:6px 14px}canvas{display:block}</style><script type=importmap>{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>';
const server=http.createServer(async (req,res)=>{
  try {
    const path=new URL(req.url,'http://localhost').pathname;
    if (path==='/') {res.setHeader('Content-Type','text/html');res.end(content);return;}
    if (path==='/favicon.ico') {res.writeHead(204).end();return;}
    let source;
    if (path.startsWith('/three/')) {
      source=resolve(threeDir,path.slice(7));
      assert.ok(source.startsWith(threeDir+'/') && source.endsWith('.js'));
      res.setHeader('Content-Type','application/javascript');
    } else if (files.includes(path.slice(1))) {
      source=join(dir,'exports',basename(path));res.setHeader('Content-Type','model/gltf-binary');
    } else {res.writeHead(404).end();return;}
    res.end(await fs.readFile(source));
  } catch {res.writeHead(404).end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
try {
  browser=await chromium.launch(launchOptions);
  const page=await browser.newPage({viewport:{width:900,height:340},deviceScaleFactor:1});
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  const shots=await page.evaluate(async names=>{
    const THREE=await import('three');
    const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
    const camera=new THREE.PerspectiveCamera(34,1,.01,30);
    camera.position.set(-4.75,3.62,5.40);camera.lookAt(-.73,1.37,.73);
    const masks=[],rows=[];
    for (const [index,name] of names.entries()) {
      const bytes=await (await fetch('/'+name)).arrayBuffer();
      const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
      const {scene:wall}=await new GLTFLoader().parseAsync(bytes,'');
      const scene=new THREE.Scene();
      scene.add(new THREE.HemisphereLight(0xfff5da,0xb5c2cc,1.4));
      const key=new THREE.DirectionalLight(0xfff4db,1.6);key.position.set(-3,6,5);scene.add(key);
      scene.add(wall);
      const renderer=new THREE.WebGLRenderer({antialias:true,alpha:true,preserveDrawingBuffer:true});
      renderer.setSize(300,300);renderer.setClearColor(0,0);
      const target=document.createElement('figure'), cap=document.createElement('figcaption');
      cap.textContent=['Close · LOD0','Middle · LOD1','Distant · LOD2'][index];
      target.append(renderer.domElement,cap);document.body.append(target);
      renderer.render(scene,camera);
      const gl=renderer.getContext(), pixels=new Uint8Array(300*300*4);
      gl.readPixels(0,0,300,300,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
      const mask=Array.from({length:300*300},(_,i)=>pixels[4*i+3]>127);
      let hits=0,totalR=0,totalG=0,totalB=0;
      for(let i=0;i<mask.length;i++) if(mask[i]) {
        hits++;totalR+=pixels[i*4];totalG+=pixels[i*4+1];totalB+=pixels[i*4+2];
      }
      masks.push(mask);
      let textureSize;
      wall.traverse(o=>{
        if(o.isMesh && o.material.map)textureSize=[o.material.map.image.width,o.material.map.image.height];
      });
      rows.push({name,sha256,draws:renderer.info.render.calls,triangles:renderer.info.render.triangles,textureSize,
        pixels:hits,meanRgb:[totalR/hits,totalG/hits,totalB/hits].map(Math.round)});
    }
    rows.forEach((row,i)=>{
      let both=0,either=0;
      for(let j=0;j<masks[i].length;j++){if(masks[0][j] && masks[i][j])both++; if(masks[0][j] || masks[i][j])either++;}
      row.silhouetteIntersectionOverUnion=both/either;
    });
    return rows;
  },files);
  const geometry=JSON.parse(await fs.readFile(join(dir,'reports','geometry.json'),'utf8'));
  assert.deepEqual(errors,[]);
  for(const [i,row] of shots.entries()){
    const expected=geometry.levels['LOD'+i];
    assert.equal(expected.sha256,row.sha256);assert.equal(expected.triangles,row.triangles);
    assert.equal(expected.draws,row.draws);assert.ok(row.pixels>17000 && row.silhouetteIntersectionOverUnion>.995);
    assert.deepEqual(row.textureSize,i===0?[512,512]:undefined);
  }
  const image=await page.screenshot({path:join(dir,'reports','levels.png')});
  const result={chromium:browser.version(),errors,view:'3/4 fixed camera, masks at 300 × 300',levels:shots,
    imageSHA256:createHash('sha256').update(image).digest('hex')};
  await fs.writeFile(join(dir,'reports','browser.json'),JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result));
} finally {
  await browser?.close();
  await new Promise(resolve=>server.close(resolve));
}
