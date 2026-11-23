// Render the actual six local GLBs without modifying the app or starting a server.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import {createRequire} from 'node:module';
import {basename,dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const base=dirname(fileURLToPath(import.meta.url)),project=createRequire(resolve('package.json'));
const three=resolve(dirname(project.resolve('three')),'..');
const {chromium}=project('playwright');
const {launchOptions}=await import(pathToFileURL(resolve('scripts/browser-test-utils.mjs')).href);
const geometry=JSON.parse(await fs.readFile(resolve(base,'reports/assembly.json'),'utf8'));
const files=Object.values(geometry.forms).map(row=>row.file);
const browser=await chromium.launch(launchOptions);
try{
  const page=await browser.newPage({viewport:{width:930,height:458},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const html='<!doctype html><meta charset=UTF-8><style>body{margin:0;background:#dad6cf;color:#3b3327;font:15px system-ui;display:grid;grid-template-columns:repeat(3,310px)}figure{margin:0}canvas{display:block}figcaption{height:39px;padding-left:12px}</style><script type=importmap>{"imports":{"three":"/three/build/three.module.js","three/addons/":"/three/examples/jsm/"}}</script>';
  await page.route('http://127.0.0.1:18408/**',async route=>{
    const path=new URL(route.request().url()).pathname;
    if(path==='/')return route.fulfill({contentType:'text/html',body:html});
    if(files.includes(path.slice(1)))return route.fulfill({contentType:'model/gltf-binary',path:resolve(base,'exports',basename(path))});
    if(path.startsWith('/three/') && path.endsWith('.js')){
      const js=resolve(three,path.slice(7));assert.ok(js.startsWith(three+'/'));
      return route.fulfill({path:js,contentType:'application/javascript'});
    }
    return route.fulfill({status:404,body:''});
  });
  await page.goto('http://127.0.0.1:18408/');
  const rows=await page.evaluate(async files=>{
    const THREE=await import('three');
    const {GLTFLoader}=await import('three/addons/loaders/GLTFLoader.js');
    const rows=[],ref=[];
    for (const [i,file] of files.entries()) {
      const bytes=await (await fetch('/'+file)).arrayBuffer();
      const sha256=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
      const {scene:trim}=await new GLTFLoader().parseAsync(bytes,'');
      const scene=new THREE.Scene();scene.add(trim);
      scene.add(new THREE.HemisphereLight(0xfff8e6,0xc8bfae,2));
      const light=new THREE.DirectionalLight(0xffffff,2.5);light.position.set(2.5,3,4);scene.add(light);
      const pair=file.includes('mitre');const width=pair?3.04:2.04,height=width*190/310;
      const camera=new THREE.OrthographicCamera(-width/2,width/2,height/2,-height/2,.01,40);
      camera.position.set(...(pair?[3.8,2.9,3.8]:[2.5,1.55,4.2]));
      camera.lookAt(...(pair?[.23,-.04,.23]:[0,-.048,0]));
      const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:true});
      renderer.setSize(310,190);renderer.setClearColor(0,0);
      const figure=document.createElement('figure'),caption=document.createElement('figcaption');
      caption.textContent=(pair?'Outside mitre':'Straight edge')+' · LOD'+i%3;
      figure.append(renderer.domElement,caption);document.body.append(figure);
      renderer.render(scene,camera);
      const gl=renderer.getContext(),pixels=new Uint8Array(310*190*4);
      gl.readPixels(0,0,310,190,gl.RGBA,gl.UNSIGNED_BYTE,pixels);
      const mask=Array.from({length:310*190},(_,j)=>pixels[4*j+3]>127);
      if(i%3===0)ref[pair?1:0]=mask;
      const reference=ref[pair?1:0];
      let inside=0,both=0,either=0;
      mask.forEach((x,j)=>{if(x)inside++;if(x&&reference[j])both++;if(x||reference[j])either++;});
      rows.push({file,sha256,renderedPixels:inside,draws:renderer.info.render.calls,triangles:renderer.info.render.triangles,
        silhouetteIntersectionOverUnion:both/either});
    }
    return rows;
  },files);
  assert.deepEqual(errors,[]);
  rows.forEach((row,i)=>{
    const expected=Object.values(geometry.forms)[i];
    assert.equal(row.sha256,expected.sha256);assert.equal(row.triangles,expected.triangles);assert.equal(row.draws,expected.draws);
    assert.ok(row.renderedPixels>1000 && row.silhouetteIntersectionOverUnion>.995);
  });
  const image=await page.screenshot({path:resolve(base,'reports/levels.png')});
  const report={chromium:browser.version(),errors,projection:'One fixed orthographic camera per form, 310 x 190 viewport',rows,
    screenshotSha256:createHash('sha256').update(image).digest('hex')};
  await fs.writeFile(resolve(base,'reports/browser.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
}finally{await browser.close();}
